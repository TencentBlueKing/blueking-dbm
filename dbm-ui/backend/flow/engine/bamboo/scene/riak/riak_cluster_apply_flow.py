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
import logging.config
from dataclasses import asdict
from typing import Dict, Optional

from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.flow.consts import DBA_ROOT_USER
from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.riak.get_riak_resource import GetRiakResourceComponent
from backend.flow.plugins.components.collections.riak.riak_db_meta import RiakDBMetaComponent
from backend.flow.utils.riak.riak_act_payload import RiakActPayload
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.utils.riak.riak_act_dataclass import DownloadMediaKwargs, ExecActuatorKwargs, \
    DBMetaFuncKwargs
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.utils.riak.riak_context_dataclass import ApplyManualContext
from backend.flow.utils.riak.riak_db_meta import RiakDBMeta

logger = logging.getLogger("flow")


class RiakClusterApplyFlow(object):
    """
    构建Riak集群申请流程的抽象类
    {
    "uid": "2022111212001000",
    "root_id": 123,
    "created_by": "admin",
    "bk_biz_id": 0,
    "ticket_type": "RIAK_APPLY",
    "timing": "2022-11-21 12:04:10",
    "bk_app_abbr": "test",
    "ip_source": "manual_input",
    "zone": "hh",
    "db_module_id": 0,
    "cluster_alias": "测试集群",
    "city_code": "深圳",
    "bk_cloud_id": 0,
    "nodes": [
        {
            "ip": "127.0.0.1",
            "bk_host_id": 0,
        }
    ]
    }
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递过来的参数列表，是dict格式
        """
        self.root_id = root_id
        self.data = data

    def deploy_riak_cluster_flow(self):
        """
        部署Riak集群
        """
        riak_pipeline = Builder(root_id=self.root_id, data=self.data)
        # 获取机器资源 done
        riak_pipeline.add_act(
            act_name=_("获取机器信息"), act_component_code=GetRiakResourceComponent.code, kwargs={}
        )

        ips = [ip for ip in self.data["nodes"]]
        riak_pipeline.add_act(
            act_name=_("下发riak介质"),
            act_component_code=TransFileComponent.code,
            kwargs=asdict(
                DownloadMediaKwargs(
                    bk_cloud_id=self.data["bk_cloud_id"],
                    exec_ip=ips,
                    file_list=GetFileList(db_type=DBType.Riak).riak_install_package(),
                )
            ),
        )

        riak_pipeline.add_act(
            act_name=_("actuator部署节点"),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(
                ExecActuatorKwargs(
                    exec_ip=ips,
                    bk_cloud_id=self.data["bk_cloud_id"],
                    run_as_system_user=DBA_ROOT_USER,
                    get_mysql_payload_func=RiakActPayload.get_deploy_payload.__name__,
                )
            ),
        )

        riak_pipeline.add_act(
            act_name=_("actuator添加节点"),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(
                ExecActuatorKwargs(
                    exec_ip=ips[0],
                    bk_cloud_id=self.data["bk_cloud_id"],
                    run_as_system_user=DBA_ROOT_USER,
                    get_mysql_payload_func=RiakActPayload.get_add_node_payload.__name__,
                )
            ),
        )
        riak_pipeline.add_act(
            act_name=_("修改元数据"),
            act_component_code=RiakDBMetaComponent.code,
            kwargs=asdict(
                DBMetaFuncKwargs(RiakDBMeta.riak_deploy_node.__name__)
            ),
        )

        riak_pipeline.run_pipeline(init_trans_data_class=ApplyManualContext())
