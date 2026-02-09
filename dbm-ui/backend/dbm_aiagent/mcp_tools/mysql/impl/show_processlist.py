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
import re
from typing import Dict, List, Tuple

import numpy
import pandas
from simpleeval import EvalWithCompoundTypes, simple_eval

from backend.components import DRSApi
from backend.db_meta.enums import ClusterType, InstanceInnerRole, MachineType, TenDBClusterSpiderRole
from backend.db_meta.models import Cluster, ProxyInstance, StorageInstance
from backend.db_services.mysql.sqlparse import digest
from backend.dbm_aiagent.mcp_tools.exceptions import DBMMcpBaseException
from backend.dbm_aiagent.mcp_tools.mysql.serializers.usefully_choices import (
    MySQLProcessListFilterFieldType,
    MySQLProcessListInstanceGroupType,
)


def show_instance_processlist_summary(cluster_obj: Cluster, instance: str, aggregate_type: str):
    cluster_type = cluster_obj.cluster_type
    bk_cloud_id = cluster_obj.bk_cloud_id
    instance_host, instance_port = instance.split(":")

    storage_instances = StorageInstance.objects.filter(machine__in=instance_host, port=instance_port)
    proxy_instances = []
    if not storage_instances or cluster_type == ClusterType.TenDBHA:
        # if instance is not storage, we query from proxy instances
        proxy_instances = ProxyInstance.objects.filter(machine__in=instance_host, port=instance_port)

    if cluster_type == ClusterType.TenDBSingle:
        proxy_processlist_detail = []
        storage_processlist_detail = __show_tendbsingle_processlist(bk_cloud_id, storage_instances)
    elif cluster_type == ClusterType.TenDBHA:
        proxy_processlist_detail, storage_processlist_detail = __show_tendbha_processlist(
            bk_cloud_id, proxy_instances, storage_instances
        )
        # TODO combine ?
    else:
        # may be query proxy or storage
        proxy_processlist_detail, storage_processlist_detail = __show_tendbcluster_processlist(
            bk_cloud_id, proxy_instances, storage_instances
        )
        for ele in storage_processlist_detail:
            if ele["db"]:
                ele["db"] = re.sub(r"_[0-9]+$", "", ele["db"])

    res = {}
    if proxy_processlist_detail:
        res["proxy_processlist_summary"] = __summary_processlist_by_type(proxy_processlist_detail, aggregate_type)
    if storage_processlist_detail:
        res["storage_processlist_summary"] = __summary_processlist_by_type(storage_processlist_detail, aggregate_type)
    return res


def show_cluster_processlist_summary(
    cluster_obj: Cluster, instance_group: MySQLProcessListInstanceGroupType
) -> Tuple[Dict, Dict]:
    cluster_type = cluster_obj.cluster_type
    bk_cloud_id = cluster_obj.bk_cloud_id

    proxy_instance_addresses, storage_instance_addresses = __get_instances_address(cluster_obj, instance_group)

    if cluster_type == ClusterType.TenDBSingle:
        proxy_processlist_detail = []
        storage_processlist_detail = __show_tendbsingle_processlist(bk_cloud_id, storage_instance_addresses)

    elif cluster_type == ClusterType.TenDBHA:
        proxy_processlist_detail, storage_processlist_detail = __show_tendbha_processlist(
            bk_cloud_id, proxy_instance_addresses, storage_instance_addresses
        )

    else:
        proxy_processlist_detail, storage_processlist_detail = __show_tendbcluster_processlist(
            bk_cloud_id, proxy_instance_addresses, storage_instance_addresses
        )
        for ele in storage_processlist_detail:
            if ele["db"]:
                ele["db"] = re.sub(r"_[0-9]+$", "", ele["db"])

    return {
        "proxy_processlist_summary": __summary_processlist(proxy_processlist_detail),
        "storage_processlist_summary": __summary_processlist(storage_processlist_detail),
    }


