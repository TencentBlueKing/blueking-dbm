"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""

from dataclasses import dataclass

from django.db.models import Q

from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.enums import ClusterType, InstanceRole, InstanceStatus, TenDBClusterSpiderRole
from backend.db_meta.models import Cluster
from backend.flow.consts import MachinePrivRoleMap, PrivRole
from backend.ticket.constants import TicketType


@dataclass()
class RuleDict:
    """
    定义不同单据类型添加随机临时账号时的匹配规则

    列表字段的三种取值语义：
    - None（默认）：未设置，对该类型实例不做任何处理，相当于全禁止查询改实例
    - []（空列表）：exec_* 表示不限制角色查全部；ignore_* 表示不排除任何角色
    - [role1, role2]：exec_* 只查指定角色；ignore_* 排除指定角色

    @attributes exec_storage_instance_role_list: 需要添加账号的 storage 角色列表（白名单模式）
    @attributes ignore_storage_instance_role_list: 需要忽略的 storage 角色列表（黑名单模式）
    @attributes exec_proxy_instance_role_list: 需要添加账号的 proxy 角色列表（白名单模式）
    @attributes ignore_proxy_instance_role_list: 需要忽略的 proxy 角色列表（黑名单模式）
    @attributes is_only_tdbctl_primary_add: 是否给 tdbctl primary 节点添加账号
    @attributes is_all_tdbctl_add: 是否给所有 tdbctl 节点添加账号
    @attributes skip_unavailable_instance: 是否过滤掉 status=unavailable 的实例，不对其添加账号
    """

    exec_storage_instance_role_list: list = None
    ignore_storage_instance_role_list: list = None
    exec_proxy_instance_role_list: list = None
    ignore_proxy_instance_role_list: list = None
    is_only_tdbctl_primary_add: bool = False
    is_all_tdbctl_add: bool = False
    skip_unavailable_instance: bool = False


# 单据类型 -> 随机账号添加规则的映射表
# 未在此映射表中的单据类型，默认对集群所有实例添加随机账号
random_job_with_ticket_map = {
    # ---- MySQL 相关 ----
    # MySQL SQL变更执行：仅对 master 和 orphan 添加账号
    TicketType.MYSQL_IMPORT_SQLFILE: RuleDict(
        exec_storage_instance_role_list=[InstanceRole.BACKEND_MASTER, InstanceRole.ORPHAN]
    ),
    # MySQL 强制SQL变更执行：仅对 master 和 orphan 添加账号
    TicketType.MYSQL_FORCE_IMPORT_SQLFILE: RuleDict(
        exec_storage_instance_role_list=[InstanceRole.BACKEND_MASTER, InstanceRole.ORPHAN]
    ),
    # MySQL 模拟执行：仅对 master 和 orphan 添加账号
    TicketType.MYSQL_SEMANTIC_CHECK: RuleDict(
        exec_storage_instance_role_list=[InstanceRole.BACKEND_MASTER, InstanceRole.ORPHAN]
    ),
    # ---- TenDBCluster 相关 ----
    # TenDBCluster SQL变更执行：仅对 tdbctl primary 添加账号
    TicketType.TENDBCLUSTER_IMPORT_SQLFILE: RuleDict(is_only_tdbctl_primary_add=True),
    # TenDBCluster 强制SQL变更执行：仅对 tdbctl primary 添加账号
    TicketType.TENDBCLUSTER_FORCE_IMPORT_SQLFILE: RuleDict(is_only_tdbctl_primary_add=True),
    # TenDBCluster 模拟执行：仅对 tdbctl primary 添加账号
    TicketType.TENDBCLUSTER_SEMANTIC_CHECK: RuleDict(is_only_tdbctl_primary_add=True),
    # TenDBCluster TDBCTL升级：对所有 tdbctl 节点添加账号
    TicketType.TENDBCLUSTER_TDBCTL_UPGRADE: RuleDict(is_all_tdbctl_add=True),
    # tendb_cluster集群表结构修复添加账号规则
    TicketType.TENDBCLUSTER_SCHEMA_REPAIR: RuleDict(is_only_tdbctl_primary_add=True),
    # tendb_cluster集群表结构校验添加账号规则
    TicketType.TENDBCLUSTER_SCHEMA_CHECK: RuleDict(is_only_tdbctl_primary_add=True),
    # ---- 自愈单据 ----
    # DBHA 自愈后端替换：跳过 unavailable 状态的实例，避免对故障实例做无效授权
    TicketType.MYSQL_DBHA_AF_BACKEND_REPLACE: RuleDict(skip_unavailable_instance=True),
    # DBHA 自愈远程替换：跳过 unavailable 状态的实例，避免对故障实例做无效授权
    TicketType.MYSQL_DBHA_AF_REMOTE_REPLACE: RuleDict(skip_unavailable_instance=True),
}

