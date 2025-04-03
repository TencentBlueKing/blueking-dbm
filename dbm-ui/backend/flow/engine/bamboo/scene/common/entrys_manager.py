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

from backend.db_meta.enums import ClusterEntryRole, ClusterEntryType
from backend.db_meta.models import Cluster, ClusterEntry
from backend.flow.consts import DnsOpType
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.plugins.components.collections.common.mysql_clb_manage import MySQLClbManageComponent
from backend.flow.plugins.components.collections.mysql.dns_manage import MySQLDnsManageComponent
from backend.flow.utils.mysql.mysql_act_dataclass import (
    ClbKwargs,
    CreateDnsKwargs,
    DeleteClusterDnsKwargs,
    RecycleDnsRecordKwargs,
)

logger = logging.getLogger("flow")


def BuildDNSManageSubflow(root_id, ticket_data, op_type: str, param: Dict) -> Optional[SubProcess]:
    """
    原生DNS域名管理
    """
    dns_sub_pipeline = SubBuilder(root_id=root_id, data=ticket_data)
    # 添加域名
    if op_type == DnsOpType.CREATE:
        dns_kwargs = CreateDnsKwargs(
            bk_cloud_id=param["bk_cloud_id"],
            add_domain_name=param["entry"],
            dns_op_exec_port=param["port"],
            exec_ip=param["add_ips"],
        )
        dns_sub_pipeline.add_act(
            act_name=_("添加域名映射"),
            act_component_code=MySQLDnsManageComponent.code,
            kwargs={**asdict(dns_kwargs)},
        )
    # 清理域名
    if op_type == DnsOpType.RECYCLE_RECORD:
        dns_kwargs = RecycleDnsRecordKwargs(
            bk_cloud_id=param["bk_cloud_id"], dns_op_exec_port=param["port"], exec_ip=param["del_ips"]
        )
        dns_sub_pipeline.add_act(
            act_name=_("删除域名映射"),
            act_component_code=MySQLDnsManageComponent.code,
            kwargs={**asdict(dns_kwargs)},
        )

    if op_type == DnsOpType.CLUSTER_DELETE:
        is_only_delete_slave_entry = param.get("is_only_delete_slave_entry", False)
        dns_kwargs = DeleteClusterDnsKwargs(
            bk_cloud_id=param["bk_cloud_id"],
            delete_cluster_id=param["cluster_id"],
            is_only_delete_slave_domain=is_only_delete_slave_entry,
        )
        dns_sub_pipeline.add_act(
            act_name=_("删除域名"),
            act_component_code=MySQLDnsManageComponent.code,
            kwargs={**asdict(dns_kwargs)},
        )

    return dns_sub_pipeline.build_sub_process(sub_name=_("域名变更子流程"))


def BuildCLBManageSubflow(root_id, ticket_data, op_type: str, param: Dict) -> Optional[SubProcess]:
    """
    CLB 指向管理
    """
    clb_sub_pipeline = SubBuilder(root_id=root_id, data=ticket_data)
    # clb添加rs
    if op_type == DnsOpType.CREATE:
        dns_kwargs = ClbKwargs(
            clb_op_type=DnsOpType.CREATE,
            clb_ip=param["entry"],
            clb_op_exec_port=param["port"],
        )
        dns_kwargs.exec_ip = param["add_ips"]
        clb_sub_pipeline.add_act(
            act_name=_("clb添加rs"),
            act_component_code=MySQLClbManageComponent.code,
            kwargs={**asdict(dns_kwargs)},
        )

    # clb删除rs
    if op_type == DnsOpType.RECYCLE_RECORD:
        dns_kwargs = ClbKwargs(
            clb_op_type=DnsOpType.RECYCLE_RECORD,
            clb_ip=param["entry"],
            clb_op_exec_port=param["port"],
        )
        dns_kwargs.exec_ip = param["del_ips"]
        clb_sub_pipeline.add_act(
            act_name=_("clb剔除rs"),
            act_component_code=MySQLClbManageComponent.code,
            kwargs={**asdict(dns_kwargs)},
        )
    # 删除clb
    if op_type == DnsOpType.CLUSTER_DELETE:
        dns_kwargs = ClbKwargs(
            clb_op_type=DnsOpType.CLUSTER_DELETE,
            clb_ip=param["entry"],
        )
        clb_sub_pipeline.add_act(
            act_name=_("删除clb"),
            act_component_code=MySQLClbManageComponent.code,
            kwargs={**asdict(dns_kwargs)},
        )

    return clb_sub_pipeline.build_sub_process(sub_name=_("CLB变更子流程"))


