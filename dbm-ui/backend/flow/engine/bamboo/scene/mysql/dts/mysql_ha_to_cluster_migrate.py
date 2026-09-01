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

from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_migrate_row_subflow import (
    build_parallel_migrate_row_pipelines,
)
from backend.flow.utils.mysql.dts.constants import MigrateType
from backend.flow.utils.mysql.dts.context import MysqlDtsTransData
from backend.flow.utils.mysql.dts.migrate_plan import resolve_migrate_plans_from_ticket_data

logger = logging.getLogger("flow")


class MysqlHaToClusterMigrateFlow:
    """TenDBHA → TenDBCluster 数据迁移 Flow。"""

    def __init__(self, root_id: str, data: Optional[Dict]):
        self.root_id = root_id
        self.data = data

    def run_flow(self):
        # FlowParamBuilder.add_common_params 会注入 uid=ticket.id；无单据场景兜底 root_id
        self.data.setdefault("uid", self.data.get("ticket_id") or self.root_id)
        migrate_plans = resolve_migrate_plans_from_ticket_data(self.data)
        pipeline = Builder(root_id=self.root_id, data=self.data)
        build_parallel_migrate_row_pipelines(
            pipeline=pipeline,
            root_id=self.root_id,
            data=self.data,
            migrate_plans=migrate_plans,
            migrate_type=MigrateType.HA_TO_CLUSTER.value,
        )
        pipeline.run_pipeline(init_trans_data_class=MysqlDtsTransData())
