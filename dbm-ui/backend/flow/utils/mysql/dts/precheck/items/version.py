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

from django.utils.translation import gettext_lazy as _

from backend.flow.utils.mysql.dts.precheck.base import CheckContext, CheckLevel, CheckResult, register
from backend.flow.utils.mysql.dts.precheck.constants import DTS_PRECHECK_MAX_MAJOR, DTS_PRECHECK_MIN_MAJOR
from backend.flow.utils.mysql.mysql_version_parse import mysql_version_parse


def _major_minor(raw: str) -> int:
    parsed = mysql_version_parse(raw)
    return parsed // 1000 if parsed else 0


def _in_range(raw: str, *, cluster_id: int, side: str) -> CheckResult:
    parsed = _major_minor(raw)
    minimum = _major_minor(DTS_PRECHECK_MIN_MAJOR)
    maximum = _major_minor(DTS_PRECHECK_MAX_MAJOR)
    ok = parsed != 0 and minimum <= parsed <= maximum
    return CheckResult(
        ok=ok,
        code="version.in_range",
        message=(
            _("{} 端集群 {} 版本在 DTS 支持范围内").format(side, cluster_id)
            if ok
            else _("{} 端集群 {} 版本不在 DTS 支持范围内").format(side, cluster_id)
        ),
        level=CheckLevel.FAIL,
        details={
            "side": side,
            "cluster_id": cluster_id,
            "raw": raw,
            "parsed": parsed,
            "range": [DTS_PRECHECK_MIN_MAJOR, DTS_PRECHECK_MAX_MAJOR],
        },
    )


def _dest_ge_source(
    src_raw: str,
    dst_raw: str,
    *,
    source_address: str = "",
    target_address: str = "",
) -> CheckResult:
    source_version = _major_minor(src_raw)
    target_version = _major_minor(dst_raw)
    ok = source_version != 0 and target_version != 0 and target_version >= source_version
    return CheckResult(
        ok=ok,
        code="version.dest_ge_source",
        message=_("目标端版本不低于源端") if ok else _("目标端版本低于源端或版本无法解析"),
        level=CheckLevel.FAIL,
        details={
            "source_address": source_address,
            "target_address": target_address,
            "source_raw": src_raw,
            "target_raw": dst_raw,
            "source_parsed": source_version,
            "target_parsed": target_version,
        },
    )


@register("version", _("版本检查"))
def run(ctx: CheckContext) -> list[CheckResult]:
    src_raw = ctx.source.mysql_version()
    dst_raw = ctx.target.mysql_version()
    rules = (
        lambda: _in_range(
            src_raw,
            cluster_id=ctx.source.endpoint.cluster_id,
            side="source",
        ),
        lambda: _in_range(
            dst_raw,
            cluster_id=ctx.target.endpoint.cluster_id,
            side="target",
        ),
        lambda: _dest_ge_source(
            src_raw,
            dst_raw,
            source_address=ctx.source.endpoint.address,
            target_address=ctx.target.endpoint.address,
        ),
    )
    results = []
    for rule in rules:
        try:
            results.append(rule())
        except Exception as exc:
            results.append(
                CheckResult(
                    ok=False,
                    code="version.rule_error",
                    message=str(exc),
                    level=CheckLevel.FAIL,
                )
            )
    return results
