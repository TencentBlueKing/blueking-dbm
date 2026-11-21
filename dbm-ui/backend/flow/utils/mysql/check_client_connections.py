"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""

from typing import List, Optional

from django.utils.translation import gettext as _

from backend.components import DRSApi
from backend.db_meta.enums import InstanceStatus, MachineType, TenDBClusterSpiderRole
from backend.db_meta.exceptions import DBMetaException
from backend.db_meta.models import Cluster
from backend.flow.consts import MYSQL_SYS_USER, CheckClientConnRole, UserName
from backend.flow.utils.mysql.get_mysql_sys_user import get_mysql_sys_users


def check_client_connection(
    bk_cloud_id: int,
    instances: list,
    is_filter_sleep: bool = False,
    is_proxy: bool = False,
    filter_hosts: Optional[List[str]] = None,
    long_query_time: int = -1,
):
    """
    通过drs接口检测实例是否存在用户线程
    @param bk_cloud_id: 操作的云区域
    @param instances: 需要判断的实例列表，每个元素的str:{ip:port}
    @param is_filter_sleep: 本次检测是否过滤sleep状态的连接，默认不过滤
    @param is_proxy: 本地检测的节点是否是mysql_proxy节点， 默认不是
    @param filter_hosts: 需要忽略的来源主机列表，支持 ip 或 ip:port
    @param long_query_time: 超过多少秒的连接视为长连接，默认-1表示不按时间过滤
    """
    if is_proxy:
        # proxy 查询
        res = DRSApi.proxyrpc(
            {
                "addresses": instances,
                "cmds": ["show processlist"],
                "force": False,
                "bk_cloud_id": bk_cloud_id,
            }
        )
        return res

    # 获取内置账号名称
    admin_user_name_list = [
        UserName.ADMIN.value,
        UserName.BACKUP.value,
        UserName.MONITOR.value,
        UserName.REPL.value,
        UserName.YW.value,
        "event_scheduler",
        "system user",
    ]
    # 对于tendb-cluster集群的实例，这里不考虑过滤内置账号的session，因为执行ddl时候，实例会存在内置账号session
    # 过滤会有风险
    users = ",".join(
        ["'" + str(x) + "'" for x in MYSQL_SYS_USER + admin_user_name_list + get_mysql_sys_users(bk_cloud_id)]
    )
    if long_query_time > 0:
        is_filter_sleep = True
    if is_filter_sleep:
        check_sql = f"select * from information_schema.processlist where command != 'Sleep' and User not in ({users})"
    else:
        check_sql = f"select * from information_schema.processlist where User not in ({users})"
    if filter_hosts:
        # processlist 的 Host 为 ip:port，调用方通常只传 IP；统一按 IP 过滤
        host_ips = [str(x).split(":")[0] for x in filter_hosts]
        host_values = ",".join([f"'{ip}'" for ip in host_ips])
        check_sql += f" and SUBSTRING_INDEX(Host, ':', 1) not in ({host_values})"
    if long_query_time > 0:
        check_sql += f" and Time > {long_query_time}"
    res = DRSApi.rpc(
        {
            "addresses": instances,
            "cmds": [check_sql],
            "force": False,
            "bk_cloud_id": bk_cloud_id,
        }
    )

    return res


def get_cluster_instances_by_role(cluster_id: int, role: str) -> List[str]:
    """
    根据集群ID和角色，动态获取集群内该角色 running 状态的实例地址
    @param cluster_id: 集群id
    @param role: 检测角色，CheckClientConnRole.value（backend/spider/proxy）
    @return: ["ip:port", ...]
    """
    try:
        cluster = Cluster.objects.get(id=cluster_id)
    except Cluster.DoesNotExist:
        raise DBMetaException(message=_("集群[{}]不存在".format(cluster_id)))

    if role == CheckClientConnRole.BACKEND.value:
        # backend 角色合并 backend + remote 两类存储实例
        instances = cluster.storageinstance_set.filter(
            machine_type__in=[MachineType.BACKEND.value, MachineType.REMOTE.value],
            status=InstanceStatus.RUNNING.value,
        )
    elif role == CheckClientConnRole.SPIDER.value:
        # spider 角色只包含业务接入层（spider_master/spider_slave）
        instances = cluster.proxyinstance_set.filter(
            machine_type=MachineType.SPIDER.value,
            tendbclusterspiderext__spider_role__in=[
                TenDBClusterSpiderRole.SPIDER_MASTER.value,
                TenDBClusterSpiderRole.SPIDER_SLAVE.value,
            ],
            status=InstanceStatus.RUNNING.value,
        )
    elif role == CheckClientConnRole.PROXY.value:
        # proxy 角色指 mysql-proxy 实例
        instances = cluster.proxyinstance_set.filter(
            machine_type=MachineType.PROXY.value,
            status=InstanceStatus.RUNNING.value,
        )
    else:
        raise DBMetaException(message=_("未知的检测角色类型: {}".format(role)))

    return [inst.ip_port for inst in instances]
