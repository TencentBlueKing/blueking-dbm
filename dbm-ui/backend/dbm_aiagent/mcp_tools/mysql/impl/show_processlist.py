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
import json
from typing import Dict, List

import pandas

from backend.components import DRSApi
from backend.db_meta.enums import ClusterType
from backend.db_meta.models import ProxyInstance
from backend.db_services.mysql.sqlparse import digest
from backend.dbm_aiagent.mcp_tools.exceptions import DBMMcpBaseException
from backend.dbm_aiagent.mcp_tools.mysql.constants import MYSQL_MCP_DB_READ


def show_mysql_processlist(bk_cloud_id: int, address: str):
    drs_raw_res = DRSApi.v2_mysql_rpc(
        {
            "addresses": [address],
            "cmds": ["show full processlist"],
            "bk_cloud_id": bk_cloud_id,
        }
    )
    if drs_raw_res[0]["error_msg"]:
        raise DBMMcpBaseException(msg=drs_raw_res[0]["error_msg"])

    if drs_raw_res[0]["cmd_results"][0]["error_msg"]:
        raise DBMMcpBaseException(msg=drs_raw_res[0]["cmd_results"][0]["error_msg"])

    processlist_detail = drs_raw_res[0]["cmd_results"][0]["table_data"]
    res = []
    for item in processlist_detail:
        # 不过滤任何东西
        digest_info = {}
        if item["Info"]:
            digest_info = digest.generate_sql_fingerprint(item["Info"], item["db"])
        res.append(
            {
                "id": item["Id"],
                # "access_source_address": item["Host"].split(":")[0],
                "source_host": item["Host"],
                "command": item.get("Command", ""),
                "user": item["User"],
                "db": item["db"],
                "time": int(item["Time"]) if isinstance(item["Time"], str) else 0,
                "state": item["State"],
                "info": item["Info"],
                # "instance_address": address,
                "tables": digest_info.get("tables", []),
                "fingerprint": digest_info.get("query_digest_text", ""),
                "fingerprint_md5": digest_info.get("query_digest_md5", ""),
                "query_len": digest_info.get("query_len", 0),
            }
        )

    return res


def show_proxy_processlist(bk_cloud_id: int, address: str):
    ip, port = address.split(":")
    proxy_ins = ProxyInstance.objects.using(MYSQL_MCP_DB_READ).get(
        machine__ip=ip, port=port, machine__bk_cloud_id=bk_cloud_id
    )
    drs_raw_res = DRSApi.v2_proxyrpc(
        {
            "addresses": [f"{ip}:{proxy_ins.admin_port}"],
            "cmds": ["show processlist"],
            "bk_cloud_id": bk_cloud_id,
        }
    )
    if drs_raw_res[0]["error_msg"]:
        raise DBMMcpBaseException(msg=drs_raw_res[0]["error_msg"])

    if drs_raw_res[0]["cmd_results"][0]["error_msg"]:
        raise DBMMcpBaseException(msg=drs_raw_res[0]["cmd_results"][0]["error_msg"])

    processlist_detail = drs_raw_res[0]["cmd_results"][0]["table_data"]
    res = []
    for item in processlist_detail:
        res.append(
            {
                "id": item["Id"],
                "source_host": item["Host"],
                "user": item["User"],
                "destination_host": item["Server"],
                "state": item["State"],
                "db": item["db"],
                "time": int(item["Time"]) if isinstance(item["Time"], str) else 0,
            }
        )

    return res


def show_instance_processlist(instance: str, bk_cloud_id: int, cluster_type, instance_role):
    if instance_role == "proxy" and cluster_type == ClusterType.TenDBHA:
        processlist_detail = show_proxy_processlist(bk_cloud_id, instance)
        return processlist_detail

    processlist_detail = show_mysql_processlist(bk_cloud_id, instance)
    return processlist_detail


def aggregate_processlist_by_type(processlist_detail: List, aggregate_type: str) -> Dict[str, str]:
    if not processlist_detail:
        return {}

    df = pandas.DataFrame(processlist_detail)
    res = {}
    if aggregate_type == "group_by_user":
        res["group_by_user_count"] = df["user"].value_counts().to_dict()
    if aggregate_type == "group_by_state":
        res["group_by_state_count"] = df["state"].value_counts().to_dict()
    if aggregate_type == "group_by_command":
        res["group_by_command_count"] = df["command"].value_counts().to_dict()
    elif aggregate_type == "group_by_client_host":
        res["group_by_client_host_count"] = df["access_source_address"].value_counts().to_dict()
    elif aggregate_type == "longest_top_5":
        # 按 time 时长排序，且排除 Command 为 Sleep 的
        res["longest_top_5"] = json.loads(
            df[df["command"] != "Sleep"]
            .nlargest(5, "time")[["user", "db", "fingerprint", "time"]]
            .to_json(orient="records")
        )
    else:
        # aggregate_type == "group_by_fingerprint":
        res["group_by_fingerprint_count"] = df["fingerprint"].value_counts().to_dict()
    return res
