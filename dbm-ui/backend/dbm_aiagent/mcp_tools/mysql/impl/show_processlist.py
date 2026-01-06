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
from collections import defaultdict
from typing import Dict, List

from backend.components import DRSApi
from backend.db_meta.enums import ClusterType, MachineType
from backend.db_meta.models import Cluster, Machine, ProxyInstance, StorageInstance
from backend.dbm_aiagent.mcp_tools.exceptions import DBMMcpBaseException, DBMMcpNotSupportClusterTypeException


def show_cluster_processlist_count(cluster_type: ClusterType, cluster_domain: str) -> List:
    cluster_obj = Cluster.objects.get(cluster_type=cluster_type, immute_domain=cluster_domain)

    if cluster_type == ClusterType.TenDBSingle:
        return __show_tendbsingle_processlist(cluster_obj, True)
    elif cluster_type == ClusterType.TenDBHA:
        return __show_tendbha_processlist(cluster_obj, True)
    elif cluster_type == ClusterType.TenDBCluster:
        return __show_tendbcluster_processlist(cluster_obj, True)
    else:
        raise DBMMcpNotSupportClusterTypeException(cluster_type=cluster_type)


def show_instances_processlist_detail(bk_cloud_id: int, instances: List[str]) -> List:
    res = []
    for ins in instances:
        ip, port = ins.split(":")
        m = Machine.objects.get(bk_cloud_id=bk_cloud_id, ip=ip)

        if m.machine_type == MachineType.PROXY:
            r = __show_processlist_on_proxy(bk_cloud_id, [ins], False)
        else:
            r = __show_processlist_on_mysql(bk_cloud_id, [ins], m.machine_type, False)

        res.append(r)

    return res


def __show_processlist(bk_cloud_id: int, addresses: List[str], machine_type: MachineType) -> Dict:
    if not addresses:
        return {}

    if machine_type == MachineType.PROXY:
        admin_addresses = []
        for ele in addresses:
            ip, port = ele.split(":")
            proxy_ins = ProxyInstance.objects.get(machine__bk_cloud_id=bk_cloud_id, machine__ip=ip, port=port)
            admin_addr = f"{ip}:{proxy_ins.admin_port}"
            admin_addresses.append(admin_addr)

        drs_raw_res = DRSApi.proxyrpc(
            {"addresses": admin_addresses, "cmds": ["show processlist"], "bk_cloud_id": bk_cloud_id}
        )
        for sr in drs_raw_res:
            admin_addr = sr["address"]
            ip, admin_port = admin_addr.split(":")
            port = int(admin_port) - 1000
            addr = f"{ip}:{port}"
            sr["address"] = addr

    else:
        drs_raw_res = DRSApi.rpc({"addresses": addresses, "cmds": ["show processlist"], "bk_cloud_id": bk_cloud_id})

    res = defaultdict(list)
    for raw_plist_res in drs_raw_res:
        if raw_plist_res["error_msg"]:
            raise DBMMcpBaseException(msg=raw_plist_res["error_msg"])

        plist_res = raw_plist_res["cmd_results"][0]
        if plist_res["error_msg"]:
            raise DBMMcpBaseException(msg=plist_res["error_msg"])

        res[raw_plist_res["address"]] = plist_res["table_data"]

    return res


def __show_processlist_on_proxy(bk_cloud_id: int, addresses: List[str], only_count: bool = True) -> List:
    """
    {
        'Host': '1.1.1.1:27057',
        'Id': '309244',
        'Server': '2.2.2.2:20000',
        'State': 'CON_STATE_READ_QUERY',
        'Time': '218',
        'User': 'gcs_admin',
        'db': None
    }
    """
    plist_res = __show_processlist(
        bk_cloud_id=bk_cloud_id,
        addresses=addresses,
        machine_type=MachineType.PROXY,
    )

    res = []  # defaultdict(list)
    for address, raw_plist in plist_res.items():
        plist = []
        for row in raw_plist:
            plist.append(
                {
                    "Id": row["Id"],
                    "host": row["Host"],
                    "command": "",
                    "user": row["User"],
                    "db": row["db"],
                    "time": row["Time"],
                    "state": row["State"],
                }
            )

        if only_count:
            res.append(
                {
                    "address": address,
                    "processlist_count": len(plist),
                    "machine_type": MachineType.PROXY,
                    "instance_role": "",
                }
            )
        else:
            res.append(
                {
                    "address": address,
                    "processlist_detail": plist,
                    "processlist_count": len(plist),
                    "machine_type": MachineType.PROXY,
                    "instance_role": "",
                }
            )

    return res


