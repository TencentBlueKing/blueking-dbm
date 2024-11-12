"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""

from dataclasses import dataclass, field

from django.db.models import Q

from backend.db_meta.enums import ClusterType, InstanceRole
from backend.db_meta.models import Cluster
from backend.flow.consts import InstanceStatus, MachinePrivRoleMap, PrivRole
from backend.ticket.constants import TicketType


@dataclass()
class RuleDict:
    """
    定义执行通用的规则结构体
    @attributes exec_storage_instance_role_list: 添加的storage角色
    @attributes ignore_storage_instance_role_list: 忽略的storage角色
    @attributes exec_proxy_instance_role_list: 需要添加的proxy角色
    @attributes ignore_proxy_instance_role_list: 忽略的proxy角色
    @attributes is_tdbctl_primary_add: 是否给tdbctl primary添加账号
    @attributes is_tdbctl_slave_add: 是否给tdbctl slave添加账号
    """

    exec_storage_instance_role_list: list = field(default_factory=list)
    ignore_storage_instance_role_list: list = field(default_factory=list)
    exec_proxy_instance_role_list: list = field(default_factory=list)
    ignore_proxy_instance_role_list: list = field(default_factory=list)
    is_tdbctl_primary_add: bool = False


# 定义的单据类型对哪些实例角色来添加随机账号
random_job_with_ticket_map = {
    # mysql 变更SQL执行添加账号规则
    TicketType.MYSQL_IMPORT_SQLFILE: RuleDict(
        exec_storage_instance_role_list=[InstanceRole.BACKEND_MASTER, InstanceRole.ORPHAN]
    ),
    # tendb_cluster集群SQL执行添加账号规则
    TicketType.TENDBCLUSTER_IMPORT_SQLFILE: RuleDict(is_tdbctl_primary_add=True),
}


def get_instance_with_random_job(cluster: Cluster, ticket_type: TicketType):
    """
    根据单据类型以及集群信息获取到需要添加的实例
    @param cluster: 集群信息
    @param ticket_type: 单据类型
    """
    tdbctl_list = []
    proxy_instances = []
    storge_instances = []
    rule_dict = random_job_with_ticket_map.get(ticket_type, None)
    if not rule_dict:
        # 表示这类单据类型没有命中规则，默认返回所有
        storge_instances = cluster.storageinstance_set.all()
        if cluster.cluster_type == ClusterType.TenDBCluster:
            proxy_instances = cluster.proxyinstance_set.all()
            tdbctl_list.append(
                {
                    "instance": cluster.tendbcluster_ctl_primary_address(),
                    "priv_role": PrivRole.TDBCTL.value,
                    "cmdb_status": InstanceStatus.RUNNING.value,
                }
            )
    else:
        # 进入匹配环节
        storage_filter_query = Q()
        storage_exclude_query = Q()
        proxy_filter_query = Q()
        proxy_exclude_query = Q()
        if rule_dict.exec_storage_instance_role_list:
            storage_filter_query &= Q(instance_role__in=rule_dict.exec_storage_instance_role_list)
        if rule_dict.ignore_storage_instance_role_list:
            storage_exclude_query |= Q(instance_role__in=rule_dict.ignore_storage_instance_role_list)
        if rule_dict.exec_proxy_instance_role_list:
            proxy_filter_query &= Q(instance_role__in=rule_dict.exec_proxy_instance_role_list)
        if rule_dict.ignore_proxy_instance_role_list:
            proxy_exclude_query |= Q(instance_role__in=rule_dict.ignore_proxy_instance_role_list)

        if storage_filter_query.children or storage_exclude_query.children:
            storge_instances = cluster.storageinstance_set.filter(storage_filter_query).exclude(storage_exclude_query)
        if proxy_filter_query.children or proxy_exclude_query.children:
            proxy_instances = cluster.proxyinstance_set.filter(proxy_filter_query).exclude(proxy_exclude_query)
        if rule_dict.is_tdbctl_primary_add:
            tdbctl_list.append(
                {
                    "instance": cluster.tendbcluster_ctl_primary_address(),
                    "priv_role": PrivRole.TDBCTL.value,
                    "cmdb_status": InstanceStatus.RUNNING.value,
                }
            )

    return [
        {
            "instance": inst.ip_port,
            "priv_role": MachinePrivRoleMap.get(inst.machine_type),
            "cmdb_status": inst.status,
        }
        for inst in list(storge_instances) + list(proxy_instances)
    ] + tdbctl_list
