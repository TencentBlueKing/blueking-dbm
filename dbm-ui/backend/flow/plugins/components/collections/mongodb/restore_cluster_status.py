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
from typing import List

from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import Service

from backend.db_meta.enums import ClusterStatus, InstanceStatus
from backend.db_meta.models import Cluster
from backend.flow.plugins.components.collections.common.base_service import BaseService

logger = logging.getLogger("json")


def _instances_all_running(cluster: Cluster) -> bool:
    """集群上已有的 storage / proxy 全部为 running。没有任何实例则不算恢复。"""
    has_storage = cluster.storageinstance_set.exists()
    has_proxy = cluster.proxyinstance_set.exists()
    if not has_storage and not has_proxy:
        return False
    storage_not_running = cluster.storageinstance_set.exclude(status=InstanceStatus.RUNNING.value).exists()
    proxy_not_running = cluster.proxyinstance_set.exclude(status=InstanceStatus.RUNNING.value).exists()
    return not storage_not_running and not proxy_not_running


def restore_mongo_cluster_status(cluster_ids: List[int]) -> List[int]:
    """
    集群下全部实例 status 为 running 时，把 Cluster.status 从 abnormal 改回 normal。

    实例 status 的正常值是 running；集群 status 的正常值是 normal（前端显示「正常」）。
    仍有非 running 实例、或集群是 temporary 时不改。
    """
    ids = sorted({int(cluster_id) for cluster_id in cluster_ids or [] if cluster_id})
    if not ids:
        return []
    updated = []
    for cluster in Cluster.objects.filter(id__in=ids):
        if cluster.status == ClusterStatus.TEMPORARY.value:
            logger.info("restore mongo cluster status skip temporary cluster_id=%s", cluster.id)
            continue
        if not _instances_all_running(cluster):
            logger.info(
                "restore mongo cluster status skip cluster_id=%s status=%s, not all instances running",
                cluster.id,
                cluster.status,
            )
            continue
        if cluster.status == ClusterStatus.NORMAL.value:
            continue
        cluster.status = ClusterStatus.NORMAL.value
        cluster.save(update_fields=["status"])
        updated.append(cluster.id)
        logger.info("restore mongo cluster status cluster_id=%s -> %s", cluster.id, ClusterStatus.NORMAL.value)
    return updated


class RestoreMongoClusterStatusService(BaseService):
    """
    kwargs: {"cluster_ids": [1, 2]}
    """

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs") or {}
        cluster_ids = kwargs.get("cluster_ids") or []
        try:
            updated = restore_mongo_cluster_status(cluster_ids)
        except Exception as exc:  # noqa: BLE001
            logger.error("restore mongo cluster status fail cluster_ids=%s err=%s", cluster_ids, exc, exc_info=True)
            self.log_error("restore mongo cluster status fail: {}".format(exc))
            return False
        self.log_info("restore mongo cluster status updated={}".format(updated))
        return True

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]


class RestoreMongoClusterStatusComponent(Component):
    name = __name__
    code = "restore_mongo_cluster_status"
    bound_service = RestoreMongoClusterStatusService
