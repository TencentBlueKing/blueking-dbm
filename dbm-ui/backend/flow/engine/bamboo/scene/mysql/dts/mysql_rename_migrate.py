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

from backend.db_meta.models import Cluster
from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_migrate_row_subflow import (
    build_parallel_migrate_row_pipelines,
)
from backend.flow.utils.mysql.dts.context import MysqlDtsTransData
from backend.flow.utils.mysql.dts.migrate_plan import (
    infer_rename_migrate_type_from_plan,
    resolve_migrate_plans_from_ticket_data,
)

logger = logging.getLogger("flow")


def _collect_plan_cluster_ids(plans) -> set[int]:
    ids: set[int] = set()
    for plan in plans:
        for spec in plan.task_specs:
            for source in spec.sources:
                ids.add(source.cluster_id)
            ids.add(spec.target_cluster_id)
    return ids


def fill_rename_migrate_types(plans) -> None:
    """按行补 plan.migrate_type；已有值保留。"""
    missing = [plan for plan in plans if not getattr(plan, "migrate_type", "")]
    if not missing:
        return
    cluster_ids = _collect_plan_cluster_ids(missing)
    clusters = {c.id: c for c in Cluster.objects.filter(id__in=cluster_ids)} if cluster_ids else {}
    for plan in missing:
        plan.migrate_type = infer_rename_migrate_type_from_plan(plan, clusters)


class MysqlRenameMigrateFlow:
    """MySQL 重命名迁移 Flow（MYSQL_RENAME_MIGRATE）：复用并行行子流程，按行 migrate_type。"""

    def __init__(self, root_id: str, data: Optional[Dict]):
        self.root_id = root_id
        self.data = data

    def run_flow(self):
        self.data.setdefault("uid", self.data.get("ticket_id") or self.root_id)
        migrate_plans = resolve_migrate_plans_from_ticket_data(self.data)
        fill_rename_migrate_types(migrate_plans)
        pipeline = Builder(root_id=self.root_id, data=self.data)
        build_parallel_migrate_row_pipelines(
            pipeline=pipeline,
            root_id=self.root_id,
            data=self.data,
            migrate_plans=migrate_plans,
        )
        pipeline.run_pipeline(init_trans_data_class=MysqlDtsTransData())
