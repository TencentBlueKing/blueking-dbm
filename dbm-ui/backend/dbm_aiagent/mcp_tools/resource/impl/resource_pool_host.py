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

from django.utils.translation import gettext_lazy as _

from backend.db_dirty.constants import MachineEventType, PoolType
from backend.db_dirty.handlers import DBDirtyMachineHandler
from backend.db_dirty.models import DirtyMachine
from backend.db_services.cmdb.biz import get_resource_biz
from backend.db_services.dbresource.exceptions import ResourceReturnException
from backend.db_services.dbresource.handlers import ResourceHandler

logger = logging.getLogger("root")


def resource_import_host(params, username):
    """通过主机ip或者主机名称把主机导入资源池"""

    # 对于传过来的信息先去cc查询到处于空闲机的主机
    conditions = []
    query_params = {}
    query_field_map = {"ip": "bk_host_innerip", "ip_v6": "bk_host_innerip_v6", "host_name": "bk_host_name"}

    for key in params:
        if key in query_field_map and params[key]:
            conditions.extend(
                [
                    {"field": query_field_map[key], "operator": "equal", "value": value}
                    for value in params[key].split(",")
                ]
            )

    if conditions:
        query_params["conditions"] = conditions
    query_params["page"] = {"start": 0, "page_size": 100}

    # 查询DBA空闲机模块的meta，构造查询空闲机参数的node_list
    bk_biz_id = params.get("bk_biz_id")
    origin_host_infos = ResourceHandler.list_dba_hosts(query_params, bk_biz_id)["data"]
    # 查询到的数据排除已经存在于资源池的主机
    host_infos = [host for host in origin_host_infos if not host["occupancy"]]
    if not host_infos:
        return []

    ticket_data = {
        "bk_biz_id": bk_biz_id,
        "for_biz": params["for_biz"],
        "label_names": [],
        "labels": [],
        "resource_type": params["resource_type"],
        "hosts": host_infos,
    }
    return ResourceHandler.resource_import(ticket_data, username)


def get_dirty_machine(params):
    query_params = {}
    query_count = 0
    if "ip" in params:
        ips = params["ip"].split(",")
        query_params["ip__in"] = ips
        query_count += len(ips)
    if "host_id" in params:
        bk_host_ids = [int(host_id) for host_id in params["host_id"].split(",")]
        query_count += len(bk_host_ids)
        query_params["bk_host_id__in"] = bk_host_ids
    hosts_qs = DirtyMachine.objects.filter(**query_params)
    return hosts_qs, query_count


def resource_undo_import(params, username):
    hosts_qs, undo_count = get_dirty_machine(params)
    if not hosts_qs:
        raise ResourceReturnException(_("未获取到需要撤销导入的主机信息, 请检查主机ip或者主机id是否正确"))

    # 检查主机数量 & 仍处于资源池
    if hosts_qs.count() != undo_count:
        raise ResourceReturnException(_("需撤销的主机部分不存在资源池，请确保所有主机都在资源池中"))
    if list(set(hosts_qs.values_list("pool", flat=True))) != [PoolType.Resource]:
        raise ResourceReturnException(_("请保证需要撤销的主机处于资源池中"))

    data = {
        "event": "undo_import",
        "remark": "",
        "hosts": [
            {
                "bk_biz_id": params["bk_biz_id"],
                "bk_cloud_id": host.bk_cloud_id,
                "bk_host_id": host.bk_host_id,
                "ip": host.ip,
            }
            for host in hosts_qs
        ],
    }
    resp = ResourceHandler.resource_delete(data, username, hosts_qs)

    return resp["data"]


def resource_delete(params, username):
    hosts_qs, delete_count = get_dirty_machine(params)
    if not hosts_qs:
        raise ResourceReturnException(_("未获取到需要删除的主机信息, 请检查主机ip或者主机id是否正确"))

    # 检查主机数量 & 仍处于待回收池
    if hosts_qs.count() != delete_count:
        raise ResourceReturnException(_("需删除主机部分不存在待回收池中，请确保所有主机都在待回收池中"))
    if list(set(hosts_qs.values_list("pool", flat=True))) != [PoolType.Recycle]:
        raise ResourceReturnException(_("请保证需要删除的主机处于待回收池中"))
    bk_host_ids = [host.bk_host_id for host in hosts_qs]
    return DBDirtyMachineHandler.transfer_hosts_to_pool(
        username, bk_host_ids, PoolType.Recycle, PoolType.Recycled, recycle_hosts=hosts_qs
    )


def resource_transfer_pool(params, username):
    hosts_qs, transfer_count = get_dirty_machine(params)
    if not hosts_qs:
        raise ResourceReturnException(_("未获取到需要转移的主机信息, 请检查主机ip或者主机id是否正确"))

    host_ids = [host.bk_host_id for host in hosts_qs]
    pool_list = list(set(hosts_qs.values_list("pool", flat=True)))

    # 资源池 ---> 故障池/待回收池
    if params["target"] in [PoolType.Fault, PoolType.Recycle] and pool_list == [PoolType.Resource]:
        event_pool_map = {PoolType.Fault: MachineEventType.ToFault, PoolType.Recycle: MachineEventType.ToRecycle}
        data = {
            "event": event_pool_map[params["target"]],
            "remark": "",
            "hosts": [
                {
                    "bk_biz_id": get_resource_biz(),
                    "bk_cloud_id": host.bk_cloud_id,
                    "bk_host_id": host.bk_host_id,
                    "ip": host.ip,
                }
                for host in hosts_qs
            ],
        }
        resp = ResourceHandler.resource_delete(data, username, hosts_qs)

        return resp["data"]

    # 故障池 ---> 待回收池
    elif params["target"] == PoolType.Recycle and pool_list == [PoolType.Fault]:
        return DBDirtyMachineHandler.transfer_hosts_to_pool(
            username, host_ids, PoolType.Fault, PoolType.Recycle, recycle_hosts=hosts_qs
        )

    else:
        message = _("主机转移失败！暂不支持的转移类型或主机未都处在同一池中")

    return {"message": message}
