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
from typing import Dict, List, Union

from django.db.models import Q

from backend.components import DRSApi
from backend.db_meta.enums import ClusterType, MachineType, TenDBClusterSpiderRole
from backend.db_meta.models import Cluster
from backend.dbm_aiagent.mcp_tools.exceptions import DBMMcpBaseException, DBMMcpNotSupportClusterTypeException


def show_cluster_processlist(cluster_type: ClusterType, cluster_domain: str, raw_addresses=None) -> Dict:
    if raw_addresses is None:
        raw_addresses = []
    cluster_obj = Cluster.objects.get(cluster_type=cluster_type, immute_domain=cluster_domain)

    addresses = []
    if raw_addresses:
        addresses = [{"ip": a.split(":")[0], "port": int(a.split(":")[1])} for a in raw_addresses]

    if cluster_type == ClusterType.TenDBSingle:
        return __show_tendbsingle_processlist(cluster_obj, addresses)
    elif cluster_type == ClusterType.TenDBHA:
        return __show_tendbha_processlist(cluster_obj, addresses)
    elif cluster_type == ClusterType.TenDBCluster:
        return __show_tendbcluster_processlist(cluster_obj, addresses)
    else:
        raise DBMMcpNotSupportClusterTypeException(cluster_type=cluster_type)


def __show_processlist(addresses: List[str], machine_type: MachineType) -> Dict:
    if not addresses:
        return {}

    if machine_type == MachineType.PROXY:
        drs_raw_res = DRSApi.proxyrpc({"addresses": addresses, "cmds": ["show processlist"]})
    else:
        drs_raw_res = DRSApi.rpc({"addresses": addresses, "cmds": ["show processlist"]})

    res = defaultdict(list)
    for proxy_plist_res in drs_raw_res:
        if proxy_plist_res["error_msg"]:
            raise DBMMcpBaseException(msg=proxy_plist_res["error_msg"])

        plist_res = proxy_plist_res["cmd_results"][0]
        if plist_res["error_msg"]:
            raise DBMMcpBaseException(msg=plist_res["error_msg"])

        res[proxy_plist_res["address"]] = plist_res["table_data"]

    return res


def __show_processlist_on_proxy(addresses: List[str]) -> Dict:
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
    plist_res = __show_processlist(addresses, MachineType.PROXY)

    res = defaultdict(list)
    for address, plist in plist_res.items():
        for row in plist:
            res[address].append(
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

    return res


def __show_processlist_on_mysql(addresses: List[str], machine_type: MachineType) -> Dict:
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
    plist_res = __show_processlist(addresses, machine_type)

    res = defaultdict(list)
    for address, plist in plist_res.items():
        for row in plist:
            res[address].append(
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

    return res


def __show_tendbsingle_processlist(cluster_obj: Cluster, addresses: List[Dict[str, Union[str, int]]]) -> Dict:
    q = Q()
    for address in addresses:
        q |= Q(**{"machine__ip": address["ip"], "port": address["port"]})

    instances = cluster_obj.storageinstance_set.filter(q)
    if not instances.exists():
        raise

    return __show_processlist_on_mysql([ins.ip_port for ins in instances], MachineType.SINGLE)


def __show_tendbha_processlist(cluster_obj: Cluster, addresses: List[Dict[str, Union[str, int]]]) -> Dict:
    if not addresses:
        return __show_processlist_on_proxy(
            [f"{pi.machine.ip}:{pi.port + 1000}" for pi in cluster_obj.proxyinstance_set.all()]
        )

    q = Q()
    for address in addresses:
        q |= Q(**{"machine__ip": address["ip"], "port": address["port"]})

    proxy_instances = cluster_obj.proxyinstance_set.filter(q)
    storage_instances = cluster_obj.storageinstance_set.filter(q)

    if not proxy_instances.exists() and not storage_instances.exists():
        raise

    return {
        **__show_processlist_on_proxy([f"{pi.machine.ip}:{pi.port + 1000}" for pi in proxy_instances]),
        **__show_processlist_on_mysql([si.ip_port for si in storage_instances], MachineType.BACKEND),
    }


def __show_tendbcluster_processlist(cluster_obj: Cluster, addresses: List[Dict[str, Union[str, int]]]) -> Dict:
    if not addresses:
        return __show_processlist_on_mysql(
            [
                si.ip_port
                for si in cluster_obj.proxyinstance_set.filter(
                    tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_MASTER
                )
            ],
            MachineType.SPIDER,
        )

    q = Q()
    for address in addresses:
        q |= Q(**{"machine__ip": address["ip"], "port": address["port"]})

    proxy_instances = cluster_obj.proxyinstance_set.filter(q)
    storage_instances = cluster_obj.storageinstance_set.filter(q)

    if not proxy_instances.exists() and not storage_instances.exists():
        raise

    return {
        **__show_processlist_on_mysql([pi.ip_port for pi in proxy_instances], MachineType.SPIDER),
        **__show_processlist_on_mysql([si.ip_port for si in storage_instances], MachineType.BACKEND),
    }
