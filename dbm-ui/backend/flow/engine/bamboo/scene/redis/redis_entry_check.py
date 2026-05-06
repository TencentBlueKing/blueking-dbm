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
from backend.flow.plugins.components.collections.redis.redis_entry_check import RedisEntryCheckComponent

logger = logging.getLogger("flow")

DEFAULT_BATCH_SIZE = 100
DEFAULT_BATCH_INTERVAL = 10  # seconds to wait between batches


class RedisEntryCheckFlow(object):
    """
    Redis Entry Check Flow

    This flow verifies that DNS/CLB/Polaris entries contain the exact same proxies
    as the cluster currently has in db_meta.

    Flow structure:
    1. Single RedisEntryCheckComponent (scheduled):
       - Loads cluster_ids from Redis
       - Processes clusters in batches with intervals between batches
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

    def run_flow(self):
        """
        Execute the Redis entry check workflow using a single scheduled component.

        The component will:
        1. Load cluster_ids from Redis (using candidates_key)
        2. Process clusters in batches
        3. Wait between batches using the schedule mechanism
        """
        redis_pipeline = Builder(root_id=self.root_id, data=self.ticket_data)

        # Get configuration from ticket_data
        candidates_key = self.ticket_data.get("candidates_key", "")
        batch_size = self.ticket_data.get("batch_size", DEFAULT_BATCH_SIZE)
        batch_interval = self.ticket_data.get("batch_interval", DEFAULT_BATCH_INTERVAL)

        if not candidates_key:
            logger.warning("No candidates_key provided in ticket_data")
            redis_pipeline.run_pipeline()
            return

        logger.info(
            f"Starting entry check flow with candidates_key={candidates_key}, "
            f"batch_size={batch_size}, batch_interval={batch_interval}"
        )

        # Add single scheduled component that handles everything
        redis_pipeline.add_act(
            act_name=_("检查访问入口一致性"),
            act_component_code=RedisEntryCheckComponent.code,
            kwargs={
                "candidates_key": candidates_key,
                "batch_size": batch_size,
                "batch_interval": batch_interval,
            },
        )

        redis_pipeline.run_pipeline()
