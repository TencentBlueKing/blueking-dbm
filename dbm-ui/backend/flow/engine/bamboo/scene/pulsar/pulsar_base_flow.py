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

from backend.configuration.constants import DOMAIN_RESOLUTION_SUPPORT
from backend.configuration.models import SystemSettings
from backend.db_meta.enums import ClusterType, InstanceRole
from backend.db_meta.models import Cluster, StorageInstance
from backend.flow.consts import ConfigTypeEnum, PulsarRoleEnum
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.engine.bamboo.scene.pulsar.exceptions import BrokerNotFoundException
from backend.flow.plugins.components.collections.pulsar.exec_actuator_script import (
    ExecutePulsarActuatorScriptComponent,
)
from backend.flow.utils.base.payload_handler import PayloadHandler
from backend.flow.utils.pulsar.consts import PulsarConfigEnum
from backend.flow.utils.pulsar.pulsar_act_payload import PulsarActPayload, get_cluster_config, get_token_by_cluster
from backend.flow.utils.pulsar.pulsar_context_dataclass import PulsarActKwargs
from backend.ticket.constants import TicketType
from backend.utils.string import str2bool

logger = logging.getLogger("flow")


class PulsarBaseFlow(object):
    # """
    # Pulsar Flow基类 仿照ES
    # """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        :param root_id: 任务流程定义的root_id
        :param data: 单据传递过来的参数列表，字典格式
        """
        self.base_flow_data = dict()
        self.zk_ips = []
        self.bookie_ips = []
        self.broker_ips = []

        # 获取角色对应实例类型
        self.role_instance_dict = {
            PulsarRoleEnum.ZooKeeper.value: InstanceRole.PULSAR_ZOOKEEPER.value,
            PulsarRoleEnum.BookKeeper.value: InstanceRole.PULSAR_BOOKKEEPER.value,
            PulsarRoleEnum.Broker.value: InstanceRole.PULSAR_BROKER.value,
        }
        self.root_id = root_id
        self.ticket_type = data.get("ticket_type")
        self.cluster_type = ClusterType.Pulsar.value
        self.created_by = data.get("created_by")
        self.ip_source = data.get("ip_source")
        self.uid = data.get("uid")
        self.bk_biz_id = data.get("bk_biz_id")
        self.nodes = data.get("nodes")

        if self.ticket_type == TicketType.PULSAR_APPLY.value:
            self.__make_new_cluster_flow_data(data)
        else:
            self.__make_cluster_op_flow_data(data)
        # 每次pulsar flow都会单独获取，支持动态更新
        self.domain_resolve_supported = str2bool(
            SystemSettings.get_setting_value(DOMAIN_RESOLUTION_SUPPORT), strict=False
        )

    def __make_new_cluster_flow_data(self, data: Optional[Dict]):
        # """
        # 新建集群 配置base_flow_data
        # """
        self.bk_cloud_id = data.get("bk_cloud_id")
        self.cluster_id = -1
        self.cluster_name = data.get("cluster_name")
        self.db_version = data.get("db_version")
        self.domain = data.get("domain")
        self.port = data.get("port")
        self.username = data.get("username")
        self.password = data.get("password")
        base_flow_data = copy.deepcopy(data)
        base_flow_data["cluster_type"] = ClusterType.Pulsar.value
        self.base_flow_data = base_flow_data

    def __make_cluster_op_flow_data(self, data: Optional[Dict]):
        # """
        # 已有集群操作 配置base_flow_data
        # """
        base_flow_data = copy.deepcopy(data)
        base_flow_data["cluster_type"] = ClusterType.Pulsar.value
        cluster = Cluster.objects.get(id=data["cluster_id"])
        self.cluster = cluster
        base_flow_data["domain"] = cluster.immute_domain
        base_flow_data["cluster_name"] = cluster.name
        base_flow_data["db_version"] = cluster.major_version
        base_flow_data["bk_biz_id"] = cluster.bk_biz_id
        base_flow_data["bk_cloud_id"] = cluster.bk_cloud_id

        dbconfig = get_cluster_config(
            bk_biz_id=str(cluster.bk_biz_id),
            cluster_domain=cluster.immute_domain,
            db_version=cluster.major_version,
            conf_type=ConfigTypeEnum.DBConf,
        )
        # dbconfig 目前返回值均为str
        base_flow_data["port"] = int(dbconfig[PulsarConfigEnum.Port])
        # pulsar-manager 用户名/密码 优先从密码服务获取
        auth_info = PayloadHandler.get_bigdata_auth_by_cluster(cluster, base_flow_data["port"])
        base_flow_data["username"] = auth_info["username"]
        base_flow_data["password"] = auth_info["password"]
        # token不再从dbconfig获取，仅从密码服务获取
        base_flow_data["token"] = get_token_by_cluster(cluster, base_flow_data["port"])

        base_flow_data["retention_time"] = int(dbconfig[PulsarRoleEnum.Broker]["defaultRetentionTimeInMinutes"])

        # 扩容需要broker ip
        self.zk_ips = list(
            cluster.storageinstance_set.filter(instance_role=InstanceRole.PULSAR_ZOOKEEPER).values_list(
                "machine__ip", flat=True
            )
        )
        # 缩容需要bookkeeper ip
        self.bookie_ips = list(
            cluster.storageinstance_set.filter(instance_role=InstanceRole.PULSAR_BOOKKEEPER).values_list(
                "machine__ip", flat=True
            )
        )
        # 获取broker 的IP列表
        broker_ips = list(
            cluster.storageinstance_set.filter(instance_role=InstanceRole.PULSAR_BROKER).values_list(
                "machine__ip", flat=True
            )
        )
        if not broker_ips:
            logger.error(f"cluster {cluster.name} found 0 broker node")
            raise BrokerNotFoundException
        else:
            self.broker_ips = broker_ips
        # 获取ip 及 域名 映射
        base_flow_data["zk_host_map"] = self.make_zk_host_map_from_dbmeta(dbconfig=dbconfig)
        # 获取ZK域名，用于bookie broker 配置
        base_flow_data["zk_hosts_str"] = ",".join(base_flow_data["zk_host_map"].values())
        self.base_flow_data = base_flow_data

    def new_nodes_common_sub_flow_list(self, act_kwargs: PulsarActKwargs, data: dict) -> list:
        # """
        # 新增节点common操作sub_flow 数组
        # 包括
        #     节点初始化
        #     解压缩介质包
        #     安装supervisor
        #     添加hosts
        # 操作
        # """
        sub_pipelines = []
        for role, role_nodes in self.nodes.items():
            act_kwargs.role = role
            for node in role_nodes:
                sub_pipeline = SubBuilder(root_id=self.root_id, data=data)
                ip = node["ip"]
                act_kwargs.exec_ip = ip
                # 初始化节点
                act_kwargs.get_pulsar_payload_func = PulsarActPayload.get_sys_init_payload.__name__
                sub_pipeline.add_act(
                    act_name=_("节点初始化-{}").format(ip),
                    act_component_code=ExecutePulsarActuatorScriptComponent.code,
                    kwargs=asdict(act_kwargs),
                )
                act_kwargs.get_pulsar_payload_func = PulsarActPayload.get_decompress_pkg_payload.__name__
                sub_pipeline.add_act(
                    act_name=_("解压缩介质包-{}").format(ip),
                    act_component_code=ExecutePulsarActuatorScriptComponent.code,
                    kwargs=asdict(act_kwargs),
                )
                # 安装supervisor
                act_kwargs.get_pulsar_payload_func = PulsarActPayload.get_install_supervisor_payload.__name__
                sub_pipeline.add_act(
                    act_name=_("安装supervisor-{}").format(ip),
                    act_component_code=ExecutePulsarActuatorScriptComponent.code,
                    kwargs=asdict(act_kwargs),
                )
                if not self.domain_resolve_supported:
                    act_kwargs.get_pulsar_payload_func = PulsarActPayload.get_add_hosts_payload.__name__
                    sub_pipeline.add_act(
                        act_name=_("仅非DNS环境使用-添加zookeeper hosts"),
                        act_component_code=ExecutePulsarActuatorScriptComponent.code,
                        kwargs=asdict(act_kwargs),
                    )

                sub_pipelines.append(sub_pipeline.build_sub_process(sub_name=_("安装Pulsar-{}-common子流程".format(ip))))

        return sub_pipelines

    # 不包含 初始化hosts
    def new_common_sub_flow(self, act_kwargs: PulsarActKwargs, data: dict, ips: list, role: PulsarRoleEnum) -> list:
        # """
        # 新增节点common操作sub_flow 数组
        # 包括
        #     节点初始化
        #     解压缩介质包
        #     安装supervisor
        # 操作
        # """
        sub_pipelines = []
        act_kwargs.role = role
        for ip in ips:
            sub_pipeline = SubBuilder(root_id=self.root_id, data=data)
            act_kwargs.exec_ip = ip
            # 初始化节点
            act_kwargs.get_pulsar_payload_func = PulsarActPayload.get_sys_init_payload.__name__
            sub_pipeline.add_act(
                act_name=_("节点初始化-{}").format(ip),
                act_component_code=ExecutePulsarActuatorScriptComponent.code,
                kwargs=asdict(act_kwargs),
            )
            act_kwargs.get_pulsar_payload_func = PulsarActPayload.get_decompress_pkg_payload.__name__
            sub_pipeline.add_act(
                act_name=_("解压缩介质包-{}").format(ip),
                act_component_code=ExecutePulsarActuatorScriptComponent.code,
                kwargs=asdict(act_kwargs),
            )
            # 安装supervisor
            act_kwargs.get_pulsar_payload_func = PulsarActPayload.get_install_supervisor_payload.__name__
            sub_pipeline.add_act(
                act_name=_("安装supervisor-{}").format(ip),
                act_component_code=ExecutePulsarActuatorScriptComponent.code,
                kwargs=asdict(act_kwargs),
            )
            sub_pipelines.append(sub_pipeline.build_sub_process(sub_name=_("安装Pulsar-{}-common子流程".format(ip))))
        return sub_pipelines

    def new_bookkeeper_act_list(self, act_kwargs: PulsarActKwargs) -> list:
        bookie_act_list = []
        for node in self.nodes[PulsarRoleEnum.BookKeeper]:
            bookie_ip = node["ip"]
            act_kwargs.exec_ip = bookie_ip
            act_kwargs.get_pulsar_payload_func = PulsarActPayload.get_install_bookkeeper_payload.__name__
            bookie_act = {
                "act_name": _("安装bookkeeper-{}".format(bookie_ip)),
                "act_component_code": ExecutePulsarActuatorScriptComponent.code,
                "kwargs": asdict(act_kwargs),
            }
            bookie_act_list.append(bookie_act)

        return bookie_act_list

    def new_broker_act_list(self, act_kwargs: PulsarActKwargs) -> list:
        broker_act_list = []
        for node in self.nodes[PulsarRoleEnum.Broker]:
            broker_ip = node["ip"]
            act_kwargs.exec_ip = broker_ip
            act_kwargs.get_pulsar_payload_func = PulsarActPayload.get_install_broker_payload.__name__
            broker_act = {
                "act_name": _("安装broker-{}").format(broker_ip),
                "act_component_code": ExecutePulsarActuatorScriptComponent.code,
                "kwargs": asdict(act_kwargs),
            }
            broker_act_list.append(broker_act)
        return broker_act_list

    def del_broker_act_list(self, act_kwargs: PulsarActKwargs) -> list:
        del_broker_acts = []
        for node in self.nodes[PulsarRoleEnum.Broker]:
            broker_ip = node["ip"]
            act_kwargs.exec_ip = broker_ip
            act_kwargs.role = PulsarRoleEnum.Broker
            act_kwargs.get_pulsar_payload_func = PulsarActPayload.get_stop_process_payload.__name__
            act = {
                "act_name": _("缩容Pulsar-Broker-{}").format(broker_ip),
                "act_component_code": ExecutePulsarActuatorScriptComponent.code,
                "kwargs": asdict(act_kwargs),
            }
            del_broker_acts.append(act)
        return del_broker_acts

    def del_bookkeeper_act_list(self, act_kwargs: PulsarActKwargs, data: dict) -> list:
        # """
        # 缩容多个bookie节点操作集合 数组
        # 需要分bookie 执行
        # 包括
        #     检查broker配置
        #     检查NameSpace配置
        #     检查未复制ledger
        #     停止BookKeeper
        #     退役BookKeeper
        # 操作
        # """
        sub_pipelines = []
        old_bookie_num = len(self.bookie_ips)
        for node in self.nodes[PulsarRoleEnum.BookKeeper]:
            sub_pipeline = SubBuilder(root_id=self.root_id, data=data)
            bookie_ip = node["ip"]
            act_kwargs.cur_bookie_num = old_bookie_num
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
            act_kwargs.exec_ip = self.broker_ips[0]
            act_kwargs.get_pulsar_payload_func = PulsarActPayload.get_check_namespace_config_payload.__name__
            sub_pipeline.add_act(
                act_name=_("检查NameSpace配置-{}").format(act_kwargs.exec_ip),
                act_component_code=ExecutePulsarActuatorScriptComponent.code,
                kwargs=asdict(act_kwargs),
            )
            act_kwargs.exec_ip = bookie_ip
            act_kwargs.get_pulsar_payload_func = PulsarActPayload.get_check_under_replicated_payload.__name__
            sub_pipeline.add_act(
                act_name=_("检查未复制ledger-{}").format(bookie_ip),
                act_component_code=ExecutePulsarActuatorScriptComponent.code,
                kwargs=asdict(act_kwargs),
            )
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
            sub_pipelines.append(
                sub_pipeline.build_sub_process(sub_name=_("缩容Pulsar-BookKeeper-{}-子流程".format(bookie_ip)))
            )
            old_bookie_num = old_bookie_num - 1
        return sub_pipelines

    def get_all_node_ips_from_dbmeta(self) -> list:
        # dbmeta 仅提供storage_instance, 若后续Pulsar存储dbmeta非storage_instance返回会有问题
        return list(self.cluster.storageinstance_set.filter().values_list("machine__ip", flat=True))

    def get_all_ips_by_role_from_dbmeta(self) -> dict:
        role_ips_dict = dict()
        for role in PulsarRoleEnum:
            ips = [
                instance.machine.ip
                for instance in StorageInstance.objects.filter(
                    cluster=self.cluster, instance_role=self.role_instance_dict[role]
                )
            ]
            role_ips_dict[role] = ips
        return role_ips_dict

    def make_zk_host_map_from_dbmeta(self, dbconfig: dict) -> dict:
        zk_host_map = dict()
        # get zk id from db config
        for i in range(len(self.zk_ips)):
            zk_ip = dbconfig[f"zk_ip_{i}"]
            zk_host_map[zk_ip] = f"zk-{i}-{self.cluster.immute_domain}"
        return zk_host_map

    def make_zk_host_map(self) -> dict:
        zk_host_map = dict()
        for i, zk_node in enumerate(self.nodes[PulsarRoleEnum.ZooKeeper]):
            zk_host_map[zk_node["ip"]] = f"zk-{i}-{self.domain}"

        return zk_host_map


# 获取ZK对应my_id, 与zk域名生成相关
def get_zk_id_from_host_map(zk_host_map: dict, zk_ip: str) -> int:
    zk_domain = zk_host_map[zk_ip]
    return int(zk_domain[-1])


def get_all_node_ips_in_ticket(data: dict) -> list:
    ips = []
    for role in data.get("nodes"):
        ips.extend(get_node_ips_in_ticket_by_role(data, role))
    return ips


def get_node_ips_in_ticket_by_role(data: dict, role: str) -> list:
    if role not in data.get("nodes"):
        return []
    return [node["ip"] for node in data["nodes"][role]]
