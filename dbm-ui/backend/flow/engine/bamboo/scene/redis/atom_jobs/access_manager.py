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
from typing import Dict

from django.utils.translation import ugettext as _

from backend.db_meta.models import ClusterEntry
from backend.flow.consts import AccessType, DnsOpType
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.plugins.components.collections.common.clb_manage import RedisClbManageComponent
from backend.flow.plugins.components.collections.common.polaris_manage import RedisPolarisManageComponent
from backend.flow.plugins.components.collections.redis.dns_manage import RedisDnsManageComponent
from backend.flow.utils.redis.redis_context_dataclass import ActKwargs, ClbKwargs, DnsKwargs, PolarisKwargs

logger = logging.getLogger("flow")


def DNSManagerAtomJob(root_id, ticket_data, act_kwargs: ActKwargs, param: Dict) -> SubBuilder:
    """
    原生DNS域名管理
    """
    dns_sub_pipeline = SubBuilder(root_id=root_id, data=ticket_data)
    # 添加域名
    if param["op_type"] == DnsOpType.CREATE:
        dns_kwargs = DnsKwargs(
            dns_op_type=DnsOpType.CREATE,
            add_domain_name=param["entry"],
            dns_op_exec_port=param["port"],
        )
        act_kwargs.exec_ip = param["add_ips"]
        dns_sub_pipeline.add_act(
            act_name=_("添加域名映射"),
            act_component_code=RedisDnsManageComponent.code,
            kwargs={**asdict(act_kwargs), **asdict(dns_kwargs)},
        )
    # 清理域名
    if param["op_type"] == DnsOpType.RECYCLE_RECORD:
        dns_kwargs = DnsKwargs(
            dns_op_type=DnsOpType.RECYCLE_RECORD,
            dns_op_exec_port=param["port"],
        )
        act_kwargs.exec_ip = param["del_ips"]
        dns_sub_pipeline.add_act(
            act_name=_("删除域名映射"),
            act_component_code=RedisDnsManageComponent.code,
            kwargs={**asdict(act_kwargs), **asdict(dns_kwargs)},
        )

    if param["op_type"] == DnsOpType.CLUSTER_DELETE:
        dns_kwargs = DnsKwargs(dns_op_type=DnsOpType.CLUSTER_DELETE, delete_cluster_id=param["cluster_id"])
        dns_sub_pipeline.add_act(
            act_name=_("删除域名"),
            act_component_code=RedisDnsManageComponent.code,
            kwargs={**asdict(act_kwargs), **asdict(dns_kwargs)},
        )

    return dns_sub_pipeline.build_sub_process(sub_name=_("域名变更子流程"))


def CLBManagerAtomJob(root_id, ticket_data, act_kwargs: ActKwargs, param: Dict) -> SubBuilder:
    """
    CLB 指向管理
    """
    clb_sub_pipeline = SubBuilder(root_id=root_id, data=ticket_data)
    # clb添加rs
    if param["op_type"] == DnsOpType.CREATE:
        dns_kwargs = ClbKwargs(
            clb_op_type=DnsOpType.CREATE,
            clb_ip=param["entry"],
            clb_op_exec_port=param["port"],
        )
        act_kwargs.exec_ip = param["add_ips"]
        clb_sub_pipeline.add_act(
            act_name=_("clb添加rs"),
            act_component_code=RedisClbManageComponent.code,
            kwargs={**asdict(act_kwargs), **asdict(dns_kwargs)},
        )

    # clb删除rs
    if param["op_type"] == DnsOpType.RECYCLE_RECORD:
        dns_kwargs = ClbKwargs(
            clb_op_type=DnsOpType.RECYCLE_RECORD,
            clb_ip=param["entry"],
            clb_op_exec_port=param["port"],
        )
        act_kwargs.exec_ip = param["del_ips"]
        clb_sub_pipeline.add_act(
            act_name=_("clb剔除rs"),
            act_component_code=RedisClbManageComponent.code,
            kwargs={**asdict(act_kwargs), **asdict(dns_kwargs)},
        )

    if param["op_type"] == DnsOpType.CLUSTER_DELETE:
        dns_kwargs = ClbKwargs(
            clb_op_type=DnsOpType.CLUSTER_DELETE,
            clb_ip=param["entry"],
        )
        clb_sub_pipeline.add_act(
            act_name=_("删除clb"),
            act_component_code=RedisClbManageComponent.code,
            kwargs={**asdict(act_kwargs), **asdict(dns_kwargs)},
        )

    return clb_sub_pipeline.build_sub_process(sub_name=_("CLB变更子流程"))


