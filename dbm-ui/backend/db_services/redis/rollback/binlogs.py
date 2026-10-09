# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""

import hashlib
import re
from collections import Counter
from datetime import datetime
from typing import Dict, List, Optional, Sequence, Tuple

from django.utils.translation import gettext as _

from backend.db_services.redis.rollback.exceptions import RollbackPlanError

GAP_SAMPLE_SIZE = 10

# binlog-{ip}-{port}-{index}-{yyyymmddHHMMSS}.log.zst; legacy GCS names carry no ip.
_SSD_BINLOG_NAME = re.compile(r"^binlog-(?:\d{1,3}(?:\.\d{1,3}){3}-)?\d+-(\d+)-\d{14}\.log\.(?:zst|lzo)$")


def binlog_index(file_name: str) -> Optional[int]:
    match = _SSD_BINLOG_NAME.match(file_name.split("/")[-1])
    return int(match.group(1)) if match else None


def index_segments(indexes: Sequence[int], limit: int = GAP_SAMPLE_SIZE) -> str:
    """Contiguous runs for humans, e.g. ``[1000-1001],[1003-1004]``; capped so many gaps stay short."""
    runs: List[List[int]] = []
    for index in sorted(set(indexes)):
        if runs and index == runs[-1][1] + 1:
            runs[-1][1] = index
        else:
            runs.append([index, index])
    shown = ["[{}]".format(start) if start == end else "[{}-{}]".format(start, end) for start, end in runs[:limit]]
    if len(runs) > limit:
        shown.append("...(+{})".format(len(runs) - limit))
    return ",".join(shown)


def binlog_fingerprint(file_names: Sequence[str]) -> str:
    """sha256 over basenames in index order; the actuator recomputes it from the files it finds."""
    return hashlib.sha256("\n".join(name.split("/")[-1] for name in file_names).encode()).hexdigest()


def select_binlog_chain(
    binlogs: Sequence[Dict], full_start: datetime, recover_at: datetime, allow_nonconsecutive: bool = False
) -> Tuple[List[Dict], Optional[Dict]]:
    """Gate C: the binlogs to replay on a full backup taken at ``full_start`` to reach ``recover_at``.

    The chain runs from the last file begun at or before the full backup to the first one begun
    at or after the target, and its indexes must be contiguous. ``binlogs`` come from the same
    source instance as the full backup; a replaced instance therefore shows up as a missing tail.

    ``allow_nonconsecutive`` lets index holes through and returns them as ``gaps``
    (``{missing_count, missing}``, first 10 indexes). A missing head or tail, duplicates, fewer
    than two files and an index that goes backwards in time (instance restart) still fail.
    """
    unique = list({b["file_name"]: b for b in binlogs}.values())
    heads = [b for b in unique if b["begin_time"] <= full_start]
    tails = [b for b in unique if b["begin_time"] >= recover_at]
    if not heads:
        raise RollbackPlanError(context={"message": _("全备开始前没有 binlog")})
    if not tails:
        raise RollbackPlanError(context={"message": _("回档时刻之后没有 binlog，binlog 链断裂（实例可能已替换），请选更早的时间")})

    head_time = max(b["begin_time"] for b in heads)
    tail_time = min(b["begin_time"] for b in tails)
    chain = sorted(
        (b for b in unique if head_time <= b["begin_time"] <= tail_time), key=lambda b: (b["index"], b["file_name"])
    )
    if len(chain) < 2:
        raise RollbackPlanError(context={"message": _("binlog 数少于 2")})

    counts = Counter(b["index"] for b in chain)
    duplicated = sorted(index for index, count in counts.items() if count > 1)
    if duplicated:
        raise RollbackPlanError(context={"message": _("binlog 序号重复: {}").format(duplicated)})
    missing = sorted(set(range(chain[0]["index"], chain[-1]["index"] + 1)) - set(counts))
    if not missing:
        return chain, None

    shown = (
        missing if len(missing) <= GAP_SAMPLE_SIZE else missing[:GAP_SAMPLE_SIZE] + ["...({})".format(len(missing))]
    )
    by_time = [b["index"] for b in sorted(chain, key=lambda b: (b["begin_time"], b["index"]))]
    if by_time != [b["index"] for b in chain]:
        raise RollbackPlanError(context={"message": _("binlog 序号不连续且随时间回退（实例可能重启过），缺失: {}").format(shown)})
    if not allow_nonconsecutive:
        raise RollbackPlanError(
            context={"message": _("binlog 序号不连续，缺失: {}；如可接受缺失这段写入，可开启 allow_binlog_nonconsecutive").format(shown)}
        )
    return chain, {"missing_count": len(missing), "missing": missing[:GAP_SAMPLE_SIZE]}