def __get_instances_address(
    cluster_obj: Cluster, instance_group: MySQLProcessListInstanceGroupType
) -> Tuple[List[str], List[str]]:
    cluster_type = cluster_obj.cluster_type

    if cluster_type == ClusterType.TenDBSingle:
        return [], [ele.ip_port for ele in cluster_obj.storageinstance_set.all()]
    elif cluster_type == ClusterType.TenDBHA:
        if instance_group == MySQLProcessListInstanceGroupType.MasterGroup:
            return [ele.ip_port for ele in cluster_obj.proxyinstance_set.all()], [
                ele.ip_port
                for ele in cluster_obj.storageinstance_set.filter(instance_inner_role=InstanceInnerRole.MASTER)
            ]
        else:
            return [], [
                ele.ip_port
                for ele in cluster_obj.storageinstance_set.filter(
                    instance_inner_role=InstanceInnerRole.SLAVE, is_stand_by=True
                )
            ]
    else:
        if instance_group == MySQLProcessListInstanceGroupType.MasterGroup:
            return [
                ele.ip_port
                for ele in cluster_obj.proxyinstance_set.filter(
                    tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_MASTER
                )
            ], [
                ele.ip_port
                for ele in cluster_obj.storageinstance_set.filter(instance_inner_role=InstanceInnerRole.MASTER)
            ]
        else:
            return [
                ele.ip_port
                for ele in cluster_obj.proxyinstance_set.filter(
                    tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_SLAVE
                )
            ], [
                ele.ip_port
                for ele in cluster_obj.storageinstance_set.filter(instance_inner_role=InstanceInnerRole.SLAVE)
            ]


def __show_tendbsingle_processlist(bk_cloud_id: int, instance_addresses: List[str]) -> List:
    return __show_processlist(
        bk_cloud_id=bk_cloud_id,
        addresses=instance_addresses,
        machine_type=MachineType.SINGLE,
    )


def __show_tendbha_processlist(
    bk_cloud_id: int, proxy_instance_addresses: List[str], storage_instance_addresses: List[str]
) -> Tuple[List, List]:
    return __show_processlist(
        bk_cloud_id=bk_cloud_id,
        addresses=proxy_instance_addresses,
        machine_type=MachineType.PROXY,
    ), __show_processlist(
        bk_cloud_id=bk_cloud_id,
        addresses=storage_instance_addresses,
        machine_type=MachineType.BACKEND,
    )


def __show_tendbcluster_processlist(
    bk_cloud_id: int, spider_instance_addresses: List[str], storage_instance_addresses: List[str]
) -> Tuple[List, List]:
    return __show_processlist(
        bk_cloud_id=bk_cloud_id,
        addresses=spider_instance_addresses,
        machine_type=MachineType.SPIDER,
    ), __show_processlist(
        bk_cloud_id=bk_cloud_id,
        addresses=storage_instance_addresses,
        machine_type=MachineType.REMOTE,
    )


def __show_processlist(bk_cloud_id: int, addresses: List[str], machine_type: MachineType) -> List:
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
        drs_raw_res = DRSApi.rpc(
            {"addresses": addresses, "cmds": ["show full processlist"], "bk_cloud_id": bk_cloud_id}
        )

    res = []
    for raw_plist_res in drs_raw_res:
        if raw_plist_res["error_msg"]:
            raise DBMMcpBaseException(msg=raw_plist_res["error_msg"])

        plist_res = raw_plist_res["cmd_results"][0]
        if plist_res["error_msg"]:
            raise DBMMcpBaseException(msg=plist_res["error_msg"])

        for row in plist_res["table_data"]:
            if row["User"] == "system user":
                continue
            digest_info = {}
            if row["Info"]:
                digest_info = digest.generate_sql_fingerprint(row["Info"], row["db"])
            res.append(
                {
                    "id": row["Id"],
                    "access_source_address": row["Host"].split(":")[0],
                    # "proxy_address": "",
                    "command": row.get("Command", ""),
                    "user": row["User"],
                    "db": row["db"],
                    "time": int(row["Time"]) if isinstance(row["Time"], str) else 0,
                    "state": row["State"],
                    "info": row["Info"],  # detail 里面可以包含 sql 详情
                    "instance_address": raw_plist_res["address"],
                    "tables": digest_info.get("tables", []),
                    "fingerprint": digest_info.get("query_digest_text", ""),
                    "fingerprint_md5": digest_info.get("query_digest_md5", ""),
                    "query_len": digest_info.get("query_len", 0),
                }
            )

    return res


