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

from bamboo_engine.builder import SubProcess
from django.utils.translation import ugettext as _

from backend.db_meta.enums import ClusterEntryType, InstanceRole
from backend.db_meta.models import Cluster, ClusterEntry, StorageInstance
from backend.flow.consts import DnsOpType, ESRoleEnum, InstanceStatus
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.plugins.components.collections.es.es_clb_manage import EsClbManageComponent
from backend.flow.plugins.components.collections.es.es_dns_manage import EsDnsManageComponent
from backend.flow.plugins.components.collections.es.es_polaris_manage import EsPolarisManageComponent
from backend.flow.utils.clb_manage import get_clb_by_ip
from backend.flow.utils.dns_manage import DnsManage
from backend.flow.utils.es.es_context_dataclass import ClbKwargs, DnsKwargs, EsActKwargs, PolarisKwargs
from backend.flow.utils.polaris_manage import GetPolarisManageByName
from backend.ticket.constants import TicketType

logger = logging.getLogger("flow")

"""es选做接入节点顺序

client > hot > cold > master
"""
order_list = [
    ESRoleEnum.CLIENT.value,
    ESRoleEnum.HOT.value,
    ESRoleEnum.COLD.value,
    ESRoleEnum.MASTER.value,
]

"""单据里角色 到 实例角色的映射表

hot      -> es_datanode_hot
cold     -> es_datanode_cold
client   -> es_client
master   -> es_master
"""
es_role_to_instance_role_map = {
    ESRoleEnum.CLIENT.value: InstanceRole.ES_CLIENT.value,
    ESRoleEnum.HOT.value: InstanceRole.ES_DATANODE_HOT.value,
    ESRoleEnum.COLD.value: InstanceRole.ES_DATANODE_COLD.value,
    ESRoleEnum.MASTER.value: InstanceRole.ES_MASTER.value,
}


def _get_add_and_del_ips(old_ip_list: list, new_ip_list: list):
    """获取应该移除和添加的ip列表

    :param old_ip_list: 原来的ip列表
    :param new_ip_list: 新的ip列表

    :return 两个ip列表，第一个是应该增加的ip，第二个是应该删除的ip
    """
    add_ips = list(set(new_ip_list) - set(old_ip_list))
    del_ips = list(set(old_ip_list) - set(new_ip_list))
    return add_ips, del_ips


def _get_ips_by_es_role_from_dbmeta(cluster_id: int, role: str) -> list:
    """获取某个角色的所有ip

    :param cluster_id: 集群id
    :param role: 角色名（单据内）

    :return 角色ip列表
    """
    if role not in es_role_to_instance_role_map.keys():
        raise ValueError("{} not in [hot, cold, client, master]".format(role))
    cluster = Cluster.objects.get(id=cluster_id)
    instances = StorageInstance.objects.filter(
        cluster=cluster,
        status=InstanceStatus.RUNNING.value,
        instance_role=es_role_to_instance_role_map[role],
    )
    return [m.machine.ip for m in instances]


def _get_access_ips_from_ticket(ticket_data: dict) -> list:
    """从单据中获取接入层ip

    仅限部署单据

    :param ticket_data: 部署单据

    :return 接入层ip列表
    """
    access_ips = []
    for role in order_list:
        if ticket_data["nodes"].get(role, []):
            for node in ticket_data["nodes"][role]:
                access_ips.append(node["ip"])
            break

    if not access_ips:
        logger.error(_("单据获取到接入层ip信息为空，请联系系统管理员"))
        raise ValueError(_("获取接入层ip异常，为空列表"))

    return access_ips


def get_access_ips_from_dns(bk_cloud_id: int, bk_biz_id: int, domain: str) -> list:
    """获取域名映射的IP"""
    dns_manage = DnsManage(bk_cloud_id=bk_cloud_id, bk_biz_id=bk_biz_id)
    dns_details = dns_manage.get_domain(domain_name=domain)
    dns_ips = [item["ip"] for item in dns_details]
    return dns_ips


