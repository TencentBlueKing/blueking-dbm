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
import json
import logging
from typing import Dict, List, Optional

from django.utils.translation import gettext as _

from backend.db_meta.models import Cluster
from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.plugins.components.collections.common.delay import DelayComponent
from backend.flow.plugins.components.collections.redis.conf_check.components import (
    RedisConfCheckCollectComponent,
    RedisConfCheckReportComponent,
)
from backend.flow.utils.redis.redis_context_dataclass import RedisConfCheckContext
from backend.utils.redis import RedisConn

logger = logging.getLogger("flow")

DEFAULT_BATCH_SIZE = 2000
DEFAULT_BATCH_INTERVAL = 10  # seconds to wait between batches

# Redis Hash key pattern (must match check_conf.py)
REDIS_CONF_CHECK_CANDIDATES_KEY = "dbm:redis_conf_check:candidates:{root_id}"
REDIS_CONF_CHECK_META_FIELD = "_meta"


class RedisConfCheckFlow(object):
    """
    Redis Conf Check Flow.

    Runs every registered conf checker (role, predixy servers, ...) against a set
    of candidate clusters. Live instance state is read via DRS; the only on-host
    work (reading predixy.conf) is delivered as one consolidated job per host.

    Flow structure (per batch of clusters):
    1. RedisConfCheckCollectService: deliver one combined on-host script per host.
    2. RedisConfCheckReportService: poll host jobs, gather DRS state, evaluate
       every checker, write reports.
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        Args:
            root_id: Unique identifier for the flow
            data: {
                "ticket_type": "REDIS_CONF_CHECK",
                "bk_biz_id": 0,
                "created_by": "system",
                "candidates_key": "redis_key_for_candidates",
                "batch_size": 2000,
                "batch_interval": 10,
                "interval": 5,
                "max_retries": 120,
                "drs_chunk_size": 20
            }
        """
        self.root_id = root_id
        self.ticket_data = data

    def _load_candidates_from_redis_hash(self, candidates_key: str) -> List[Dict]:
        """
        Load candidate cluster infos from a Redis Hash.

        Hash structure:
        - Field "_meta": {"total_cloud_groups": int, "total_clusters": int, ...}
        - Field "<bk_cloud_id>": [cluster_id1, cluster_id2, ...] (JSON array)

        Returns: [{"bk_cloud_id": x, "cluster_ids": [...]}, ...]
        """
        try:
            hash_data = RedisConn.hgetall(candidates_key)
            if not hash_data:
                logger.warning(f"No data found in Redis Hash for key: {candidates_key}")
                return []

            infos = []
            for field, value in hash_data.items():
                field_str = field.decode() if isinstance(field, bytes) else field
                value_str = value.decode() if isinstance(value, bytes) else value
                if field_str == REDIS_CONF_CHECK_META_FIELD:
                    continue
                bk_cloud_id = int(field_str)
                cluster_ids = json.loads(value_str)
                infos.append({"bk_cloud_id": bk_cloud_id, "cluster_ids": cluster_ids})

            logger.info(f"Loaded {len(infos)} cloud groups from Redis Hash: {candidates_key}")
            RedisConn.delete(candidates_key)
            return infos
        except Exception as e:
            logger.exception(f"Failed to load candidates from Redis Hash: {e}")
            return []

    def _prepare_cluster_data_list(self, infos: List[Dict]) -> List[Dict]:
        """Flatten cloud groups into a list of {cluster_id, bk_cloud_id} for valid clusters."""
        candidate_ids = [cluster_id for info in infos for cluster_id in info.get("cluster_ids", [])]
        existing_ids = set(Cluster.objects.filter(id__in=candidate_ids).values_list("id", flat=True))
        cluster_data_list = []
        for info in infos:
            bk_cloud_id = info.get("bk_cloud_id", 0)
            for cluster_id in info.get("cluster_ids", []):
                if cluster_id not in existing_ids:
                    logger.warning(f"Cluster {cluster_id} not found, skipping")
                    continue
                cluster_data_list.append({"cluster_id": cluster_id, "bk_cloud_id": bk_cloud_id})
        return cluster_data_list

    def run_flow(self):
        """Execute the conf check workflow in batches."""
        redis_pipeline = Builder(root_id=self.root_id, data=self.ticket_data)

        candidates_key = self.ticket_data.get("candidates_key", "")
        if candidates_key:
            infos = self._load_candidates_from_redis_hash(candidates_key)
        else:
            infos = self.ticket_data.get("infos", [])

        if not infos:
            logger.warning("No cluster infos provided for conf check")
            redis_pipeline.run_pipeline()
            return

        cluster_data_list = self._prepare_cluster_data_list(infos)
        if not cluster_data_list:
            logger.warning("No valid clusters to check")
            redis_pipeline.run_pipeline()
            return

        batch_size = self.ticket_data.get("batch_size", DEFAULT_BATCH_SIZE)
        batch_interval = self.ticket_data.get("batch_interval", DEFAULT_BATCH_INTERVAL)
        interval = self.ticket_data.get("interval", None)
        max_retries = self.ticket_data.get("max_retries", None)
        drs_chunk_size = self.ticket_data.get("drs_chunk_size", None)

        total_clusters = len(cluster_data_list)
        total_batches = (total_clusters + batch_size - 1) // batch_size
        logger.info(f"Starting conf check for {total_clusters} clusters in {total_batches} batches")

        for batch_idx in range(total_batches):
            start_idx = batch_idx * batch_size
            end_idx = min(start_idx + batch_size, total_clusters)
            batch_clusters = cluster_data_list[start_idx:end_idx]
            batch_num = batch_idx + 1

            redis_pipeline.add_act(
                act_name=_("批次{}/{}: 下发配置检查脚本 ({}个集群)").format(batch_num, total_batches, len(batch_clusters)),
                act_component_code=RedisConfCheckCollectComponent.code,
                kwargs={
                    "node_name": f"conf_check_collect_batch_{batch_num}",
                    "clusters": batch_clusters,
                },
            )

            redis_pipeline.add_act(
                act_name=_("批次{}/{}: 采集状态并处理检查结果").format(batch_num, total_batches),
                act_component_code=RedisConfCheckReportComponent.code,
                kwargs={
                    "node_name": f"conf_check_report_batch_{batch_num}",
                    "clusters": batch_clusters,
                    "interval": interval,
                    "max_retries": max_retries,
                    "drs_chunk_size": drs_chunk_size,
                },
            )

            if batch_idx < total_batches - 1 and batch_interval > 0:
                redis_pipeline.add_act(
                    act_name=_("批次{}/{}: 等待{}秒后继续下一批次").format(batch_num, total_batches, batch_interval),
                    act_component_code=DelayComponent.code,
                    kwargs={"delay_seconds": batch_interval},
                )

        redis_pipeline.run_pipeline(init_trans_data_class=RedisConfCheckContext())