# 定义哪些单据类型在对 unavailable 实例授权失败时需要异常退出（而非仅告警）
# 默认情况下，unavailable 实例授权失败只会产生告警，不会中断流程
# 如需开启强制校验，将对应单据类型添加到此列表即可
TICKET_TYPE_SENSITIVE_LIST = []


def get_instance_with_random_job(cluster: Cluster, ticket_type: TicketType):
    """
    根据单据类型及集群信息，获取需要添加随机临时账号的实例列表

    @param cluster: 集群对象
    @param ticket_type: 单据类型
    @return: 实例信息列表，每个元素包含 instance(ip:port)、priv_role(权限角色)、cmdb_status(实例状态)
    """
    tdbctl_list = []
    proxy_instances = []
    storage_instances = []
    rule_dict = random_job_with_ticket_map.get(ticket_type, None)
    # 只有 TenDBCluster 集群类型才需要处理 proxy 和 tdbctl 节点
    is_tendb_cluster = cluster.cluster_type == ClusterType.TenDBCluster

    if not rule_dict:
        # 未命中任何规则，默认返回集群所有实例（storage + proxy + tdbctl primary）
        # 注意：只有 TenDBCluster 集群类型才会额外添加 proxy 和 tdbctl primary 节点
        storage_instances = cluster.storageinstance_set.all()
        if is_tendb_cluster:
            proxy_instances = cluster.proxyinstance_set.all()
            tdbctl_list.append(
                {
                    "instance": cluster.tendbcluster_ctl_primary_address(),
                    "priv_role": PrivRole.TDBCTL.value,
                    # tdbctl 不是独立的 CMDB 模型实例，无法直接查询真实状态，此处硬编码为 RUNNING
                    "cmdb_status": InstanceStatus.RUNNING.value,
                }
            )
    else:
        # 根据规则构建查询条件，分别对 storage 和 proxy 进行过滤
        storage_filter_query = Q()
        storage_exclude_query = Q()
        proxy_filter_query = Q()
        proxy_exclude_query = Q()
        # 标记是否需要查询对应类型的实例，默认不查询
        # 只有当对应的 exec_*/ignore_* 字段被设置（is not None）或 skip_unavailable_instance=True 时才查询
        storage_need_query = False
        proxy_need_query = False

        # 构建 storage 白名单/黑名单过滤条件
        # is not None 表示该字段已设置（包括空列表），需要纳入查询
        # 空列表表示"不限制角色/不排除角色"，不会添加额外的 role 过滤条件
        if rule_dict.exec_storage_instance_role_list is not None:
            if rule_dict.exec_storage_instance_role_list:
                storage_filter_query &= Q(instance_role__in=rule_dict.exec_storage_instance_role_list)
            storage_need_query = True
        if rule_dict.ignore_storage_instance_role_list is not None:
            if rule_dict.ignore_storage_instance_role_list:
                storage_exclude_query |= Q(instance_role__in=rule_dict.ignore_storage_instance_role_list)
            storage_need_query = True

        # 构建 proxy 白名单/黑名单过滤条件（逻辑同 storage）
        if rule_dict.exec_proxy_instance_role_list is not None:
            if rule_dict.exec_proxy_instance_role_list:
                proxy_filter_query &= Q(instance_role__in=rule_dict.exec_proxy_instance_role_list)
            proxy_need_query = True
        if rule_dict.ignore_proxy_instance_role_list is not None:
            if rule_dict.ignore_proxy_instance_role_list:
                proxy_exclude_query |= Q(instance_role__in=rule_dict.ignore_proxy_instance_role_list)
            proxy_need_query = True

        # 过滤掉 unavailable 状态的实例（用于自愈场景，避免对故障实例做无效授权）
        if rule_dict.skip_unavailable_instance:
            storage_exclude_query |= Q(status=InstanceStatus.UNAVAILABLE.value)
            proxy_exclude_query |= Q(status=InstanceStatus.UNAVAILABLE.value)
            storage_need_query = True
            proxy_need_query = True

        # 执行 storage 查询
        # storage_need_query 为 True 表示至少有一个 storage 相关的规则被设置
        if storage_need_query:
            storage_instances = cluster.storageinstance_set.filter(storage_filter_query).exclude(storage_exclude_query)
        # 执行 proxy 查询：仅 TenDBCluster 集群类型才需要查询 proxy 实例
        if proxy_need_query and is_tendb_cluster:
            proxy_instances = cluster.proxyinstance_set.filter(proxy_filter_query).exclude(proxy_exclude_query)

        # tdbctl primary 节点添加账号
        if rule_dict.is_only_tdbctl_primary_add:
            # 注意：tendbcluster_ctl_primary_address() 内部已过滤 status=RUNNING 的 spider 来获取 primary 地址，
            # 因此间接保证了 tdbctl primary 的可用性，无需额外做 unavailable 过滤
            return [
                {
                    "instance": cluster.tendbcluster_ctl_primary_address(),
                    "priv_role": PrivRole.TDBCTL.value,
                    # tdbctl 不是独立的 CMDB 模型实例，无法直接查询真实状态，此处硬编码为 RUNNING
                    "cmdb_status": InstanceStatus.RUNNING.value,
                }
            ]

        # 所有 tdbctl 节点添加账号
        # 架构约定：tdbctl 与 spider_master 部署在同一机器上，端口 = spider.port + 1000
        # 因此通过遍历 spider_master 来推算所有 tdbctl 节点的地址
        if rule_dict.is_all_tdbctl_add:
            spider_master_query = Q(tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_MASTER.value)
            # 当开启 skip_unavailable_instance 时，排除 unavailable 状态的 spider（对应的 tdbctl 也不可用）
            if rule_dict.skip_unavailable_instance:
                spider_master_query &= ~Q(status=InstanceStatus.UNAVAILABLE.value)

            spider_masters = cluster.proxyinstance_set.filter(spider_master_query)
            for spider in spider_masters:
                tdbctl_list.append(
                    {
                        # tdbctl 端口 = spider_master 端口 + 1000（TenDBCluster 架构约定）
                        "instance": "{}{}{}".format(spider.machine.ip, IP_PORT_DIVIDER, spider.port + 1000),
                        "priv_role": PrivRole.TDBCTL.value,
                        # tdbctl 不是独立的 CMDB 模型实例，此处以对应 spider 的可用性间接代表其状态
                        "cmdb_status": InstanceStatus.RUNNING.value,
                    }
                )

    # 统一组装返回结果
    return [
        {
            "instance": inst.ip_port,
            "priv_role": MachinePrivRoleMap.get(inst.machine_type),
            "cmdb_status": inst.status,
        }
        for inst in list(storage_instances) + list(proxy_instances)
    ] + tdbctl_list