def _get_access_ips_from_clb(clb_ip: str) -> list:
    """获取clb后端的rs ip"""
    clb_manager = get_clb_by_ip(clb_ip)
    rs_instances = clb_manager.get_clb_rs()
    return [instance.split(":")[0] for instance in rs_instances]


def _get_access_ips_from_polaris(service_name: str) -> list:
    """获取北极星后端的rs ip"""
    polaris_manager = GetPolarisManageByName(service_name)
    rs_instances = polaris_manager.get_polaris_rs()
    return [instance.split(":")[0] for instance in rs_instances]


def _get_new_access_ips_from_dbmeta_and_ticket(ticket_data: dict, cluster_id: int) -> list:
    """从dbmeta和单据中，获取最新的接入层ip

    根据单据类型，获取最新的接入层ip，按角色优先级遍历dbmeta和单据，仅支持扩容和缩容单据
    扩容单据：最高优先级节点，取 dbmeta 与 单据 的并集
    缩容单据：最高优先级节点，取 dbmeta 与 单据 的差集

    :param ticket_data: 单据
    :param cluster_id: 集群id
    :return 最新的接入层ip列表
    """
    ticket_type = ticket_data["ticket_type"]
    if ticket_type != TicketType.ES_SCALE_UP and ticket_type != TicketType.ES_SHRINK:
        raise ValueError("ticket type not in [ES_SCALE_UP, ES_SHRINK]")
    access_ips = []
    for role in order_list:
        ips_in_ticket = []
        if role in ticket_data.get("nodes"):
            ips_in_ticket = [node["ip"] for node in ticket_data["nodes"][role]]
        ips_in_dbmeta = _get_ips_by_es_role_from_dbmeta(cluster_id=cluster_id, role=role)
        if ticket_data["ticket_type"] == TicketType.ES_SCALE_UP:
            access_ips = list(set(ips_in_ticket) | set(ips_in_dbmeta))
        elif ticket_data["ticket_type"] == TicketType.ES_SHRINK:
            access_ips = list(set(ips_in_dbmeta) - set(ips_in_ticket))
        if access_ips:
            return access_ips
    return access_ips


def get_access_ips_from_dbmeta(cluster_id: int) -> list:
    """从dbmeta中，获取接入层ip

    根据cluster id获取集群的接入层ip
    按角色优先级遍历，存在的最高优先级角色为接入节点

    :param cluster_id: 集群id

    :return 接入层ip列表
    """
    for role in order_list:
        ip_list = _get_ips_by_es_role_from_dbmeta(cluster_id=cluster_id, role=role)
        if ip_list:
            return ip_list


