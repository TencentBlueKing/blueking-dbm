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
from backend.flow.consts import DnsOpType, DorisRoleEnum, ManagerOpType, ManagerServiceType
from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.doris.doris_base_flow import (
    DorisBaseFlow,
    get_all_node_ips_in_ticket,
    get_node_ips_in_ticket_by_role,
    make_meta_host_map,
)
from backend.flow.engine.bamboo.scene.doris.exceptions import (
    BeMachineCountException,
    RoleMachineCountException,
    RoleMachineCountMustException,
)
from backend.flow.plugins.components.collections.common.bigdata_manager_service import BigdataManagerComponent
from backend.flow.plugins.components.collections.doris.doris_db_meta import DorisMetaComponent
from backend.flow.plugins.components.collections.doris.doris_dns_manage import DorisDnsManageComponent
from backend.flow.plugins.components.collections.doris.exec_doris_actuator_script import (
    ExecuteDorisActuatorScriptComponent,
)
from backend.flow.plugins.components.collections.doris.get_doris_payload import GetDorisActPayloadComponent
from backend.flow.plugins.components.collections.doris.get_doris_resource import GetDorisResourceComponent
from backend.flow.plugins.components.collections.doris.rewrite_doris_config import WriteBackDorisConfigComponent
from backend.flow.plugins.components.collections.doris.trans_files import TransFileComponent
from backend.flow.utils.doris.consts import (
    DORIS_BACKEND_NOT_COUNT,
    DORIS_FOLLOWER_MUST_COUNT,
    DORIS_OBSERVER_NOT_COUNT,
)
from backend.flow.utils.doris.doris_act_payload import DorisActPayload
from backend.flow.utils.doris.doris_context_dataclass import DnsKwargs, DorisActKwargs, DorisApplyContext
from backend.flow.utils.extension_manage import BigdataManagerKwargs

logger = logging.getLogger("flow")