def generic_manager(cluster_entry_type, root_id, ticket_data, op_type: str, param: Dict) -> Optional[SubProcess]:
    if cluster_entry_type == ClusterEntryType.DNS:
        return BuildDNSManageSubflow(root_id, ticket_data, op_type, param)
    if cluster_entry_type == ClusterEntryType.CLB:
        return BuildCLBManageSubflow(root_id, ticket_data, op_type, param)


def BuildEntrysManageSubflow(root_id, ticket_data, op_type: str, param: Dict) -> Optional[SubProcess]:
    """
        封装接入层管理原子任务。
        主要包含类型：dns、clb、北极星、CLB域名 （clb.xxxx.x.xx.x.db）、 主域名直接指向CLB
        dns: forward_id == null 原生dns； forward_id != null 跳转处理forward_id
        主要操作：增删改查，不包含创建
        要求：根据域名的类型，同步更新操作相关的组件

        # nodes域名注意！！！
        # DNS域名记录中，端口没有实际意义，(domain,ip)为唯一键，如果有多条记录，还会报错。这个地方设置起始端口的值就行。

        Args:
        param (Dict): {
            "cluster_id",       必传
            "port": 30000,
            "add_ips": [],
            "del_ips": [],
            "entry_role": []
    }
    """
    #  1. 根据cluster_id从db_meta_clusterentry表中查询出所有记录。看下这个集群都有些啥接入组件
    #  2. 然后根据使用的接入组件，进行对应的操作
    # op_type in [DnsOpType.CREATE、DnsOpType.RECYCLE_RECORD、DnsOpType.CLUSTER_DELETE]

    # 如果指定了角色，那么就需要操作指定node域名。 否则默认只对proxy操作
    # 一般只有两种场景需要指定role: 1、 nodes域名的操作。 2、 操作对应的全部域名
    if "entry_role" in param:
        entry_role = param["entry_role"]
    # 这个地方，历史残留原因。 有些enter的默认值是master_entry
    else:
        entry_role = [
            ClusterEntryRole.MASTER_ENTRY.value,
        ]

    cluster_id = param["cluster_id"]
    cluster_enterys = ClusterEntry.objects.filter(cluster__id=cluster_id, role__in=entry_role).values()
    cluster = Cluster.objects.get(id=cluster_id)
    # 老的rediscluster集群可能不存在nodes域名
    if not cluster_enterys:
        return None

    sub_builder_list = []
    sub_process_name = ""
    for ce in cluster_enterys:
        if ce["forward_to_id"]:
            # 有forward_to_id, 这这条记录不需要操作，只需要操作forward_to_id对应的记录
            continue
        param["entry"] = ce["entry"]
        param["bk_cloud_id"] = cluster.bk_cloud_id
        sub_builder_list.append(generic_manager(ce["cluster_entry_type"], root_id, ticket_data, op_type, param))
        if ce["cluster_entry_type"] == ClusterEntryType.CLB:
            sub_process_name += "clb/"
        if ce["cluster_entry_type"] == ClusterEntryType.DNS:
            sub_process_name += "dns/"
    sub_pipeline = SubBuilder(root_id=root_id, data=ticket_data)
    sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_builder_list)
    return sub_pipeline.build_sub_process(sub_name=_("{}-{}-{} 接入层子任务".format(cluster_id, op_type, sub_process_name)))