def gen_dns_atom_job(root_id, ticket_data, param: Dict) -> Optional[SubProcess]:
    """生成DNS管理原子任务

    根据参数构造DNS管理原子任务

    :param root_id:
    :param ticket_data: 单据
    :param param:

    :return SubProcess 子流程
    """
    dns_sub_pipeline = SubBuilder(root_id=root_id, data=ticket_data)
    if param["op_type"] == DnsOpType.CREATE:
        dns_kwargs = DnsKwargs(
            bk_cloud_id=ticket_data["bk_cloud_id"],
            dns_op_type=DnsOpType.CREATE,
            domain_name=param["domain"],
            exec_ip=param["new_ips"],
            dns_op_exec_port=param["port"],
        )
        dns_sub_pipeline.add_act(
            act_name=_("添加域名"), act_component_code=EsDnsManageComponent.code, kwargs={**asdict(dns_kwargs)}
        )
    elif param["op_type"] == DnsOpType.CLUSTER_DELETE:
        dns_kwargs = DnsKwargs(bk_cloud_id=ticket_data["bk_cloud_id"], dns_op_type=DnsOpType.CLUSTER_DELETE)
        dns_sub_pipeline.add_act(
            act_name=_("删除域名"),
            act_component_code=EsDnsManageComponent.code,
            kwargs={**asdict(dns_kwargs)},
        )
    elif param["op_type"] == DnsOpType.ADD_AND_DELETE:
        old_ips = get_access_ips_from_dns(ticket_data["bk_cloud_id"], ticket_data["bk_biz_id"], param["domain"])
        add_ips, del_ips = _get_add_and_del_ips(old_ips, param["new_ips"])
        if len(add_ips + del_ips) == 0:
            return None
        # 添加域名
        if add_ips:
            dns_kwargs = DnsKwargs(
                bk_cloud_id=ticket_data["bk_cloud_id"],
                dns_op_type=DnsOpType.CREATE,
                domain_name=param["domain"],
                exec_ip=add_ips,
                dns_op_exec_port=param["port"],
            )
            dns_sub_pipeline.add_act(
                act_name=_("添加域名"),
                act_component_code=EsDnsManageComponent.code,
                kwargs={**asdict(dns_kwargs)},
            )

        # 清理域名
        if del_ips:
            # 移除域名映射
            dns_kwargs = DnsKwargs(
                bk_cloud_id=ticket_data["bk_cloud_id"],
                dns_op_type=DnsOpType.RECYCLE_RECORD,
                domain_name=param["domain"],
                exec_ip=del_ips,
                dns_op_exec_port=param["port"],
            )
            dns_sub_pipeline.add_act(
                act_name=_("删除域名映射"),
                act_component_code=EsDnsManageComponent.code,
                kwargs={**asdict(dns_kwargs)},
            )
    return dns_sub_pipeline.build_sub_process(sub_name=_("域名变更子流程"))


def gen_clb_atom_job(root_id, ticket_data, param: Dict) -> Optional[SubProcess]:
    """
    CLB 指向管理
    """
    clb_sub_pipeline = SubBuilder(root_id=root_id, data=ticket_data)
    act_kwargs = EsActKwargs(bk_cloud_id=ticket_data["bk_cloud_id"])
    if param["op_type"] == DnsOpType.CREATE:
        clb_kwargs = ClbKwargs(
            clb_op_type=DnsOpType.CREATE,
            clb_ip=param["entry"],
            clb_op_exec_port=param["port"],
        )
        act_kwargs.exec_ip = param["new_ips"]
        clb_sub_pipeline.add_act(
            act_name=_("clb添加rs"),
            act_component_code=EsClbManageComponent.code,
            kwargs={**asdict(act_kwargs), **asdict(clb_kwargs)},
        )
    elif param["op_type"] == DnsOpType.CLUSTER_DELETE:
        clb_kwargs = ClbKwargs(
            clb_op_type=DnsOpType.CLUSTER_DELETE,
            clb_ip=param["entry"],
        )
        clb_sub_pipeline.add_act(
            act_name=_("删除clb"),
            act_component_code=EsClbManageComponent.code,
            kwargs={**asdict(act_kwargs), **asdict(clb_kwargs)},
        )
    elif param["op_type"] == DnsOpType.ADD_AND_DELETE:
        old_ips = _get_access_ips_from_clb(param["entry"])
        add_ips, del_ips = _get_add_and_del_ips(old_ips, param["new_ips"])
        if len(add_ips + del_ips) == 0:
            return None
        # 添加ip
        if add_ips:
            clb_kwargs = ClbKwargs(
                clb_op_type=DnsOpType.CREATE,
                clb_ip=param["entry"],
                clb_op_exec_port=param["port"],
            )
            act_kwargs.exec_ip = add_ips
            clb_sub_pipeline.add_act(
                act_name=_("clb添加rs"),
                act_component_code=EsClbManageComponent.code,
                kwargs={**asdict(act_kwargs), **asdict(clb_kwargs)},
            )
        # 清理ip
        if del_ips:
            clb_kwargs = ClbKwargs(
                clb_op_type=DnsOpType.RECYCLE_RECORD,
                clb_ip=param["entry"],
                clb_op_exec_port=param["port"],
            )
            act_kwargs.exec_ip = del_ips
            clb_sub_pipeline.add_act(
                act_name=_("clb剔除rs"),
                act_component_code=EsClbManageComponent.code,
                kwargs={**asdict(act_kwargs), **asdict(clb_kwargs)},
            )
    return clb_sub_pipeline.build_sub_process(sub_name=_("CLB变更子流程"))


