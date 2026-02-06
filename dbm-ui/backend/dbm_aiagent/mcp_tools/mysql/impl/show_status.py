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
from typing import Dict, List

from backend.components import DRSApi
from backend.db_meta.enums import MachineType
from backend.dbm_aiagent.mcp_tools.exceptions import DBMMcpBaseException, DBMMcpNotSupportMachineTypeException
from backend.dbm_aiagent.mcp_tools.mysql.serializers.usefully_choices import mysql_slave_status_masks


def show_instance_status(bk_cloud_id: int, address: str, machine_type: MachineType, status_hints: List[str]) -> Dict:
    if machine_type not in [
        MachineType.SINGLE,
        MachineType.PROXY,
        MachineType.BACKEND,
        MachineType.REMOTE,
        MachineType.SPIDER,
    ]:
        raise DBMMcpNotSupportMachineTypeException(machine_type=machine_type)

    if machine_type == MachineType.PROXY:
        return __show_proxy_status(bk_cloud_id=bk_cloud_id, address=address)
    else:
        runtime_statuses = __mysql_show_status(bk_cloud_id=bk_cloud_id, address=address)
        # slave_status = __mysql_show_slave_status(bk_cloud_id=bk_cloud_id, address=address)
        return {
            # "address": address,
            "runtime_status": [ele for ele in runtime_statuses if ele["status_name"] in status_hints],
        }


def __show_proxy_status(bk_cloud_id: int, address: str) -> Dict:
    split_address = address.split(":")
    raw_drs_res = DRSApi.proxyrpc(
        {
            "addresses": [f"{split_address[0]}:{int(split_address[1]) + 1000}"],
            "cmds": ["show uptime"],
            "bk_cloud_id": bk_cloud_id,
        }
    )

    address_res = raw_drs_res[0]
    if address_res["error_msg"]:
        raise DBMMcpBaseException(msg=address_res["error_msg"])

    show_uptime_res = address_res["cmd_results"][0]
    if show_uptime_res["error_msg"]:
        raise DBMMcpBaseException(msg=address_res["error_msg"])

    return {
        "address": address,
        "runtime_status": [{"status_name": "Uptime", "status_value": show_uptime_res["table_data"][0]["Uptime"]}],
    }


def __mysql_show_status(bk_cloud_id: int, address: str) -> List:
    raw_drs_res = DRSApi.rpc({"addresses": [address], "cmds": ["SHOW GLOBAL STATUS"], "bk_cloud_id": bk_cloud_id})

    address_res = raw_drs_res[0]
    if address_res["error_msg"]:
        raise DBMMcpBaseException(msg=address_res["error_msg"])

    show_status_res = address_res["cmd_results"][0]
    if show_status_res["error_msg"]:
        raise DBMMcpBaseException(msg=address_res["error_msg"])

    runtime_statuses = []
    for vv in show_status_res["table_data"]:
        v_name = vv["Variable_name"]
        v_value = vv["Value"]
        runtime_statuses.append({"status_name": v_name, "status_value": v_value})

    return runtime_statuses


def mysql_show_slave_status(bk_cloud_id: int, address: str) -> List:
    raw_drs_res = DRSApi.rpc({"addresses": [address], "cmds": ["SHOW SLAVE STATUS"], "bk_cloud_id": bk_cloud_id})

    address_res = raw_drs_res[0]
    if address_res["error_msg"]:
        raise DBMMcpBaseException(msg=address_res["error_msg"])

    show_status_res = address_res["cmd_results"][0]
    if show_status_res["error_msg"]:
        raise DBMMcpBaseException(msg=address_res["error_msg"])

    runtime_statuses = []

    if show_status_res["table_data"]:
        for k, v in show_status_res["table_data"][0].items():
            if k not in mysql_slave_status_masks:
                runtime_statuses.append({"status_name": k, "status_value": v})

    return runtime_statuses
