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
from dataclasses import asdict

from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.models import Cluster
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.plugins.components.collections.mysql.mysql_checksum_ticket import MySQLCheckSumTicketComponent
from backend.flow.plugins.components.collections.mysql.mysql_checksum_ticket_result_get import (
    MySQLCheckSumTicketResultComponent,
)
from backend.flow.plugins.components.collections.mysql.mysql_checksum_ticket_status import (
    MySQLCheckSumTicketProbeComponent,
)
from backend.flow.utils.mysql.dts.checksum_helper import build_dts_checksum_ticket_info
from backend.flow.utils.mysql.dts.context import MysqlDtsChecksumSubflowInput
from backend.flow.utils.mysql.dts.migrate_plan import DtsTaskSpec
from backend.flow.utils.mysql.mysql_act_dataclass import MysqlCheckSumKwargs


def mysql_dts_checksum_subflow(
    *,
    inp: MysqlDtsChecksumSubflowInput,
    task_spec: DtsTaskSpec,
) -> SubBuilder:
    """追平后关联 MYSQL_DTS_CHECKSUM：源=master、目标=slave，dts_mode 跳过主从硬检查。"""
    checksum_info = build_dts_checksum_ticket_info(task_spec=task_spec, bk_biz_id=inp.bk_biz_id)
    info0 = checksum_info["details"]["infos"][0]
    src_cluster = Cluster.objects.get(id=info0["cluster_id"])

    sub = SubBuilder(
        root_id=inp.root_id,
        data={
            "bk_biz_id": inp.bk_biz_id,
            "uid": inp.ticket_id,
            "ticket_id": inp.ticket_id,
            "creator": inp.creator,
            "created_by": inp.creator,
            "root_id": inp.root_id,
            "dts_mode": True,
        },
    )
    sub.add_act(
        act_name=MySQLCheckSumTicketComponent.node_name,
        act_component_code=MySQLCheckSumTicketComponent.code,
        kwargs=asdict(
            MysqlCheckSumKwargs(
                uid=inp.ticket_id,
                bk_biz_id=inp.bk_biz_id,
                created_by=inp.creator,
                checksum_info=checksum_info,
            )
        ),
    )
    sub.add_act(
        act_name=MySQLCheckSumTicketProbeComponent.node_name,
        act_component_code=MySQLCheckSumTicketProbeComponent.code,
        kwargs={},
    )
    sub.add_act(
        act_name=MySQLCheckSumTicketResultComponent.node_name,
        act_component_code=MySQLCheckSumTicketResultComponent.code,
        kwargs={
            "bk_cloud_id": src_cluster.bk_cloud_id,
            "checksum_pairs": [
                {
                    "master": f"{info0['master']['ip']}{IP_PORT_DIVIDER}{info0['master']['port']}",
                    "slave": f"{info0['slaves'][0]['ip']}{IP_PORT_DIVIDER}{info0['slaves'][0]['port']}",
                }
            ],
            "cluster_id": src_cluster.id,
        },
    )
    return sub
