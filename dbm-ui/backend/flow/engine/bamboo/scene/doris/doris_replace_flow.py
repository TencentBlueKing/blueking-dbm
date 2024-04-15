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
from backend.db_meta.enums import InstanceRole
from backend.flow.consts import DnsOpType, DorisRoleEnum
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.doris.doris_base_flow import (
    DorisBaseFlow,
    be_exists_in_ticket,
    fe_exists_in_ticket,
    get_all_node_ips_in_ticket,
    make_meta_host_map,
)
from backend.flow.engine.bamboo.scene.doris.exceptions import (
    ReplaceMachineCountException,
    RoleMachineCountMustException,
)
from backend.flow.plugins.components.collections.doris.doris_db_meta import DorisMetaComponent
from backend.flow.plugins.components.collections.doris.doris_dns_manage import DorisDnsManageComponent
from backend.flow.plugins.components.collections.doris.exec_doris_actuator_script import (
    ExecuteDorisActuatorScriptComponent,
)
from backend.flow.plugins.components.collections.doris.get_doris_payload import GetDorisActPayloadComponent
from backend.flow.plugins.components.collections.doris.get_doris_resource import GetDorisResourceComponent
from backend.flow.plugins.components.collections.es.trans_files import TransFileComponent
from backend.flow.utils.doris.consts import DORIS_FOLLOWER_MUST_COUNT
from backend.flow.utils.doris.doris_act_payload import DorisActPayload
from backend.flow.utils.doris.doris_context_dataclass import DnsKwargs, DorisActKwargs, DorisApplyContext
from backend.ticket.constants import TicketType

logger = logging.getLogger("flow")