def PolarisManagerAtomJob(root_id, ticket_data, act_kwargs: ActKwargs, param: Dict) -> SubBuilder:
    """ "
    北极星 指向管理
    """
    polaris_sub_pipeline = SubBuilder(root_id=root_id, data=ticket_data)
    # clb添加rs
    if param["op_type"] == DnsOpType.CREATE:
        dns_kwargs = PolarisKwargs(
            polaris_op_type=DnsOpType.CREATE,
            servicename=param["entry"],
            polaris_op_exec_port=param["port"],
        )
        act_kwargs.exec_ip = param["add_ips"]
        polaris_sub_pipeline.add_act(
            act_name=_("polaris添加rs"),
            act_component_code=RedisPolarisManageComponent.code,
            kwargs={**asdict(act_kwargs), **asdict(dns_kwargs)},
        )

    # clb删除rs
    if param["op_type"] == DnsOpType.RECYCLE_RECORD:
        dns_kwargs = PolarisKwargs(
            polaris_op_type=DnsOpType.RECYCLE_RECORD,
            servicename=param["entry"],
            polaris_op_exec_port=param["port"],
        )
        act_kwargs.exec_ip = param["del_ips"]
        polaris_sub_pipeline.add_act(
            act_name=_("polaris剔除rs"),
            act_component_code=RedisPolarisManageComponent.code,
            kwargs={**asdict(act_kwargs), **asdict(dns_kwargs)},
        )

    if param["op_type"] == DnsOpType.CLUSTER_DELETE:
        dns_kwargs = PolarisKwargs(
            polaris_op_type=DnsOpType.CLUSTER_DELETE,
            servicename=param["entry"],
        )
        polaris_sub_pipeline.add_act(
            act_name=_("删除polaris"),
            act_component_code=RedisPolarisManageComponent.code,
            kwargs={**asdict(act_kwargs), **asdict(dns_kwargs)},
        )

    return polaris_sub_pipeline.build_sub_process(sub_name=_("北极星变更子流程"))


def generic_manager(cluster_entry_type, root_id, ticket_data, act_kwargs: ActKwargs, param: Dict) -> SubBuilder:
    if cluster_entry_type == AccessType.DNS:
        return DNSManagerAtomJob(root_id, ticket_data, act_kwargs, param)
    if cluster_entry_type == AccessType.CLB:
        return CLBManagerAtomJob(root_id, ticket_data, act_kwargs, param)
    if cluster_entry_type == AccessType.POLARIS:
        return PolarisManagerAtomJob(root_id, ticket_data, act_kwargs, param)


def AccessManagerAtomJob(root_id, ticket_data, act_kwargs: ActKwargs, param: Dict) -> SubBuilder:
    """
        封装接入层管理原子任务。
        主要包含类型：dns、clb、北极星、CLB域名 （clb.xxxx.x.xx.x.db）、 主域名直接指向CLB
        dns: forward_id == null 原生dns； forward_id != null 跳转处理forward_id
        主要操作：增删改查，不包含创建
        要求：根据域名的类型，同步更新操作相关的组件

        Args:
        param (Dict): {
            "cluster_id",       必传
            "op_type": "",      必传
            "port": 30000,
            "add_ips": [],
            "del_ips": [],
    }
    """
    #  1. 根据cluster_id从db_meta_clusterentry表中查询出所有记录。看下这个集群都有些啥接入组件
    #  2. 然后根据使用的接入组件，进行对应的操作
    # op_type in [DnsOpType.CREATE、DnsOpType.RECYCLE_RECORD、DnsOpType.CLUSTER_DELETE]

    cluster_id = param["cluster_id"]
    cluster_enterys = ClusterEntry.objects.filter(cluster__id=cluster_id).values()
    sub_builder_list = []
    for ce in cluster_enterys:
        if ce["forward_to_id"]:
            # 有forward_to_id, 这这条记录不需要操作，只需要操作forward_to_id对应的记录
            continue
        param["entry"] = ce["entry"]
        sub_builder_list.append(generic_manager(ce["cluster_entry_type"], root_id, ticket_data, act_kwargs, param))

    sub_pipeline = SubBuilder(root_id=root_id, data=ticket_data)
    sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_builder_list)
    return sub_pipeline.build_sub_process(sub_name=_("dns/clb 接入层子任务"))
