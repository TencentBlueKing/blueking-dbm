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
import logging
from typing import List, Tuple, Union

from celery.schedules import crontab
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
from django.db.models import Q

from backend.configuration.constants import AffinityEnum, DBType
from backend.configuration.models import DBAdministrator
from backend.db_meta.enums import InstanceInnerRole, InstancePhase, MachineType
from backend.db_meta.models import Cluster, ProxyInstance, StorageInstance, StorageInstanceTuple
from backend.db_monitor.models import MySQLAutofixTicketStatus, MySQLDBHAAutofixTodo
from backend.db_periodic_task.local_tasks.mysql_autofix.dbha.group_todo import GroupedTodo, group_todo
from backend.db_periodic_task.local_tasks.mysql_autofix.dbha.tendbcluster.remote_autofix import remote_autofix
from backend.db_periodic_task.local_tasks.mysql_autofix.dbha.tendbcluster.spider_autofix import spider_autofix
from backend.db_periodic_task.local_tasks.mysql_autofix.dbha.tendbha.backend_autofix import backend_autofix
from backend.db_periodic_task.local_tasks.mysql_autofix.dbha.tendbha.proxy_autofix import proxy_autofix
from backend.db_periodic_task.local_tasks.mysql_autofix.exception import (
    MySQLAutofixException,
    MySQLDBHAAutofixBadInstanceStatus,
    MySQLDBHAAutofixUnsupportedMachineType,
)
from backend.db_periodic_task.local_tasks.register import register_periodic_task
from backend.flow.consts import InstanceStatus
from backend.ticket.models import Ticket

logger = logging.getLogger("celery")


@transaction.atomic
@register_periodic_task(run_every=crontab(minute="*"))
def mysql_dbha_autofix():
    """
    查询未结束的dbha事件分类处理
    """
    for gtd in group_todo():
        if gtd.status in [
            MySQLAutofixTicketStatus.PENDING,
            MySQLAutofixTicketStatus.RUNNING,
            MySQLAutofixTicketStatus.FAILED,  # 失败的也跟踪状态, 这样重试后才能正常记录成功
        ]:
            tk = Ticket.objects.get(pk=gtd.ticket_id)
            MySQLDBHAAutofixTodo.objects.filter(check_id=gtd.check_id).update(status=tk.status)
            continue

        try:
            td_records, instances, cluster_objs, dbas = query_base_info(gtd)
            resource_spec = calculate_resource_spec(gtd=gtd, instances=instances, cluster_objs=cluster_objs)

            if gtd.machine_type == MachineType.PROXY:
                tk = proxy_autofix(gtd=gtd, proxies=instances, dbas=dbas, resource_spec=resource_spec)
            elif gtd.machine_type == MachineType.SPIDER:
                tk = spider_autofix(gtd=gtd, spiders=instances, dbas=dbas, resource_spec=resource_spec)
            elif gtd.machine_type == MachineType.BACKEND:
                tk = backend_autofix(gtd=gtd, backends=instances, dbas=dbas, resource_spec=resource_spec)
            elif gtd.machine_type == MachineType.REMOTE:
                tk = remote_autofix(gtd=gtd, remotes=instances, dbas=dbas, resource_spec=resource_spec)
            else:  # 未实现的全都跳过, 这是保护代码
                raise MySQLDBHAAutofixUnsupportedMachineType(
                    check_id=gtd.check_id, ip=gtd.ip, machine_type=gtd.machine_type
                )

            MySQLDBHAAutofixTodo.objects.filter(check_id=gtd.check_id).update(
                ticket_id=tk.id, status=MySQLAutofixTicketStatus.PENDING
            )
        except MySQLDBHAAutofixUnsupportedMachineType as e:
            logger.error(e)
            MySQLDBHAAutofixTodo.objects.filter(check_id=gtd.check_id).update(status=MySQLAutofixTicketStatus.SKIPPED)
        except MySQLAutofixException as e:
            # ToDo warning all
            logger.error(e)
            MySQLDBHAAutofixTodo.objects.filter(check_id=gtd.check_id).update(
                status=MySQLAutofixTicketStatus.TERMINATED
            )
        except ObjectDoesNotExist as e:
            # 集群没找到. 理论上概率很低的
            logger.error(e)
            MySQLDBHAAutofixTodo.objects.filter(check_id=gtd.check_id).update(
                status=MySQLAutofixTicketStatus.TERMINATED
            )