class DorisApplyFlow(DorisBaseFlow):
    """
    构建DORIS申请流程
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        :param root_id: 任务流程定义的root_id
        :param data: 单据传递过来的参数列表，字典格式
        """
        super().__init__(root_id, data)
        self.cluster_alias = data.get("cluster_alias")

    def __get_flow_data(self) -> dict:
        flow_data = self.get_flow_base_data()
        flow_data["cluster_alias"] = self.cluster_alias
        flow_data["nodes"] = self.nodes

        master_ip = self.nodes[DorisRoleEnum.FOLLOWER][0]["ip"]
        flow_data["master_fe_ip"] = master_ip
        host_map = make_meta_host_map(flow_data)
        flow_data["host_meta_map"] = host_map

        return flow_data

    def deploy_doris_flow(self):
        """
        定义部署DORIS集群
        :return:
        """

        doris_deploy_data = self.__get_flow_data()
        # 检查单据传参
        self.check_apply_role_ip_count(doris_deploy_data)

        doris_pipeline = Builder(root_id=self.root_id, data=doris_deploy_data)

        trans_files = GetFileList(db_type=DBType.Doris)

        act_kwargs = DorisActKwargs(bk_cloud_id=self.bk_cloud_id)
        act_kwargs.set_trans_data_dataclass = DorisApplyContext.__name__
        act_kwargs.file_list = trans_files.doris_apply(db_version=self.db_version)

        doris_pipeline.add_act(
            act_name=_("获取集群部署配置"), act_component_code=GetDorisActPayloadComponent.code, kwargs=asdict(act_kwargs)
        )

        # 获取机器资源
        doris_pipeline.add_act(
            act_name=_("获取机器信息"), act_component_code=GetDorisResourceComponent.code, kwargs=asdict(act_kwargs)
        )

        act_kwargs.exec_ip = get_all_node_ips_in_ticket(data=doris_deploy_data)
        doris_pipeline.add_act(
            act_name=_("下发DORIS介质"), act_component_code=TransFileComponent.code, kwargs=asdict(act_kwargs)
        )

        # 新节点统一初始化流程
        sub_common_pipelines = self.new_common_sub_flows(
            act_kwargs=act_kwargs,
            data=doris_deploy_data,
        )
        # 并发执行所有子流程
        doris_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_common_pipelines)

        # 启动master follower 初始化元数据
        act_kwargs.exec_ip = doris_deploy_data["master_fe_ip"]
        act_kwargs.doris_role = DorisRoleEnum.FOLLOWER
        act_kwargs.get_doris_payload_func = DorisActPayload.get_install_doris_payload.__name__
        doris_pipeline.add_act(
            act_name=_("启动Master FE {}".format(doris_deploy_data["master_fe_ip"])),
            act_component_code=ExecuteDorisActuatorScriptComponent.code,
            kwargs=asdict(act_kwargs),
        )

        act_kwargs.get_doris_payload_func = DorisActPayload.get_check_start_payload.__name__
        doris_pipeline.add_act(
            act_name=_("检查Master FE {}是否正常启动".format(doris_deploy_data["master_fe_ip"])),
            act_component_code=ExecuteDorisActuatorScriptComponent.code,
            kwargs=asdict(act_kwargs),
        )

        act_kwargs.get_doris_payload_func = DorisActPayload.get_init_grant_payload.__name__
        doris_pipeline.add_act(
            act_name=_("账号权限初始化"),
            act_component_code=ExecuteDorisActuatorScriptComponent.code,
            kwargs=asdict(act_kwargs),
        )

        act_kwargs.get_doris_payload_func = DorisActPayload.get_add_metadata_payload.__name__
        doris_pipeline.add_act(
            act_name=_("集群元数据更新"),
            act_component_code=ExecuteDorisActuatorScriptComponent.code,
            kwargs=asdict(act_kwargs),
        )
        # 扩容FE节点子流程
        sub_new_fe_pipelines = self.new_fe_sub_flows(act_kwargs=act_kwargs, data=doris_deploy_data)
        doris_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_new_fe_pipelines)
        # 扩容BE节点子流程
        sub_new_be_acts = self.new_be_sub_acts(act_kwargs=act_kwargs, data=doris_deploy_data)
        doris_pipeline.add_parallel_acts(acts_list=sub_new_be_acts)

        # 插入Doris WebUI实例信息
        manager_kwargs = BigdataManagerKwargs(
            manager_op_type=ManagerOpType.CREATE,
            db_type=DBType.Doris,
            service_type=ManagerServiceType.DORIS_WEB_UI,
            manager_ip=doris_deploy_data["master_fe_ip"],
            # 端口由界面自定义
            manager_port=self.http_port,
        )
        doris_pipeline.add_act(
            act_name=_("插入Doris WebUI实例信息"),
            act_component_code=BigdataManagerComponent.code,
            kwargs={**asdict(act_kwargs), **asdict(manager_kwargs)},
        )

        # 回写DBConfig
        doris_pipeline.add_act(
            act_name=_("回写集群配置信息"), act_component_code=WriteBackDorisConfigComponent.code, kwargs=asdict(act_kwargs)
        )

        # 添加域名
        dns_kwargs = DnsKwargs(
            bk_cloud_id=doris_deploy_data["bk_cloud_id"],
            dns_op_type=DnsOpType.CREATE,
            domain_name=self.domain,
            dns_op_exec_port=self.http_port,
        )
        doris_pipeline.add_act(
            act_name=_("添加域名"),
            act_component_code=DorisDnsManageComponent.code,
            kwargs={**asdict(act_kwargs), **asdict(dns_kwargs)},
        )

        # 添加到DBMeta并转模块
        doris_pipeline.add_act(
            act_name=_("添加到DBMeta"), act_component_code=DorisMetaComponent.code, kwargs=asdict(act_kwargs)
        )

        doris_pipeline.run_pipeline()

    @staticmethod
    def check_apply_role_ip_count(data: dict):
        # 检查 follower 数量
        follower_count = len(get_node_ips_in_ticket_by_role(data, DorisRoleEnum.FOLLOWER))
        if follower_count != DORIS_FOLLOWER_MUST_COUNT:
            logger.error(_("DorisFollower主机数不为{},当前选择数量为{}".format(DORIS_FOLLOWER_MUST_COUNT, follower_count)))
            raise RoleMachineCountMustException(
                doris_role=DorisRoleEnum.FOLLOWER, must_count=DORIS_FOLLOWER_MUST_COUNT
            )

        # 检查 observer 数量
        observer_count = len(get_node_ips_in_ticket_by_role(data, DorisRoleEnum.OBSERVER))
        if observer_count == DORIS_OBSERVER_NOT_COUNT:
            logger.error(_("DorisObserver主机数不能为{}".format(DORIS_OBSERVER_NOT_COUNT)))
            raise RoleMachineCountException(doris_role=DorisRoleEnum.OBSERVER, machine_count=DORIS_OBSERVER_NOT_COUNT)

        # 检查数据节点的数量(hot + cold > 1)
        hot_count = len(get_node_ips_in_ticket_by_role(data, DorisRoleEnum.HOT))
        cold_count = len(get_node_ips_in_ticket_by_role(data, DorisRoleEnum.COLD))
        if hot_count + cold_count == DORIS_BACKEND_NOT_COUNT:
            logger.error(_("Doris数据节点(hot+cold)数量不能为{}".format(DORIS_BACKEND_NOT_COUNT)))
            raise BeMachineCountException(must_count=DORIS_BACKEND_NOT_COUNT)