def gen_polaris_atom_job(root_id, ticket_data, param: Dict) -> Optional[SubProcess]:
    """
    北极星 指向管理
    """
    polaris_sub_pipeline = SubBuilder(root_id=root_id, data=ticket_data)
    act_kwargs = EsActKwargs(bk_cloud_id=ticket_data["bk_cloud_id"])
    # clb添加rs
    if param["op_type"] == DnsOpType.CREATE:
        polaris_kwargs = PolarisKwargs(
            polaris_op_type=DnsOpType.CREATE,
            servicename=param["entry"],
            polaris_op_exec_port=param["port"],
        )
        act_kwargs.exec_ip = param["new_ips"]
        polaris_sub_pipeline.add_act(
            act_name=_("polaris添加rs"),
            act_component_code=EsPolarisManageComponent.code,
            kwargs={**asdict(act_kwargs), **asdict(polaris_kwargs)},
        )
    elif param["op_type"] == DnsOpType.CLUSTER_DELETE:
        polaris_kwargs = PolarisKwargs(
            polaris_op_type=DnsOpType.CLUSTER_DELETE,
            servicename=param["entry"],
        )
        polaris_sub_pipeline.add_act(
            act_name=_("删除polaris"),
            act_component_code=EsPolarisManageComponent.code,
            kwargs={**asdict(act_kwargs), **asdict(polaris_kwargs)},
        )
    elif param["op_type"] == DnsOpType.ADD_AND_DELETE:
        old_ips = _get_access_ips_from_polaris(param["entry"])
        add_ips, del_ips = _get_add_and_del_ips(old_ips, param["new_ips"])
        if len(add_ips + del_ips) == 0:
            return None
        # 添加ip
        if add_ips:
            polaris_kwargs = PolarisKwargs(
                polaris_op_type=DnsOpType.CREATE,
                servicename=param["entry"],
                polaris_op_exec_port=param["port"],
            )
            act_kwargs.exec_ip = add_ips
            polaris_sub_pipeline.add_act(
                act_name=_("polaris添加rs"),
                act_component_code=EsPolarisManageComponent.code,
                kwargs={**asdict(act_kwargs), **asdict(polaris_kwargs)},
            )
        # 清理ip
        if del_ips:
            polaris_kwargs = PolarisKwargs(
                polaris_op_type=DnsOpType.RECYCLE_RECORD,
                servicename=param["entry"],
                polaris_op_exec_port=param["port"],
            )
            act_kwargs.exec_ip = del_ips
            polaris_sub_pipeline.add_act(
                act_name=_("polaris剔除rs"),
                act_component_code=EsPolarisManageComponent.code,
                kwargs={**asdict(act_kwargs), **asdict(polaris_kwargs)},
            )
    return polaris_sub_pipeline.build_sub_process(sub_name=_("北极星变更子流程"))


def generic_manager(cluster_entry_type, root_id, ticket_data, param: Dict) -> Optional[SubProcess]:
    if cluster_entry_type == ClusterEntryType.DNS:
        return gen_dns_atom_job(root_id, ticket_data, param)
    elif cluster_entry_type == ClusterEntryType.CLB:
        return gen_clb_atom_job(root_id, ticket_data, param)
    elif cluster_entry_type == ClusterEntryType.POLARIS:
        return gen_polaris_atom_job(root_id, ticket_data, param)


