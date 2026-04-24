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
from backend.dbm_aiagent.mcp_tools.mysql.helpers.get_slave_address_and_dbname import safe_sql_in_string


def show_instance_variables(bk_cloud_id: int, address: str, machine_type: MachineType, names: list[str]) -> Dict:
    if machine_type not in [MachineType.SINGLE, MachineType.BACKEND, MachineType.REMOTE, MachineType.SPIDER]:
        raise DBMMcpNotSupportMachineTypeException(machine_type=machine_type)
    cmd = "SHOW GLOBAL VARIABLES"
    if names:
        # show global variables  where Variable_name in ('wait_timeout', 'version');
        # 因为是使用输入的 names，担心有注入，限制只能是 a-zA-Z_
        in_clause = safe_sql_in_string(names)
        cmd = f"{cmd} WHERE Variable_name IN {in_clause}"

    raw_drs_res = DRSApi.v2_mysql_rpc({"addresses": [address], "cmds": [cmd], "bk_cloud_id": bk_cloud_id})

    address_res = raw_drs_res[0]
    if address_res["error_msg"]:
        raise DBMMcpBaseException(msg=address_res["error_msg"])

    show_variable_res = address_res["cmd_results"][0]
    if show_variable_res["error_msg"]:
        raise DBMMcpBaseException(msg=address_res["error_msg"])

    runtime_variables = []
    for vv in show_variable_res["table_data"]:
        runtime_variables.append({"variable_name": vv["Variable_name"], "variable_value": vv["Value"]})

    return {"runtime_variables": runtime_variables}