def __show_processlist_on_mysql(
    bk_cloud_id: int, addresses: List[str], machine_type: MachineType, only_count: bool = True
) -> List:
    """
    {
        'Command': 'Binlog Dump',
        'Host': '3.3.3.3:55846',
        'Id': '128245',
        'Info': None,
        'Rows_examined': '0',
        'Rows_sent': '0',
        'State': 'Master has sent all binlog to '
                'slave; waiting for binlog to be '
                'updated',
        'Time': '348886',
        'User': 'repl',
        'db': None
    }
    """
    plist_res = __show_processlist(bk_cloud_id=bk_cloud_id, addresses=addresses, machine_type=machine_type)

    res = []  # defaultdict(list)
    for address, raw_plist in plist_res.items():
        plist = []
        for row in raw_plist:
            plist.append(
                {
                    "id": row["Id"],
                    "host": row["Host"],
                    "command": row["Command"],
                    "user": row["User"],
                    "db": row["db"],
                    "time": row["Time"],
                    "state": row["State"],
                }
            )

        ip, port = address.split(":")
        if machine_type == MachineType.SPIDER:
            role = ProxyInstance.objects.get(machine__ip=ip, port=port).tendbclusterspiderext.spider_role
        else:
            role = StorageInstance.objects.get(machine__ip=ip, port=port).instance_role

        if only_count:
            res.append(
                {
                    "address": address,
                    "processlist_count": len(plist),
                    "machine_type": machine_type,
                    "instance_role": role,
                }
            )
        else:
            res.append(
                {
                    "address": address,
                    "processlist_detail": plist,
                    "processlist_count": len(plist),
                    "machine_type": machine_type,
                    "instance_role": role,
                }
            )

    return res


def __show_tendbsingle_processlist(cluster_obj: Cluster, only_count: bool = True) -> List:
    instances = cluster_obj.storageinstance_set.all()
    if not instances.exists():
        raise

    return __show_processlist_on_mysql(
        bk_cloud_id=cluster_obj.bk_cloud_id,
        addresses=[ins.ip_port for ins in instances],
        machine_type=MachineType.SINGLE,
        only_count=only_count,
    )


def __show_tendbha_processlist(cluster_obj: Cluster, only_count: bool = True) -> List:
    proxy_instances = cluster_obj.proxyinstance_set.all()
    storage_instances = cluster_obj.storageinstance_set.all()

    if not proxy_instances.exists() and not storage_instances.exists():
        raise

    return __show_processlist_on_proxy(
        bk_cloud_id=cluster_obj.bk_cloud_id,
        addresses=[f"{pi.machine.ip}:{pi.port + 1000}" for pi in proxy_instances],
        only_count=only_count,
    ) + __show_processlist_on_mysql(
        bk_cloud_id=cluster_obj.bk_cloud_id,
        addresses=[si.ip_port for si in storage_instances],
        machine_type=MachineType.BACKEND,
        only_count=only_count,
    )


def __show_tendbcluster_processlist(cluster_obj: Cluster, only_count: bool = True) -> List:
    proxy_instances = cluster_obj.proxyinstance_set.all()
    storage_instances = cluster_obj.storageinstance_set.all()

    if not proxy_instances.exists() and not storage_instances.exists():
        raise

    return __show_processlist_on_mysql(
        bk_cloud_id=cluster_obj.bk_cloud_id,
        addresses=[pi.ip_port for pi in proxy_instances],
        machine_type=MachineType.SPIDER,
        only_count=only_count,
    ) + __show_processlist_on_mysql(
        bk_cloud_id=cluster_obj.bk_cloud_id,
        addresses=[si.ip_port for si in storage_instances],
        machine_type=MachineType.BACKEND,
        only_count=only_count,
    )