def __combine_by_id(proxy_list_dict: Dict, storage_list_dict: Dict) -> List:
    combine_dict = {}
    for k, v in storage_list_dict.items():

        proxy_v = proxy_list_dict.get(k, {})
        if proxy_v:
            v["proxy_address"] = v.pop("access_source_address")
            combine_dict[k] = v
            combine_dict[k]["access_source_address"] = proxy_v["access_source_address"]
        else:
            combine_dict[k] = v
            combine_dict[k]["proxy_address"] = ""

    return list(combine_dict.values())


def apply_filters(row, filters) -> bool:
    satisfy = True
    for ft in filters:
        filter_field = ft["filter_field"]
        filter_op = ft["filter_op"]
        filter_values = ft["filter_values"]

        row_value = row[filter_field]

        if filter_field == MySQLProcessListFilterFieldType.State:
            evaluator = EvalWithCompoundTypes()
            command_value = row["command"]
            expr = f"'{row_value}' {filter_op} {filter_values} or '{command_value}' {filter_op} {filter_values}"
            yes = evaluator.eval(expr)
        elif filter_field == MySQLProcessListFilterFieldType.Time:
            yes = simple_eval(f"{row_value} {filter_op} {int(filter_values[0])}")
        else:
            evaluator = EvalWithCompoundTypes()
            yes = evaluator.eval(f"'{row_value}' {filter_op} {filter_values}")

        satisfy = satisfy and yes

    return satisfy


def __summary_processlist(processlist_detail: List) -> Dict[str, str]:
    if not processlist_detail:
        return {}

    df = pandas.DataFrame(processlist_detail)
    hist, bin_edges = numpy.histogram(df["time"], bins=5)
    return {
        "total_count": len(processlist_detail),
        "group_by_access_source_address": df.groupby("access_source_address")
        .agg({"access_source_address": ["count"]})
        .to_json(),
        "group_by_user": df.groupby("user").agg({"user": ["count"]}).to_json(),
        "group_by_db": df.groupby("db").agg({"db": ["count"]}).to_json(),
        "group_by_command": df.groupby("command").agg({"command": ["count"]}).to_json(),
        "group_by_state": df.groupby("state").agg({"state": ["count"]}).to_json(),
        "group_by_instance_address": df.groupby("instance_address").agg({"instance_address": ["count"]}).to_json(),
        "time_histogram": pandas.cut(df["time"], bins=bin_edges).value_counts().sort_index().to_json(),
    }


def __summary_processlist_by_type(processlist_detail: List, aggregate_type: str) -> Dict[str, str]:
    if not processlist_detail:
        return {}

    df = pandas.DataFrame(processlist_detail)
    res = {
        "total_count": len(processlist_detail),
        "group_by_state": df.groupby("state").agg({"state": ["count"]}).to_json(),
    }
    if aggregate_type == "group_by_user":
        res["group_by_user"] = df.groupby("user").agg({"user": ["count"]}).to_json()
    elif aggregate_type == "group_by_client_host":
        res["group_by_client_host"] = df.groupby("access_source_address").agg({"access_source_address": ["count"]})
    elif aggregate_type == "longest_top_5":
        # 按 time 时长排序，且排除 Command 为 Sleep 的
        res["longest_top_5"] = (
            df[df["command"] != "Sleep"].nlargest(5, "time")[["user", "db", "fingerprint", "time"]].to_json()
        )
    else:
        # aggregate_type == "group_by_fingerprint":
        res["group_by_fingerprint"] = df.groupby("fingerprint").agg({"fingerprint": ["count"]}).to_json()
    return res
