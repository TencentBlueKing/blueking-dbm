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
from backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_migrate_subflow import mysql_dts_migrate_subflow
from backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_task_clean_subflow import mysql_dts_task_clean_subflow
from backend.flow.utils.mysql.dts.constants import MigrateType
from backend.flow.utils.mysql.dts.context import (
    MysqlDtsMigrateSubflowInput,
    MysqlDtsTaskCleanSubflowInput,
    MysqlDtsTransData,
)
from backend.flow.utils.mysql.dts.cutover_helper import resolve_master_addr_from_plan
from backend.flow.utils.mysql.dts.migrate_credentials import (
    grant_targets_to_dicts,
    resolve_migrate_temp_account_for_pipeline,
)
from backend.flow.utils.mysql.dts.migrate_helper import build_ticket_dts_clean_names
from backend.flow.utils.mysql.dts.migrate_plan import resolve_migrate_plan_from_ticket_data

logger = logging.getLogger("flow")


class MysqlHaToClusterMigrateFlow:
    """TenDBHA → TenDBCluster 数据迁移 Flow。"""

    def __init__(self, root_id: str, data: Optional[Dict]):
        self.root_id = root_id
        self.data = data

    def run_flow(self):
        # FlowParamBuilder.add_common_params 会注入 uid=ticket.id；无单据场景兜底 root_id
        self.data.setdefault("uid", self.data.get("ticket_id") or self.root_id)
        migrate_plan = resolve_migrate_plan_from_ticket_data(self.data)
        migrate_plan.migrate_type = MigrateType.HA_TO_CLUSTER.value
        pipeline = Builder(root_id=self.root_id, data=self.data)

        dts_user, dts_password, grant_hosts, grant_targets = resolve_migrate_temp_account_for_pipeline(migrate_plan)
        grant_target_dicts = grant_targets_to_dicts(grant_targets)
        creator = self.data.get("created_by", "")
        bk_biz_id = int(self.data["bk_biz_id"])
        ticket_id = int(self.data.get("ticket_id", 0) or 0)

        migrate_inp = MysqlDtsMigrateSubflowInput(
            root_id=self.root_id,
            bk_biz_id=bk_biz_id,
            ticket_id=ticket_id,
            migrate_plan=migrate_plan,
            creator=creator,
            dts_user=dts_user,
            dts_password=dts_password,
            grant_hosts=grant_hosts,
            grant_targets=grant_targets,
        )
        pipeline.add_sub_pipeline(
            mysql_dts_migrate_subflow(migrate_inp).build_sub_process(sub_name=_("HA 到 Cluster 数据迁移"))
        )

        task_names, source_names = build_ticket_dts_clean_names(migrate_plan)
        clean_inp = MysqlDtsTaskCleanSubflowInput(
            root_id=self.root_id,
            bk_biz_id=bk_biz_id,
            dts_user=dts_user,
            grant_hosts=grant_hosts,
            grant_targets=grant_target_dicts,
            ignore_errors=True,
            creator=creator,
            master_addr=resolve_master_addr_from_plan(migrate_plan),
            bk_cloud_id=int(migrate_plan.bk_cloud_id or 0),
            task_names=task_names,
            source_names=source_names,
        )
        pipeline.add_sub_pipeline(
            mysql_dts_task_clean_subflow(clean_inp).build_sub_process(sub_name=_("dts-task-clean"))
        )
        pipeline.run_pipeline(init_trans_data_class=MysqlDtsTransData())
