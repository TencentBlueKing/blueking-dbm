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

from backend.components import DBConfigApi
from backend.components.dbconfig.constants import ConfType, FormatType, LevelName, ReqType
from backend.db_meta.enums import ClusterType, InstanceRole
from backend.db_meta.enums.cluster_entry_role import ClusterEntryRole
from backend.db_meta.models import Cluster, StorageInstance
from backend.flow.consts import LevelInfoEnum, NameSpaceEnum, VmRoleEnum
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.plugins.components.collections.vm.exec_vm_actuator_script import ExecuteVmActuatorScriptComponent
from backend.flow.utils.vm.vm_act_payload import VmActPayload
from backend.flow.utils.vm.vm_context_dataclass import VmActKwargs
from backend.ticket.constants import TicketType

logger = logging.getLogger("flow")


def make_meta_host_map(data: dict) -> dict:
    host_map = {}
    for role in data["nodes"]:
        ips = [node["ip"] for node in data["nodes"][role]]
        host_map[role] = ips

    return host_map


class VmBaseFlow(object):
    """
    VM Flow基类
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        :param root_id: 任务流程定义的root_id
        :param data: 单据传递过来的参数列表，字典格式
        """
        self.root_id = root_id
        self.ticket_type = data.get("ticket_type")
        self.cluster_type = ClusterType.Vm.value
        self.created_by = data.get("created_by")
        self.ip_source = data.get("ip_source")
        self.uid = data.get("uid")
        self.bk_biz_id = data.get("bk_biz_id")
        self.nodes = data.get("nodes")
        # 仅 IP来源为资源池时，会有传值
        self.resource_spec = data.get("resource_spec")
        if self.ticket_type == TicketType.VM_APPLY:
            self.cluster_id = -1
            self.cluster_name = data.get("cluster_name")
            self.db_version = data.get("db_version")
            self.vminsert_domain = data.get("vminsert_domain")
            self.vmselect_domain = data.get("vmselect_domain")
            self.vminsert_port = data.get("vminsert_port")
            self.vmselect_port = data.get("vmselect_port")
            self.bk_cloud_id = data.get("bk_cloud_id")
            self.auth = data.get("auth")
            self.retention_period = data.get("retention_period")
            self.replication_factor = data.get("replication_factor")
            self.username = data.get("username")
            self.password = data.get("password")
        else:
            self.cluster_id = data.get("cluster_id")
            cluster = Cluster.objects.get(id=self.cluster_id)
            slave_dns = cluster.clusterentry_set.get(role=ClusterEntryRole.SLAVE_ENTRY).entry
            self.cluster_name = cluster.name
            self.db_version = cluster.major_version
            self.vminsert_domain = cluster.immute_domain
            self.vmselect_domain = slave_dns
            self.vminsert_port = self.get_vminsert_port_in_dbmeta(cluster=cluster)
            self.vmselect_port = self.get_vmselect_port_in_dbmeta(cluster=cluster)
            self.bk_cloud_id = cluster.bk_cloud_id
            # 从dbconfig获取配置信息
            dbconfig = DBConfigApi.query_conf_item(
                {
                    "bk_biz_id": str(self.bk_biz_id),
                    "level_name": LevelName.CLUSTER,
                    "level_value": self.vminsert_domain,
                    "level_info": {"module": LevelInfoEnum.TendataModuleDefault},
                    "conf_file": self.db_version,
                    "conf_type": ConfType.DBCONF,
                    "namespace": NameSpaceEnum.Vm,
                    "format": FormatType.MAP_LEVEL,
                    "method": ReqType.GENERATE_AND_PUBLISH,
                }
            )
            self.retention_period = dbconfig["content"][VmRoleEnum.VMSTORAGE.value]["retentionPeriod"]
            self.replication_factor = dbconfig["content"][VmRoleEnum.VMINSERT.value]["replicationFactor"]
            # auth_info = PayloadHandler.get_bigdata_auth_by_cluster(cluster, 0)

            self.username = data.get("username", "")
            self.password = data.get("password", "")

    def get_flow_base_data(self) -> dict:
        flow_data = {
            "bk_cloud_id": self.bk_cloud_id,
            "bk_biz_id": self.bk_biz_id,
            "ticket_type": self.ticket_type,
            "cluster_id": self.cluster_id,
            "cluster_name": self.cluster_name,
            "ip_source": self.ip_source,
            "db_version": self.db_version,
            "username": self.username,
            "password": self.password,
            "vminsert_port": self.vminsert_port,
            "vmselect_port": self.vmselect_port,
            "uid": self.uid,
            "created_by": self.created_by,
            "vminsert_domain": self.vminsert_domain,
            "vmselect_domain": self.vmselect_domain,
            "resource_spec": self.resource_spec,
            "retention_period": self.retention_period,
            "replication_factor": self.replication_factor,
        }
        return flow_data

    def __get_flow_data(self) -> dict:
        pass

    def get_vminsert_port_in_dbmeta(self, cluster: Cluster) -> int:
        self.cluster_name = cluster.name
        vminserts = StorageInstance.objects.filter(cluster=cluster, instance_role=InstanceRole.VM_INSERT)
        if not vminserts:
            logger.info("found 0 vminsert node")
            raise Exception(f"the cluster({self.cluster_id}, {self.cluster_name}) has no vminsert node")
        return vminserts.first().port

    def get_vmselect_port_in_dbmeta(self, cluster: Cluster) -> int:
        self.cluster_name = cluster.name
        vmselects = StorageInstance.objects.filter(cluster=cluster, instance_role=InstanceRole.VM_SELECT)
        if not vmselects:
            logger.info("found 0 vmselect node")
            raise Exception(f"the cluster({self.cluster_id}, {self.cluster_name}) has no vmselect node")
        return vmselects.first().port

    def get_all_node_ips_in_dbmeta(self) -> list:
        cluster = Cluster.objects.get(id=self.cluster_id)
        storage_ips = list(set(StorageInstance.objects.filter(cluster=cluster).values_list("machine__ip", flat=True)))
        return storage_ips

    def get_role_ips_in_dbmeta(self, role: InstanceRole) -> list:
        cluster = Cluster.objects.get(id=self.cluster_id)
        role_ips = list(cluster.storageinstance_set.filter(instance_role=role).values_list("machine__ip", flat=True))
        return role_ips

    def new_common_sub_flows(self, act_kwargs: VmActKwargs, data: dict) -> list:
        """
        # 新增节点common操作sub_flow 数组
        # 包括
        #     节点初始化
        #     解压缩介质包
        #     渲染集群配置
        #     安装supervisor
        # 操作
        """
        sub_pipelines = []
        for role, role_nodes in data["nodes"].items():
            for node in role_nodes:
                sub_pipeline = SubBuilder(root_id=self.root_id, data=data)
                ip = node["ip"]
                # 节点初始化
                act_kwargs.get_vm_payload_func = VmActPayload.get_sys_init_payload.__name__
                act_kwargs.vm_role = role
                act_kwargs.exec_ip = ip
                sub_pipeline.add_act(
                    act_name=_("节点初始化-{}").format(ip),
                    act_component_code=ExecuteVmActuatorScriptComponent.code,
                    kwargs=asdict(act_kwargs),
                )
                # 解压缩
                act_kwargs.get_vm_payload_func = VmActPayload.get_decompress_vm_pkg_payload.__name__
                sub_pipeline.add_act(
                    act_name=_("解压缩介质包-{}").format(ip),
                    act_component_code=ExecuteVmActuatorScriptComponent.code,
                    kwargs=asdict(act_kwargs),
                )
                # 安装supervisor
                act_kwargs.get_vm_payload_func = VmActPayload.get_install_supervisor_payload.__name__
                act_kwargs.exec_ip = ip
                sub_pipeline.add_act(
                    act_name=_("安装supervisor-{}").format(ip),
                    act_component_code=ExecuteVmActuatorScriptComponent.code,
                    kwargs=asdict(act_kwargs),
                )
                sub_pipelines.append(sub_pipeline.build_sub_process(sub_name=_("安装Vm {}-{}子流程").format(role, ip)))
        return sub_pipelines

    def new_vmstorage_act_list(self, act_kwargs: VmActKwargs) -> list:
        """
        安装vmstorage的子流程
        """
        vm_act_list = []
        for node in self.nodes[VmRoleEnum.VMSTORAGE]:
            vm_ip = node["ip"]
            act_kwargs.exec_ip = vm_ip
            act_kwargs.get_vm_payload_func = VmActPayload.get_install_vmstorage_payload.__name__
            vm_act = {
                "act_name": _("安装vmstorage-{}").format(vm_ip),
                "act_component_code": ExecuteVmActuatorScriptComponent.code,
                "kwargs": asdict(act_kwargs),
            }
            vm_act_list.append(vm_act)
        return vm_act_list

    def new_vminsert_act_list(self, act_kwargs: VmActKwargs) -> list:
        """
        安装vminsert的子流程
        """
        vm_act_list = []
        for node in self.nodes[VmRoleEnum.VMINSERT]:
            vm_ip = node["ip"]
            act_kwargs.exec_ip = vm_ip
            act_kwargs.get_vm_payload_func = VmActPayload.get_install_vminsert_payload.__name__
            vm_act = {
                "act_name": _("安装vminsert-{}").format(vm_ip),
                "act_component_code": ExecuteVmActuatorScriptComponent.code,
                "kwargs": asdict(act_kwargs),
            }
            vm_act_list.append(vm_act)
        return vm_act_list

    def new_vminstall_act_list(self, role: str, act_kwargs: VmActKwargs, data: dict) -> list:
        """
        安装指定角色的子流程
        """
        vm_act_list = []
        for node in data["nodes"][role]:
            vm_ip = node["ip"]
            act_kwargs.exec_ip = vm_ip
            # 动态构建函数名
            get_payload_func_name = f"get_install_{role}_payload"
            # 使用 getattr 来获取实际的函数对象的名字
            act_kwargs.get_vm_payload_func = getattr(VmActPayload, get_payload_func_name).__name__
            vm_act = {
                "act_name": _(f"安装{role}-{vm_ip}"),
                "act_component_code": ExecuteVmActuatorScriptComponent.code,
                "kwargs": asdict(act_kwargs),
            }
            vm_act_list.append(vm_act)
        return vm_act_list


