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
from typing import Dict, Optional

from django.utils.translation import gettext as _

from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.plugins.components.collections.redis.conf_check.components import RedisConfCheckBatchComponent
from backend.flow.plugins.components.collections.redis.conf_check.redis_candidates import count_candidate_cluster_ids

logger = logging.getLogger("flow")

DEFAULT_BATCH_SIZE = 2000
DEFAULT_BATCH_INTERVAL = 10  # seconds to wait between batches


class RedisConfCheckFlow(object):
    """
    Redis Conf Check Flow.

    Runs every registered conf checker (role, predixy servers, ...) against a set
    of candidate clusters. Live instance state is read via DRS; the only on-host
    work (reading predixy.conf) is delivered as one consolidated job per host.

    Flow structure (per batch of clusters):
    1. RedisConfCheckBatchService: issue host scripts, poll jobs, pace DRS calls,
       evaluate every checker, write reports, optional inter-batch delay — one node.

    Candidate cluster IDs live in a Redis list (candidates_key); each batch act
    reads its slice by batch_num — cluster IDs are not embedded in pipeline kwargs.
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
                "drs_chunk_size": 20,
                "drs_chunks_per_tick": 1,
                "password_batch_size": 200,
                "checker_customized": {},
            }
        """
        self.root_id = root_id
        self.ticket_data = data

    def run_flow(self):
        """Execute the conf check workflow in batches."""
        redis_pipeline = Builder(root_id=self.root_id, data=self.ticket_data)

        candidates_key = self.ticket_data.get("candidates_key", "")
        if not candidates_key:
            logger.warning("No candidates_key provided for conf check")
            redis_pipeline.run_pipeline()
            return

        total_clusters = count_candidate_cluster_ids(candidates_key)
        if total_clusters == 0:
            logger.warning("No cluster candidates found in Redis for conf check")
            redis_pipeline.run_pipeline()
            return

        batch_size = self.ticket_data.get("batch_size", DEFAULT_BATCH_SIZE)
        batch_interval = self.ticket_data.get("batch_interval", DEFAULT_BATCH_INTERVAL)
        interval = self.ticket_data.get("interval", None)
        max_retries = self.ticket_data.get("max_retries", None)
        drs_chunk_size = self.ticket_data.get("drs_chunk_size", None)
        drs_chunks_per_tick = self.ticket_data.get("drs_chunks_per_tick", None)
        password_batch_size = self.ticket_data.get("password_batch_size", None)

        total_batches = (total_clusters + batch_size - 1) // batch_size
        logger.info(f"Starting conf check for {total_clusters} clusters in {total_batches} batches")

        for batch_idx in range(total_batches):
            batch_num = batch_idx + 1

            redis_pipeline.add_act(
                act_name=_("批次{}/{}: 配置检查").format(batch_num, total_batches),
                act_component_code=RedisConfCheckBatchComponent.code,
                kwargs={
                    "node_name": f"conf_check_batch_{batch_num}",
                    "candidates_key": candidates_key,
                    "batch_num": batch_num,
                    "batch_size": batch_size,
                    "total_batches": total_batches,
                    "interval": interval,
                    "max_retries": max_retries,
                    "drs_chunk_size": drs_chunk_size,
                    "drs_chunks_per_tick": drs_chunks_per_tick,
                    "password_batch_size": password_batch_size,
                    "delay_after_seconds": batch_interval if batch_idx < total_batches - 1 else 0,
                },
            )

        redis_pipeline.run_pipeline()