def get_access_manager_atom_job(root_id, ticket_data) -> Optional[SubProcess]:
    """
        封装接入层管理原子任务。
        主要包含类型：域名、clb、北极星、域名直接指向CLB
        forward_id == null  原生DNS
        forward_id != null 跳转处理forward_id
        主要操作：增删改查
        要求：根据域名的类型，同步更新操作相关的组件

        # DNS域名记录中，端口没有实际意义，(domain,ip)为唯一键
    }
    """

    # 判断操作类型给op_type
    # 1. 部署单据：只有增加域名一个选项，op_type=DnsOpType.CREATE
    # 2. 扩容单据：DnsOpType.UPDATE
    # 3. 缩容单据：DnsOpType.RECYCLE_RECORD
    # 4. 删除单据：DnsOpType.CLUSTER_DELETE
    # 5. 不会有替换单据类型，替换单据=扩容单据+缩容单据，是两个子流程

    new_ips = []
    sub_builder_list = []
    param = {}
    ticket_type = ticket_data["ticket_type"]
    if ticket_type == TicketType.ES_APPLY:
        cluster_id = 0
        param["op_type"] = DnsOpType.CREATE
        new_ips = _get_access_ips_from_ticket(ticket_data)
        param["new_ips"] = new_ips
        param["domain"] = ticket_data["domain"]
        param["port"] = ticket_data["http_port"]
        sub_builder_list.append(generic_manager(ClusterEntryType.DNS, root_id, ticket_data, param))
    else:
        #  1. 根据cluster_id从db_meta_clusterentry表中查询出所有记录。获取所有的接入类型
        #  2. 然后根据使用的接入类型，进行对应的操作
        # op_type in [DnsOpType.CREATE、DnsOpType.RECYCLE_RECORD、DnsOpType.CLUSTER_DELETE]

        cluster_id = ticket_data["cluster_id"]
        cluster_entries = ClusterEntry.objects.filter(cluster__id=cluster_id).values()
        cluster = Cluster.objects.get(id=cluster_id)
        if ticket_type == TicketType.ES_SCALE_UP:
            param["op_type"] = DnsOpType.ADD_AND_DELETE
            new_ips = _get_new_access_ips_from_dbmeta_and_ticket(ticket_data, cluster_id)
        elif ticket_type == TicketType.ES_SHRINK:
            param["op_type"] = DnsOpType.ADD_AND_DELETE
            new_ips = _get_new_access_ips_from_dbmeta_and_ticket(ticket_data, cluster_id)
        elif ticket_type == TicketType.ES_DESTROY:
            param["op_type"] = DnsOpType.CLUSTER_DELETE

        # 获取端口号
        masters = StorageInstance.objects.filter(cluster=cluster, instance_role=InstanceRole.ES_MASTER)
        if not masters:
            message = f"the cluster({cluster_id}, {cluster.name}) has no master node"
            raise ValueError(message)
        port = masters.first().port

        param["new_ips"] = new_ips
        param["domain"] = cluster.immute_domain
        param["port"] = port
        for ce in cluster_entries:
            # 销毁集群时，原集群域名要跟着一起清理掉
            if ce["forward_to_id"] is None or (
                ce["forward_to_id"]
                and ticket_type == TicketType.ES_DESTROY
                and ce["cluster_entry_type"] == ClusterEntryType.DNS
            ):
                param["entry"] = ce["entry"]
                sub_builder = generic_manager(ce["cluster_entry_type"], root_id, ticket_data, param)
                if sub_builder:
                    sub_builder_list.append(sub_builder)
    # 子流程不能为空，否则run_pipeline会报错
    if sub_builder_list:
        sub_pipeline = SubBuilder(root_id=root_id, data=ticket_data)
        sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_builder_list)
        return sub_pipeline.build_sub_process(sub_name=_("{}-{}-dns/clb 接入层子任务".format(cluster_id, param["op_type"])))
    return None
