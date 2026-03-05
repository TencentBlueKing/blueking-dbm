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
import copy
import logging
from dataclasses import asdict
from typing import Dict, Optional

from django.utils.translation import gettext as _

from backend.configuration.constants import DBType
from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.models import Cluster
from backend.flow.consts import DBA_ROOT_USER
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.plugins.components.collections.spider.spider_schema_check_result import (
    SpiderSchemaCheckResultComponent,
)
from backend.flow.utils.mysql.mysql_act_dataclass import DownloadMediaKwargs, ExecActuatorKwargs
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload

logger = logging.getLogger("flow")


class SpiderSchemaCheckFlow(object):
    """
    spider集群表结构校验流程引擎
    {
    "uid": "2022111212001000",
    "root_id": 123,
    "created_by": "admin",
    "bk_biz_id": 9991001,
    "ticket_type": "TENDBCLUSTER_SCHEMA_CHECK",
    "cluster_ids": [1, 2],
    "check_all": true,
    "inconsistency_throws_err": false,
    "check_objects": [
        {"dbname": "test_db", "tables": ["table1", "table2"]},
        {"dbname": "another_db", "tables": []}
    ]
    }
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        self.root_id = root_id
        self.data = data

    def spider_schema_check_flow(self):
        """
        执行spider集群表结构校验
        流程：按 cluster_ids 编排，每个集群独立子流程
        1. 根据cluster_id获取集群信息（tdbctl中控节点IP和端口）
        2. 下发actuator介质
        3. 执行schema-check命令
        """
        cluster_ids = self.data["cluster_ids"]
        pipeline = Builder(
            root_id=self.root_id,
            data=self.data,
            need_random_pass_cluster_ids=list(set(cluster_ids)),
        )

        for cluster_id in cluster_ids:
            cluster = Cluster.objects.get(id=cluster_id)
            ctl_primary_address = cluster.tendbcluster_ctl_primary_address()
            ctl_primary_ip, ctl_primary_port = ctl_primary_address.split(IP_PORT_DIVIDER)
            ctl_primary_port = int(ctl_primary_port)

            sub_flow_context = copy.deepcopy(self.data)
            sub_flow_context.pop("cluster_ids")
            sub_flow_context["cluster_id"] = cluster_id
            sub_flow_context["bk_cloud_id"] = cluster.bk_cloud_id
            sub_flow_context["immute_domain"] = cluster.immute_domain

            sub_pipeline = SubBuilder(root_id=self.root_id, data=sub_flow_context)

            sub_pipeline.add_act(
                act_name=_("下发actuator介质"),
                act_component_code=TransFileComponent.code,
                kwargs=asdict(
                    DownloadMediaKwargs(
                        bk_cloud_id=cluster.bk_cloud_id,
                        exec_ip=[ctl_primary_ip],
                        file_list=GetFileList(db_type=DBType.MySQL).get_db_actuator_package(),
                    )
                ),
            )

            check_params = {
                "ip": ctl_primary_ip,
                "port": ctl_primary_port,
                "check_all": self.data.get("check_all", False),
                "inconsistency_throws_err": self.data.get("inconsistency_throws_err", False),
                "check_objects": self.data.get("check_objects", []),
            }

            sub_pipeline.add_act(
                act_name=_("执行表结构检查"),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(
                    ExecActuatorKwargs(
                        exec_ip=ctl_primary_ip,
                        bk_cloud_id=cluster.bk_cloud_id,
                        run_as_system_user=DBA_ROOT_USER,
                        get_mysql_payload_func=MysqlActPayload.get_spider_schema_check_payload.__name__,
                        cluster=check_params,
                    )
                ),
            )

            sub_pipeline.add_act(
                act_name=_("查询表结构检查结果"),
                act_component_code=SpiderSchemaCheckResultComponent.code,
                kwargs={
                    "ip": ctl_primary_ip,
                    "port": ctl_primary_port,
                    "bk_cloud_id": cluster.bk_cloud_id,
                },
            )

            pipeline.add_sub_pipeline(
                sub_flow=sub_pipeline.build_sub_process(sub_name=_("集群[{}]表结构检查").format(cluster.immute_domain))
            )

        logger.info(_("构建spider表结构检查流程成功"))
        pipeline.run_pipeline_with_sidecar(check_ai_monitor_cluster_list=list(set(cluster_ids)))