class DorisReplaceFlow(DorisBaseFlow):
    """
    Doris替换流程
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        :param root_id: 任务流程定义的root_id
        :param data: 单据传递过来的参数列表，字典格式
        """
        super().__init__(root_id, data)
        self.new_nodes = data["new_nodes"]
        self.old_nodes = data["old_nodes"]

    def __get_flow_data(self) -> dict:
        flow_data = self.get_flow_base_data()
        flow_data["new_nodes"] = self.new_nodes
        flow_data["old_nodes"] = self.old_nodes
        return flow_data

    def __get_scale_up_flow_data(self) -> dict:
        flow_data = self.get_flow_base_data()
        flow_data["nodes"] = self.new_nodes
        flow_data["ticket_type"] = TicketType.DORIS_SCALE_UP.value
        follower_ips = self.get_role_ips_in_dbmeta(InstanceRole.DORIS_FOLLOWER)
        # 增加follower 数量 判断(不判断严格等于，兼容替换场景)
        if len(follower_ips) < DORIS_FOLLOWER_MUST_COUNT:
            logger.error("get follower ips from dbmeta, count is {}, invalid".format(len(follower_ips)))
            raise RoleMachineCountMustException(
                doris_role=DorisRoleEnum.FOLLOWER, must_count=DORIS_FOLLOWER_MUST_COUNT
            )

        # 随机选取follower 作为添加元数据的操作IP
        flow_data["master_fe_ip"] = follower_ips[0]
        host_map = make_meta_host_map(flow_data)
        flow_data["host_meta_map"] = host_map
        return flow_data

    def __get_shrink_flow_data(self) -> dict:
        flow_data = self.get_flow_base_data()
        flow_data["nodes"] = self.old_nodes
        flow_data["ticket_type"] = TicketType.DORIS_SHRINK.value
        # 选取 master_fe_ip 与其他流程不同，若有follower角色替换，直接获取新的follower ip作为master_fe_ip
        if DorisRoleEnum.FOLLOWER in self.new_nodes and self.new_nodes[DorisRoleEnum.FOLLOWER]:
            new_follower_ips = [node["ip"] for node in self.new_nodes[DorisRoleEnum.FOLLOWER]]
            flow_data["master_fe_ip"] = new_follower_ips[0]
        else:
            follower_ips = self.get_role_ips_in_dbmeta(InstanceRole.DORIS_FOLLOWER)
            # 增加follower 数量 判断(不判断严格等于，兼容替换场景)
            if len(follower_ips) < DORIS_FOLLOWER_MUST_COUNT:
                logger.error("get follower ips from dbmeta, count is {}, invalid".format(len(follower_ips)))
                raise RoleMachineCountMustException(
                    doris_role=DorisRoleEnum.FOLLOWER, must_count=DORIS_FOLLOWER_MUST_COUNT
                )
            # 随机选取follower 作为添加元数据的操作IP
            flow_data["master_fe_ip"] = follower_ips[0]

        return flow_data

    def replace_doris_flow(self):
        """
        定义替换Doris集群
        :return:
        """
        replace_data = self.__get_flow_data()
        # 检查 替换表单角色机器数量是否合法
        self.check_replace_role_ip_count(replace_data)

        doris_pipeline = Builder(root_id=self.root_id, data=replace_data)
        # 扩容子流程
        scale_up_data = self.__get_scale_up_flow_data()
        scale_up_sub_pipeline = SubBuilder(root_id=self.root_id, data=scale_up_data)

        trans_files = GetFileList(db_type=DBType.Doris)
        # 扩容流程使用的act_kwargs
        new_act_kwargs = DorisActKwargs(bk_cloud_id=self.bk_cloud_id)
        new_act_kwargs.set_trans_data_dataclass = DorisApplyContext.__name__
        new_act_kwargs.file_list = trans_files.doris_apply(self.db_version)

        scale_up_sub_pipeline.add_act(
            act_name=_("获取Payload"), act_component_code=GetDorisActPayloadComponent.code, kwargs=asdict(new_act_kwargs)
        )

        # 获取机器资源
        scale_up_sub_pipeline.add_act(
            act_name=_("获取机器信息"), act_component_code=GetDorisResourceComponent.code, kwargs=asdict(new_act_kwargs)
        )
        """
        new_act_kwargs.exec_ip = get_all_node_ips_in_ticket(data=scale_up_data)
        scale_up_sub_pipeline.add_act(
            act_name=_("下发DORIS介质"), act_component_code=TransFileComponent.code, kwargs=asdict(new_act_kwargs)
        )

        # 新节点统一初始化流程
        sub_common_pipelines = self.new_common_sub_flows(act_kwargs=new_act_kwargs, data=scale_up_data)
        # 并发执行所有子流程
        scale_up_sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_common_pipelines)

        new_act_kwargs.exec_ip = scale_up_data["master_fe_ip"]
        new_act_kwargs.get_doris_payload_func = DorisActPayload.get_add_nodes_metadata_payload.__name__
        scale_up_sub_pipeline.add_act(
            act_name=_("集群元数据更新"),
            act_component_code=ExecuteDorisActuatorScriptComponent.code,
            kwargs=asdict(new_act_kwargs),
        )
        """

        # 扩容FE节点子流程
        if fe_exists_in_ticket(data=scale_up_data):
            sub_new_fe_pipelines = self.new_fe_sub_flows(act_kwargs=new_act_kwargs, data=scale_up_data)
            scale_up_sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_new_fe_pipelines)

        # 扩容BE节点子流程
        if be_exists_in_ticket(data=scale_up_data):
            sub_new_be_acts = self.new_be_sub_acts(act_kwargs=new_act_kwargs, data=scale_up_data)
            scale_up_sub_pipeline.add_parallel_acts(acts_list=sub_new_be_acts)

        # 添加到DBMeta并转模块
        scale_up_sub_pipeline.add_act(
            act_name=_("添加到DBMeta"), act_component_code=DorisMetaComponent.code, kwargs=asdict(new_act_kwargs)
        )

        # 添加域名
        dns_kwargs = DnsKwargs(
            bk_cloud_id=scale_up_data["bk_cloud_id"],
            dns_op_type=DnsOpType.UPDATE,
            domain_name=self.domain,
            dns_op_exec_port=self.http_port,
        )
        scale_up_sub_pipeline.add_act(
            act_name=_("添加域名"),
            act_component_code=DorisDnsManageComponent.code,
            kwargs={**asdict(new_act_kwargs), **asdict(dns_kwargs)},
        )

        doris_pipeline.add_sub_pipeline(sub_flow=scale_up_sub_pipeline.build_sub_process(sub_name=_("扩容子流程")))

        # 缩容子流程
        shrink_data = self.__get_shrink_flow_data()
        shrink_sub_pipeline = SubBuilder(root_id=self.root_id, data=shrink_data)

        shrink_act_kwargs = DorisActKwargs(bk_cloud_id=shrink_data["bk_cloud_id"])
        shrink_act_kwargs.set_trans_data_dataclass = DorisApplyContext.__name__
        shrink_act_kwargs.file_list = trans_files.doris_actuator()
        shrink_sub_pipeline.add_act(
            act_name=_("获取缩容流程集群部署配置"),
            act_component_code=GetDorisActPayloadComponent.code,
            kwargs=asdict(shrink_act_kwargs),
        )
        # 更新dbactor介质包
        shrink_act_kwargs.exec_ip = get_all_node_ips_in_ticket(data=shrink_data)
        shrink_sub_pipeline.add_act(
            act_name=_("下发DORIS介质"), act_component_code=TransFileComponent.code, kwargs=asdict(shrink_act_kwargs)
        )

        # 缩容FE节点子流程
        if fe_exists_in_ticket(data=shrink_data):
            del_fe_pipeline = self.build_del_fe_sub_flow(data=shrink_data)
            shrink_sub_pipeline.add_sub_pipeline(del_fe_pipeline.build_sub_process(sub_name=_("缩容管理节点FE")))

        # 缩容BE节点子流程
        if be_exists_in_ticket(data=shrink_data):
            del_be_pipeline = self.build_del_be_sub_flow(data=shrink_data)
            shrink_sub_pipeline.add_sub_pipeline(del_be_pipeline.build_sub_process(sub_name=_("缩容数据节点BE")))

        shrink_ips = get_all_node_ips_in_ticket(shrink_data)
        shrink_ip_acts = []
        for ip in shrink_ips:
            # 节点清理
            shrink_act_kwargs.get_doris_payload_func = DorisActPayload.get_clean_data_payload.__name__
            shrink_act_kwargs.exec_ip = ip
            act = {
                "act_name": _("Doris集群节点清理-{}").format(ip),
                "act_component_code": ExecuteDorisActuatorScriptComponent.code,
                "kwargs": asdict(shrink_act_kwargs),
            }
            shrink_ip_acts.append(act)

        shrink_sub_pipeline.add_parallel_acts(acts_list=shrink_ip_acts)
        # 添加到DBMeta并转模块
        shrink_sub_pipeline.add_act(
            act_name=_("更新DBMeta"), act_component_code=DorisMetaComponent.code, kwargs=asdict(shrink_act_kwargs)
        )

        # 更新域名
        dns_kwargs = DnsKwargs(
            bk_cloud_id=replace_data["bk_cloud_id"],
            dns_op_type=DnsOpType.UPDATE,
            domain_name=self.domain,
            dns_op_exec_port=self.http_port,
        )
        shrink_sub_pipeline.add_act(
            act_name=_("更新域名"),
            act_component_code=DorisDnsManageComponent.code,
            kwargs={**asdict(shrink_act_kwargs), **asdict(dns_kwargs)},
        )
        doris_pipeline.add_sub_pipeline(sub_flow=shrink_sub_pipeline.build_sub_process(sub_name=_("缩容子流程")))

        doris_pipeline.run_pipeline()

    def check_replace_role_ip_count(self, data: dict):
        old_role_nodes = {}
        new_role_nodes = {}
        # 构建替换表单的角色IP数量 不检查被替换IP是否在集群内
        for role in DorisRoleEnum:
            if role not in data.get("old_nodes"):
                old_ips = []
            else:
                old_ips = [node["ip"] for node in data["old_nodes"][role]]
            old_role_nodes[role] = old_ips

            if role not in data.get("new_nodes"):
                new_ips = []
            else:
                new_ips = [node["ip"] for node in data["new_nodes"][role]]
            new_role_nodes[role] = new_ips

        for role, ips in old_role_nodes.items():
            old_ips_cnt = len(ips)
            new_ips_cnt = len(new_role_nodes[role])
            if old_ips_cnt != new_ips_cnt:
                logger.error("ticket_type: %s, role is %s, machine count mismatch.", self.ticket_type, role)
                raise ReplaceMachineCountException(doris_role=role, old_count=old_ips_cnt, new_count=new_ips_cnt)
