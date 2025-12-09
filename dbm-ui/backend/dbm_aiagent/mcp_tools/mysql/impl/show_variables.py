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


def show_mysql_variables(address: str, machine_type: MachineType, variable_hints: List[str]) -> Dict:
    if machine_type not in [MachineType.SINGLE, MachineType.BACKEND, MachineType.REMOTE, MachineType.SPIDER]:
        raise DBMMcpNotSupportMachineTypeException(machine_type=machine_type)

    raw_drs_res = DRSApi.rpc({"addresses": [address], "cmds": ["SHOW VARIABLES"]})

    address_res = raw_drs_res[0]
    if address_res["error_msg"]:
        raise DBMMcpBaseException(msg=address_res["error_msg"])

    show_variable_res = address_res["cmd_results"][0]
    if show_variable_res["error_msg"]:
        raise DBMMcpBaseException(msg=address_res["error_msg"])

    runtime_variables = []
    if variable_hints:
        for vv in show_variable_res["table_data"]:
            v_name = vv["Variable_name"]
            v_value = vv["Value"]
            if v_name in variable_hints:
                runtime_variables.append({"variable_name": v_name, "variable_value": v_value})
    else:
        for vv in show_variable_res["table_data"]:
            v_name = vv["Variable_name"]
            v_value = vv["Value"]
            runtime_variables.append({"variable_name": v_name, "variable_value": v_value})

    return {"address": address, "runtime_variables": runtime_variables}
