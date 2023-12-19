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
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.riak.exec_actuator_script import ExecuteRiakActuatorScriptComponent
from backend.flow.plugins.components.collections.riak.get_riak_cluster_node import GetRiakClusterNodeComponent
from backend.flow.plugins.components.collections.riak.get_riak_resource import GetRiakResourceComponent
from backend.flow.plugins.components.collections.riak.riak_db_meta import RiakDBMetaComponent
from backend.flow.plugins.components.collections.riak.trans_files import TransFileComponent
from backend.flow.utils.riak.riak_act_dataclass import DBMetaFuncKwargs, DownloadMediaKwargsFromTrans
from backend.flow.utils.riak.riak_act_payload import RiakActPayload
from backend.flow.utils.riak.riak_context_dataclass import RiakActKwargs, ScaleOutManualContext
from backend.flow.utils.riak.riak_db_meta import RiakDBMeta

logger = logging.getLogger("flow")


class RiakClusterScaleOutFlow(object):
    """
    Riak扩容流程的抽象类
    {
    "uid": "2022111212001000",
    "root_id": 123,
    "created_by": "admin",
    "bk_biz_id": 0,
    "ticket_type": "RIAK_CLUSTER_SCALE_OUT",
    "ip_source": "manual_input",
    "bk_cloud_id": 0,
    "cluster_id": 5,
    "nodes": [
        {
            "ip": "127.0.0.1",
            "bk_host_id": 0
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

    def riak_cluster_scale_out_flow(self):
        """
        Riak集群扩容
        """
        riak_pipeline = Builder(root_id=self.root_id, data=self.data)
        sub_pipeline = SubBuilder(root_id=self.root_id, data=self.data)

        sub_pipeline.add_act(act_name=_("获取机器信息"), act_component_code=GetRiakResourceComponent.code, kwargs={})
        sub_pipeline.add_act(act_name=_("获取集群中的节点"), act_component_code=GetRiakClusterNodeComponent.code, kwargs={})
        ips = [node["ip"] for node in self.data["nodes"]]

        sub_pipeline.add_act(
            act_name=_("下发actuator以及riak介质"),
            act_component_code=TransFileComponent.code,
            kwargs=asdict(
                DownloadMediaKwargsFromTrans(
                    get_trans_data_ip_var=ScaleOutManualContext.get_nodes_var_name(),
                    bk_cloud_id=self.data["bk_cloud_id"],
                    file_list=GetFileList(db_type=DBType.Riak).riak_install_package(self.data["db_version"]),
                )
            ),
        )

        sub_pipeline.add_act(
            act_name=_("actuator_riak获取集群配置"),
            act_component_code=ExecuteRiakActuatorScriptComponent.code,
            kwargs=asdict(
                RiakActKwargs(
                    get_trans_data_ip_var=ScaleOutManualContext.get_base_node_var_name(),
                    bk_cloud_id=self.data["bk_cloud_id"],
                    run_as_system_user=DBA_ROOT_USER,
                    get_riak_payload_func=RiakActPayload.get_config_payload.__name__,
                )
            ),
            write_payload_var="configs",
        )

        sub_pipeline.add_act(
            act_name=_("actuator_riak系统配置初始化"),
            act_component_code=ExecuteRiakActuatorScriptComponent.code,
            kwargs=asdict(
                RiakActKwargs(
                    get_trans_data_ip_var=ScaleOutManualContext.get_operate_nodes_var_name(),
                    bk_cloud_id=self.data["bk_cloud_id"],
                    run_as_system_user=DBA_ROOT_USER,
                    get_riak_payload_func=RiakActPayload.get_sysinit_payload.__name__,
                )
            ),
        )

        sub_pipeline.add_act(
            act_name=_("actuator_riak部署节点"),
            act_component_code=ExecuteRiakActuatorScriptComponent.code,
            kwargs=asdict(
                RiakActKwargs(
                    get_trans_data_ip_var=ScaleOutManualContext.get_operate_nodes_var_name(),
                    bk_cloud_id=self.data["bk_cloud_id"],
                    run_as_system_user=DBA_ROOT_USER,
                    get_riak_payload_func=RiakActPayload.get_deploy_trans_payload.__name__,
                )
            ),
        )

        sub_pipeline.add_act(
            act_name=_("actuator_riak节点加入集群"),
            act_component_code=ExecuteRiakActuatorScriptComponent.code,
            kwargs=asdict(
                RiakActKwargs(
                    get_trans_data_ip_var=ScaleOutManualContext.get_operate_nodes_var_name(),
                    bk_cloud_id=self.data["bk_cloud_id"],
                    run_as_system_user=DBA_ROOT_USER,
                    get_riak_payload_func=RiakActPayload.get_join_cluster_trans_payload.__name__,
                )
            ),
        )

        sub_pipeline.add_act(
            act_name=_("actuator_集群变更生效"),
            act_component_code=ExecuteRiakActuatorScriptComponent.code,
            kwargs=asdict(
                RiakActKwargs(
                    get_trans_data_ip_var=ScaleOutManualContext.get_base_node_var_name(),
                    bk_cloud_id=self.data["bk_cloud_id"],
                    run_as_system_user=DBA_ROOT_USER,
                    get_riak_payload_func=RiakActPayload.get_commit_cluster_change_payload.__name__,
                )
            ),
        )

        sub_pipeline.add_act(
            act_name=_("actuator_检查数据搬迁进度"),
            act_component_code=ExecuteRiakActuatorScriptComponent.code,
            kwargs=asdict(
                RiakActKwargs(
                    get_trans_data_ip_var=ScaleOutManualContext.get_operate_nodes_var_name(),
                    bk_cloud_id=self.data["bk_cloud_id"],
                    run_as_system_user=DBA_ROOT_USER,
                    get_riak_payload_func=RiakActPayload.get_transfer_payload.__name__,
                )
            ),
        )

        sub_pipeline.add_act(
            act_name=_("riak修改元数据"),
            act_component_code=RiakDBMetaComponent.code,
            kwargs=asdict(
                DBMetaFuncKwargs(
                    db_meta_class_func=RiakDBMeta.riak_scale_out.__name__,
                    is_update_trans_data=True,
                )
            ),
        )

        acts_list = []
        for ip in ips:
            monitor_kwargs = RiakActKwargs(
                exec_ip=ip,
                bk_cloud_id=self.data["bk_cloud_id"],
                run_as_system_user=DBA_ROOT_USER,
                get_riak_payload_func=RiakActPayload.get_install_monitor_payload.__name__,
            )
            act_info = dict()
            act_info["act_name"] = _("actuator_{}部署定时任务和riak监控".format(ip))
            act_info["act_component_code"] = ExecuteRiakActuatorScriptComponent.code
            act_info["kwargs"] = asdict(monitor_kwargs)
            acts_list.append(act_info)
        sub_pipeline.add_parallel_acts(acts_list=acts_list)

        riak_pipeline.add_sub_pipeline(sub_pipeline.build_sub_process(sub_name=_("Riak集群扩容")))
        riak_pipeline.run_pipeline(init_trans_data_class=ScaleOutManualContext())