def query_base_info(
    gtd: GroupedTodo,
) -> Tuple[List[MySQLDBHAAutofixTodo], List[Union[ProxyInstance, StorageInstance]], List[Cluster], List[str]]:
    q = Q(
        **{
            "machine__ip": gtd.ip,
            "machine__bk_cloud_id": gtd.bk_cloud_id,
            "status": InstanceStatus.UNAVAILABLE,
            "phase": InstancePhase.ONLINE,
            "machine_type": gtd.machine_type,
        }
    )
    if gtd.machine_type in [MachineType.PROXY, MachineType.SPIDER]:
        instances = list(ProxyInstance.objects.filter(q).prefetch_related("machine"))
    else:
        q &= Q(**{"instance_inner_role": InstanceInnerRole.SLAVE, "is_stand_by": True})
        instances = list(StorageInstance.objects.filter(q).prefetch_related("machine"))

    td_records = list(MySQLDBHAAutofixTodo.objects.filter(check_id=gtd.check_id))
    if len(instances) != len(td_records):
        raise MySQLDBHAAutofixBadInstanceStatus(machine_type=gtd.machine_type, ip=gtd.ip)

    cluster_objs = list(Cluster.objects.filter(pk__in=gtd.cluster_ids))

    if gtd.machine_type in [MachineType.SPIDER, MachineType.REMOTE]:
        db_type = DBType.TenDBCluster
    else:
        db_type = DBType.MySQL

    dbas = DBAdministrator.get_biz_db_type_admins(bk_biz_id=gtd.bk_biz_id, db_type=db_type)

    return td_records, instances, cluster_objs, dbas


def calculate_resource_spec(
    gtd: GroupedTodo, instances: List[Union[ProxyInstance, StorageInstance]], cluster_objs: List[Cluster]
):
    """
    计算申请新机器的地域参数
    city: 肯定和源集群同城
    zone: 得看情况了
    1. cross zone 接入层, 活着的接入层的 sub zone 随便排除一个
    2. same zone 接入层, 按故障机器 sub zone 申请
    3. cross zone 存储, 排除对端 sub zone
    4. same zone 存储, 按故障机器 sub zone 申请

    因为反亲和的问题, 这里有一个隐式要求
    一个 check_id 只能对应 一个 ip
    """
    cluster_affinity = cluster_objs[0].disaster_tolerance_level

    resource_spec = {
        "spec_id": instances[0].machine.spec_id,
        "count": 1,
        "location_spec": {
            "city": cluster_objs[0].region,
            "sub_zone_ids": [],
            "include_or_exclue": False,
        },
    }

    # 同 sub zone 按故障机器 zone 申请
    if cluster_affinity in [AffinityEnum.SAME_SUBZONE, AffinityEnum.SAME_SUBZONE_CROSS_SWTICH]:
        resource_spec["location_spec"]["include_or_exclue"] = True
        resource_spec["location_spec"]["sub_zone_ids"] = [instances[0].machine.bk_sub_zone_id]
    # 跨 sub zone 用排除语义
    # 存储排除掉对端
    # 接入层随便排除一个剩下的
    elif cluster_affinity == AffinityEnum.CROS_SUBZONE:
        resource_spec["location_spec"]["include_or_exclue"] = False
        if gtd.machine_type in [MachineType.REMOTE, MachineType.BACKEND]:
            peer_ins = StorageInstanceTuple.objects.get(receiver=instances[0]).ejector
            sub_zone_ids = [peer_ins.machine.bk_sub_zone_id]
        else:
            rest_proxies = cluster_objs[0].proxyinstance_set.exclude(machine__ip=instances[0].machine.ip)
            if gtd.machine_type == MachineType.SPIDER:
                rest_proxies = rest_proxies.filter(
                    tendbclusterspiderext__spider_role=instances[0].tendbclusterspiderext.spider_role
                )
            sub_zone_ids = [rest_proxies[0].machine.bk_sub_zone_id]

        resource_spec["location_spec"]["sub_zone_ids"] = sub_zone_ids

    else:
        del resource_spec["location_spec"]["sub_zone_ids"]
        del resource_spec["location_spec"]["include_or_exclue"]

    return resource_spec
