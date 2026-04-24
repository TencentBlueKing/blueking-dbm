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
from typing import Dict

from backend.components import DRSApi
from backend.db_meta.enums import MachineType
from backend.dbm_aiagent.mcp_tools.exceptions import DBMMcpBaseException, DBMMcpNotSupportMachineTypeException


def show_engine_status(bk_cloud_id: int, address: str, engine: str, machine_type: MachineType) -> Dict:
    if machine_type not in [MachineType.SINGLE, MachineType.BACKEND, MachineType.REMOTE, MachineType.SPIDER]:
        raise DBMMcpNotSupportMachineTypeException(machine_type=machine_type)

    raw_drs_res = DRSApi.v2_mysql_rpc(
        {"addresses": [address], "cmds": [f"show engine {engine} status"], "bk_cloud_id": bk_cloud_id}
    )
    address_res = raw_drs_res[0]
    if address_res["error_msg"]:
        raise DBMMcpBaseException(msg=address_res["error_msg"])

    engine_status_res = address_res["cmd_results"][0]
    if engine_status_res["error_msg"]:
        raise DBMMcpBaseException(msg=engine_status_res["error_msg"])

    return {
        "engine_status": [
            {
                "name": row["Name"],
                "status": row["Status"],
                "type": row["Type"],
            }
            for row in engine_status_res["table_data"]
        ]
    }