def get_node_ips_in_ticket_by_role(data: dict, role: str) -> list:
    if role not in data.get("nodes"):
        return []
    return [node["ip"] for node in data["nodes"][role]]


def get_all_node_ips_in_ticket(data: dict) -> list:
    ips = []
    for role in data.get("nodes"):
        ips.extend(get_node_ips_in_ticket_by_role(data, role))
    return ips


def role_exists_in_ticket(role: str, data: dict) -> bool:
    return role in data["nodes"]


def get_vm_ips(role: str, data: dict) -> list:
    """
    生成vm ip数据
    :return:
    """
    ticket_type = data["ticket_type"]
    # 当为TicketType.VM_APPLY时，从ticket_data返回
    if ticket_type == TicketType.VM_APPLY:
        return [node["ip"] for node in data["nodes"].get(role, [])]

    # 当为 TicketType.VM_SCALE_UP 或 TicketType.VM_SHRINK 时，从dbmeta获取
    if ticket_type in (TicketType.VM_SCALE_UP, TicketType.VM_SHRINK, TicketType.VM_REPLACE):
        cluster = Cluster.objects.get(id=data["cluster_id"])
        db_ips = set(cluster.storageinstance_set.filter(instance_role=role).values_list("machine__ip", flat=True))

        # 当为TicketType.VM_SCALE_UP时，取ticket_data和数据库的合集
        if ticket_type == TicketType.VM_SCALE_UP:
            ticket_ips = set(node["ip"] for node in data["nodes"].get(role, []))
            return list(db_ips | ticket_ips)  # Union of db_ips and ticket_ips

        # 当为TicketType.VM_SHRINK时，取数据库和ticket_data的差集
        elif ticket_type == TicketType.VM_SHRINK:
            ticket_ips = set(node["ip"] for node in data["nodes"].get(role, []))
            return list(db_ips - ticket_ips)  # Difference of db_ips and ticket_ips

        # 当为TicketType.VM_REPLACE时，取数据库跟new_nodes的合集再减去old_nodes
        elif ticket_type == TicketType.VM_REPLACE:
            new_nodes_ips = set(node["ip"] for node in data["new_nodes"].get(role, []))
            old_nodes_ips = set(node["ip"] for node in data["old_nodes"].get(role, []))
            return list(
                (db_ips | new_nodes_ips) - old_nodes_ips
            )  # Union of db_ips and new_nodes_ips, then difference of old_nodes_ips
    # 如果ticket_type不是上述任何一种，返回空列表
    return []


def get_vmstorage_ipstr(port: int, addresses: list) -> str:
    """
    生成vminsert和vmselect的storage地址
    格式: ip1:port,ip2:port,ip3:port
    vminsert传8400
    vmselect传8401
    """
    return ",".join(f"{address}:{port}" for address in addresses)
