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

from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.plugins.components.collections.common.delay import DelayComponent
from backend.flow.plugins.components.collections.redis.redis_entry_check import RedisEntryCheckComponent
from backend.utils.redis import RedisConn

logger = logging.getLogger("flow")

DEFAULT_BATCH_SIZE = 100
DEFAULT_BATCH_INTERVAL = 10  # seconds to wait between batches

# Redis key pattern (must match check_entry.py)
REDIS_ENTRY_CHECK_CANDIDATES_KEY = "dbm:redis_entry_check:candidates:{root_id}"


class RedisEntryCheckFlow(object):
    """
    Redis Entry Check Flow

    This flow verifies that DNS/CLB/Polaris entries contain the exact same proxies
    as the cluster currently has in db_meta.

    Flow structure:
    1. RedisEntryCheckComponent: Checks entries for a batch of clusters
    2. DelayComponent: Waits between batches (optional)
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        Initialize the Redis entry check flow

        Args:
            root_id: Unique identifier for the flow
            data: {
                "ticket_type": "REDIS_ENTRY_CHECK",
                "bk_biz_id": 0,
                "created_by": "system",
                "candidates_key": "redis_key_for_candidates",
                "batch_size": 100,
                "batch_interval": 10,  # seconds to wait between batches
            }
        """
        self.root_id = root_id
        self.ticket_data = data

    def _load_candidates_from_redis(self, candidates_key: str) -> List[int]:
        """
        Load candidate cluster_ids from Redis.

        Args:
            candidates_key: Redis key where candidates are stored

        Returns:
            List of cluster_ids
        """
        try:
            # Get the JSON array from Redis
            data = RedisConn.get(candidates_key)
            if not data:
                logger.warning(f"No data found in Redis for key: {candidates_key}")
                return []

            # Handle bytes if redis returns bytes
            data_str = data.decode() if isinstance(data, bytes) else data
            cluster_ids = json.loads(data_str)

            logger.info(f"Loaded {len(cluster_ids)} clusters from Redis: {candidates_key}")

            # Clean up the key after loading
            RedisConn.delete(candidates_key)
            return cluster_ids

        except Exception as e:
            logger.exception(f"Failed to load candidates from Redis: {e}")
            return []

    def run_flow(self):
        """
        Execute the Redis entry check workflow in batches.

        Batches are executed sequentially with optional intervals between batches.
        """
        redis_pipeline = Builder(root_id=self.root_id, data=self.ticket_data)

        # Load candidates from Redis using the key
        candidates_key = self.ticket_data.get("candidates_key", "")
        if candidates_key:
            cluster_ids = self._load_candidates_from_redis(candidates_key)
        else:
            logger.warning("There's no candidates key in ticket_data")
            cluster_ids = []

        if not cluster_ids:
            logger.warning("No cluster_ids provided for entry check")
            redis_pipeline.run_pipeline()
            return

        total_clusters = len(cluster_ids)

        batch_size = self.ticket_data.get("batch_size", DEFAULT_BATCH_SIZE)
        batch_interval = self.ticket_data.get("batch_interval", DEFAULT_BATCH_INTERVAL)
        total_batches = (total_clusters + batch_size - 1) // batch_size
        logger.info(f"Starting entry check for {total_clusters} clusters in {total_batches} batches")

        # Process cluster_ids in batches
        for batch_idx in range(total_batches):
            start_idx = batch_idx * batch_size
            end_idx = min(start_idx + batch_size, total_clusters)
            batch_cluster_ids = cluster_ids[start_idx:end_idx]
            batch_num = batch_idx + 1

            # Activity: Check entries for this batch
            redis_pipeline.add_act(
                act_name=_("批次{}/{}: 检查访问入口一致性").format(batch_num, total_batches),
                act_component_code=RedisEntryCheckComponent.code,
                kwargs={
                    "node_name": f"entry_check_batch_{batch_num}",
                    "cluster_ids": batch_cluster_ids,
                },
            )

            # Activity: Add delay between batches (except for the last batch)
            if batch_idx < total_batches - 1 and batch_interval > 0:
                redis_pipeline.add_act(
                    act_name=_("批次{}/{}: 等待{}秒后继续下一批次").format(batch_num, total_batches, batch_interval),
                    act_component_code=DelayComponent.code,
                    kwargs={"delay_seconds": batch_interval},
                )

        redis_pipeline.run_pipeline()
