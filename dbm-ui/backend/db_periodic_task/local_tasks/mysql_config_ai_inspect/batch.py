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
import logging
import uuid
from typing import Optional

from django.core.cache import cache
from django.utils.translation import gettext as _

from backend.db_meta.enums import ClusterPhase, ClusterType
from backend.db_meta.models import Cluster
from backend.db_report.models.mysql_config_ai_inspect import MysqlConfigAiInspect, MysqlConfigAiInspectStatus

logger = logging.getLogger("celery")

_OPEN_STATUSES = (
    MysqlConfigAiInspectStatus.PENDING.value,
    MysqlConfigAiInspectStatus.RUNNING.value,
)

_TARGET_CLUSTER_TYPES = (
    ClusterType.TenDBSingle.value,
    ClusterType.TenDBHA.value,
    ClusterType.TenDBCluster.value,
)

_OPEN_BATCH_LOCK_KEY = "mysql_config_ai_inspect:ensure_open_batch"
_OPEN_BATCH_LOCK_TTL = 120


def is_batch_finished(batch_id: str) -> bool:
    """批次无 pending/running 行则视为已结批。"""
    if not batch_id:
        return True
    return not MysqlConfigAiInspect.objects.filter(batch_id=batch_id, status__in=_OPEN_STATUSES).exists()


def _find_open_batch_id() -> Optional[str]:
    """优先返回最老的未完成批次，避免双批时孤儿旧批。"""
    return (
        MysqlConfigAiInspect.objects.filter(status__in=_OPEN_STATUSES)
        .order_by("create_at")
        .values_list("batch_id", flat=True)
        .first()
    )


def ensure_open_batch() -> Optional[str]:
    """确保存在未完成批次；若无则快照 ONLINE 三类集群开新批。"""
    open_batch_id = _find_open_batch_id()
    if open_batch_id:
        return open_batch_id

    got_lock = False
    try:
        got_lock = bool(cache.add(_OPEN_BATCH_LOCK_KEY, 1, timeout=_OPEN_BATCH_LOCK_TTL))
    except Exception:  # noqa
        # fail-closed：缓存异常时不开新批，避免双批孤儿
        logger.warning(_("获取开批锁失败，跳过开批"))
        return _find_open_batch_id()

    if not got_lock:
        return _find_open_batch_id()

    try:
        open_batch_id = _find_open_batch_id()
        if open_batch_id:
            return open_batch_id

        clusters = list(
            Cluster.objects.filter(phase=ClusterPhase.ONLINE, cluster_type__in=_TARGET_CLUSTER_TYPES).only(
                "id", "bk_biz_id", "immute_domain", "cluster_type"
            )
        )
        if not clusters:
            logger.warning(_("无 ONLINE MySQL 集群可开批"))
            return None

        batch_id = str(uuid.uuid4())
        rows = [
            MysqlConfigAiInspect(
                batch_id=batch_id,
                bk_biz_id=cluster.bk_biz_id,
                cluster_id=cluster.id,
                cluster_domain=cluster.immute_domain,
                cluster_type=cluster.cluster_type,
                status=MysqlConfigAiInspectStatus.PENDING.value,
                creator="system",
                updater="system",
            )
            for cluster in clusters
        ]
        MysqlConfigAiInspect.objects.bulk_create(rows, batch_size=500)
        logger.info(_("开批完成: batch_id={} cluster_count={}").format(batch_id, len(rows)))
        return batch_id
    finally:
        if got_lock:
            try:
                cache.delete(_OPEN_BATCH_LOCK_KEY)
            except Exception:  # noqa
                logger.warning(_("释放开批锁失败"))
