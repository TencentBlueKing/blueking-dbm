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
import logging.config
from dataclasses import asdict
from typing import Dict, Optional

from django.utils.translation import ugettext as _

from backend.db_meta.enums import InstanceRole
from backend.db_meta.models import Cluster
from backend.flow.consts import DnsOpType, PulsarRoleEnum
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.engine.bamboo.scene.pulsar.pulsar_base_flow import PulsarBaseFlow, get_zk_id_from_host_map
from backend.flow.plugins.components.collections.pulsar.blank_schedule_service import BlankScheduleComponent
from backend.flow.plugins.components.collections.pulsar.exec_actuator_script import (
    ExecutePulsarActuatorScriptComponent,
)
from backend.flow.plugins.components.collections.pulsar.pulsar_zk_dns_manage import PulsarZkDnsManageComponent
from backend.flow.utils.pulsar.consts import PULSAR_ROLE_ALL, PULSAR_ZOOKEEPER_SERVICE_PORT
from backend.flow.utils.pulsar.pulsar_act_payload import PulsarActPayload
from backend.flow.utils.pulsar.pulsar_context_dataclass import PulsarActKwargs, ZkDnsKwargs
from backend.ticket.constants import TicketType

logger = logging.getLogger("flow")


class PulsarOperationFlow(PulsarBaseFlow):
    """
    构建Pulsar变更操作流程的常用类，封装扩缩容替换等子流程
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递过来的参数列表，是dict格式
        """
        super().__init__(root_id, data)
        self.data = data

    def get_replace_zk_nodes(self, ticket_data: dict):
        # """
        # 替换时 获取单据中替换ZK 节点信息
        # make field old_zk_ips & new_zk_ips
        # only effect zookeeper
        # """
        old_zk_ips = []
        new_zk_ips = []
        if PulsarRoleEnum.ZooKeeper.value in ticket_data["old_nodes"]:
            old_zk_ips = [node["ip"] for node in ticket_data["old_nodes"][PulsarRoleEnum.ZooKeeper]]
            new_zk_ips = [node["ip"] for node in ticket_data["new_nodes"][PulsarRoleEnum.ZooKeeper]]
        self.base_flow_data["old_zk_ips"] = old_zk_ips
        self.base_flow_data["new_zk_ips"] = new_zk_ips

    def replace_zookeeper_pipeline_list(self, act_kwargs: PulsarActKwargs, data: dict) -> list:
        # """
        # 替换多个zookeeper节点操作集合 数组
        # 需要分zk节点 串行 执行
        # 包括
        #     停止ZK服务
        #     更新ZK域名
        #     更新ZK映射（DNS不可用环境）
        #     新增ZK映射（DNS不可用环境）
        #     安装新节点ZK
        # 操作
        # """
        sub_pipelines = []
        # ZK 一一对应
        for i in range(len(data["old_zk_ips"])):
            old_zk_ip = data["old_zk_ips"][i]
            new_zk_ip = data["new_zk_ips"][i]
            sub_pipeline = SubBuilder(root_id=self.root_id, data=data)
            act_kwargs.get_pulsar_payload_func = PulsarActPayload.get_stop_process_payload.__name__
            act_kwargs.role = PULSAR_ROLE_ALL
            act_kwargs.exec_ip = old_zk_ip
            sub_pipeline.add_act(
                act_name=_("停止ZooKeeper服务-{}").format(old_zk_ip),
                act_component_code=ExecutePulsarActuatorScriptComponent.code,
                kwargs=asdict(act_kwargs),
            )
            zk_dns_kwargs = ZkDnsKwargs(
                bk_cloud_id=data["bk_cloud_id"],
                dns_op_type=DnsOpType.UPDATE,
                domain_name=data["domain"],
                dns_op_exec_port=PULSAR_ZOOKEEPER_SERVICE_PORT,
                zk_host_map=data["zk_host_map"],
                old_zk_ip=old_zk_ip,
                new_zk_ip=new_zk_ip,
            )
            sub_pipeline.add_act(
                act_name=_("更新ZK域名"),
                act_component_code=PulsarZkDnsManageComponent.code,
                kwargs={**asdict(act_kwargs), **asdict(zk_dns_kwargs)},
            )
            # begin 仅测试 用于DNS不可用环境
            act_kwargs.exec_ip = self.get_all_node_ips_from_dbmeta()
            act_kwargs.get_pulsar_payload_func = PulsarActPayload.get_modify_hosts_payload.__name__
            if act_kwargs.zk_host_map:
                new_zk_host_map = copy.deepcopy(act_kwargs.zk_host_map)
            else:
                new_zk_host_map = copy.deepcopy(data["zk_host_map"])
            replace_domain = new_zk_host_map.pop(old_zk_ip)
            new_zk_host_map[new_zk_ip] = replace_domain
            act_kwargs.zk_host_map = new_zk_host_map
            sub_pipeline.add_act(
                act_name=_("更新ZK映射"),
                act_component_code=ExecutePulsarActuatorScriptComponent.code,
                kwargs={**asdict(act_kwargs)},
            )
            act_kwargs.exec_ip = new_zk_ip
            act_kwargs.get_pulsar_payload_func = PulsarActPayload.get_add_hosts_payload.__name__
            sub_pipeline.add_act(
                act_name=_("添加ZK映射"),
                act_component_code=ExecutePulsarActuatorScriptComponent.code,
                kwargs={**asdict(act_kwargs)},
            )
            # 获取ZK对应的my id
            my_id = get_zk_id_from_host_map(data["zk_host_map"], old_zk_ip)
            act_kwargs.zk_my_id = my_id
            act_kwargs.exec_ip = new_zk_ip
            act_kwargs.get_pulsar_payload_func = PulsarActPayload.get_install_zookeeper_payload.__name__
            sub_pipeline.add_act(
                act_name=_("安装zookeeper-{}").format(new_zk_ip),
                act_component_code=ExecutePulsarActuatorScriptComponent.code,
                kwargs=asdict(act_kwargs),
            )
            sub_pipelines.append(
                sub_pipeline.build_sub_process(sub_name=_("替换Pulsar-ZooKeeper-{}-子流程".format(old_zk_ip)))
            )

        return sub_pipelines

    def update_role_ips_from_dbmeta(self):
        # """
        # 替换时 实时更新dbmeta 节点信息
        # only effect self.variables, zk_ips,bookie_ips,broker_ips
        # """
        cluster = Cluster.objects.get(id=self.base_flow_data["cluster_id"])
        self.zk_ips = list(
            cluster.storageinstance_set.filter(instance_role=InstanceRole.PULSAR_ZOOKEEPER).values_list(
                "machine__ip", flat=True
            )
        )
        self.bookie_ips = list(
            cluster.storageinstance_set.filter(instance_role=InstanceRole.PULSAR_BOOKKEEPER).values_list(
                "machine__ip", flat=True
            )
        )
        self.broker_ips = list(
            cluster.storageinstance_set.filter(instance_role=InstanceRole.PULSAR_BROKER).values_list(
                "machine__ip", flat=True
            )
        )

    def update_nodes_replace(self, ticket_data: dict, ticket_type: TicketType) -> dict:
        # """
        # 替换时 更新nodes信息，便于执行扩容/缩容 流程
        # only effect roles broker,bookkeeper, not include zookeeper
        # """
        flow_data = copy.deepcopy(self.base_flow_data)
        if ticket_type == TicketType.PULSAR_SCALE_UP:
            flow_data["ticket_type"] = TicketType.PULSAR_SCALE_UP.value
            node_type = "new_nodes"
        else:
            flow_data["ticket_type"] = TicketType.PULSAR_SHRINK.value
            node_type = "old_nodes"
        self.nodes = dict()
        # 仅替换bookkeeper broker角色
        if PulsarRoleEnum.Broker.value in ticket_data[node_type]:
            self.nodes[PulsarRoleEnum.Broker.value] = ticket_data[node_type][PulsarRoleEnum.Broker.value]
        if PulsarRoleEnum.BookKeeper.value in ticket_data[node_type]:
            self.nodes[PulsarRoleEnum.BookKeeper.value] = ticket_data[node_type][PulsarRoleEnum.BookKeeper.value]
        flow_data["nodes"] = self.nodes
        return flow_data

    def del_bookkeeper_sub_flow(self, act_kwargs: PulsarActKwargs, data: dict, cur_bookie_num: int) -> SubBuilder:

        data["shrink_bookie_ips"] = [node["ip"] for node in data["nodes"][PulsarRoleEnum.BookKeeper]]
        sub_pipeline = SubBuilder(root_id=self.root_id, data=data)
        # 检查剩余bookie数量 >= broker配置参数
        act_kwargs.cur_bookie_num = cur_bookie_num
        logger.info("test-richie:{}".format(cur_bookie_num))
        broker_acts = []
        act_kwargs.get_pulsar_payload_func = PulsarActPayload.get_check_broker_config_payload.__name__
        for broker_ip in self.broker_ips:
            act_kwargs.exec_ip = broker_ip
            act = {
                "act_name": _("检查Broker配置-{}").format(broker_ip),
                "act_component_code": ExecutePulsarActuatorScriptComponent.code,
                "kwargs": asdict(act_kwargs),
            }
            broker_acts.append(act)
        sub_pipeline.add_parallel_acts(acts_list=broker_acts)

        # 选取任一台broker 检查namespace
        # 检查剩余bookie数量 >= namespace默认值
        act_kwargs.exec_ip = self.broker_ips[0]
        act_kwargs.get_pulsar_payload_func = PulsarActPayload.get_check_namespace_config_payload.__name__
        sub_pipeline.add_act(
            act_name=_("检查NameSpace配置-{}").format(act_kwargs.exec_ip),
            act_component_code=ExecutePulsarActuatorScriptComponent.code,
            kwargs=asdict(act_kwargs),
        )

        # 检查是否有under replicated
        check_under_replicated_acts = []
        for bookie_ip in data["shrink_bookie_ips"]:
            act_kwargs.exec_ip = bookie_ip
            act_kwargs.get_pulsar_payload_func = PulsarActPayload.get_check_under_replicated_payload.__name__
            act = {
                "act_name": _("检查未复制ledger-{}").format(bookie_ip),
                "act_component_code": ExecutePulsarActuatorScriptComponent.code,
                "kwargs": asdict(act_kwargs),
            }
            check_under_replicated_acts.append(act)

        sub_pipeline.add_parallel_acts(acts_list=check_under_replicated_acts)

        # 检查ledger metadata
        check_ledger_metadata_acts = []
        act_kwargs.get_pulsar_payload_func = PulsarActPayload.get_check_ledger_metadata_payload.__name__
        for bookie_ip in data["shrink_bookie_ips"]:
            act_kwargs.exec_ip = bookie_ip
            act = {
                "act_name": _("检查Ledger Metadata-{}").format(bookie_ip),
                "act_component_code": ExecutePulsarActuatorScriptComponent.code,
                "kwargs": asdict(act_kwargs),
            }
            check_ledger_metadata_acts.append(act)
        sub_pipeline.add_parallel_acts(acts_list=check_ledger_metadata_acts)

        # 修改bookie参数为只读
        bookie_acts = []
        act_kwargs.get_pulsar_payload_func = PulsarActPayload.get_set_bookie_read_only_payload.__name__
        for bookie_ip in data["shrink_bookie_ips"]:
            act_kwargs.exec_ip = bookie_ip
            act = {
                "act_name": _("修改Bookie参数为ReadOnly-{}").format(bookie_ip),
                "act_component_code": ExecutePulsarActuatorScriptComponent.code,
                "kwargs": asdict(act_kwargs),
            }
            bookie_acts.append(act)
        sub_pipeline.add_parallel_acts(acts_list=bookie_acts)

        # 滚动重启bookie
        for bookie_ip in data["shrink_bookie_ips"]:
            act_kwargs.exec_ip = bookie_ip
            act_kwargs.get_pulsar_payload_func = PulsarActPayload.get_reboot_process_payload.__name__
            act_kwargs.role = PulsarRoleEnum.BookKeeper
            # 是否需要考虑设置每次重启的间隔时间
            sub_pipeline.add_act(
                act_name=_("滚动重启BookKeeper-{}").format(bookie_ip),
                act_component_code=ExecutePulsarActuatorScriptComponent.code,
                kwargs=asdict(act_kwargs),
            )

        # TODO 等待一个周期，默认为数据过期时间
        sub_pipeline.add_act(
            act_name=_("等待数据过期"),
            act_component_code=BlankScheduleComponent.code,
            kwargs=asdict(act_kwargs),
        )

        # 停止BookKeeper服务 + 退役BookKeeper
        for bookie_ip in data["shrink_bookie_ips"]:
            act_kwargs.get_pulsar_payload_func = PulsarActPayload.get_stop_process_payload.__name__
            act_kwargs.role = PulsarRoleEnum.BookKeeper
            sub_pipeline.add_act(
                act_name=_("停止BookKeeper服务-{}").format(bookie_ip),
                act_component_code=ExecutePulsarActuatorScriptComponent.code,
                kwargs=asdict(act_kwargs),
            )
            act_kwargs.get_pulsar_payload_func = PulsarActPayload.get_decommission_bookie_payload.__name__
            sub_pipeline.add_act(
                act_name=_("退役BookKeeper-{}").format(bookie_ip),
                act_component_code=ExecutePulsarActuatorScriptComponent.code,
                kwargs=asdict(act_kwargs),
            )
        return sub_pipeline
