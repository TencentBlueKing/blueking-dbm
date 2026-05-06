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
from typing import Any, Dict, List, Optional

from django.utils.translation import gettext as _

from backend.components import DRSApi
from backend.db_meta.enums import MachineType
from backend.dbm_aiagent.mcp_tools.exceptions import DBMMcpBaseException, DBMMcpNotSupportMachineTypeException

# 仅允许常见 binlog 文件名字符，避免 SQL 注入
_SAFE_BINLOG_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9._-]+$")


def _build_show_binlog_events_sql(
    log_name: Optional[str],
    from_pos: Optional[int],
    limit_offset: Optional[int],
    limit_row_count: int,
) -> str:
    parts: List[str] = ["SHOW BINLOG EVENTS"]
    if log_name is not None:
        if not _SAFE_BINLOG_NAME_PATTERN.match(log_name):
            raise DBMMcpBaseException(msg=_("log_name 不合法, 仅允许字母、数字、点、下划线与连字符"))
        parts.append("IN '{}'".format(log_name))
    if from_pos is not None:
        parts.append("FROM {}".format(int(from_pos)))
    if limit_offset is not None:
        parts.append("LIMIT {}, {}".format(int(limit_offset), int(limit_row_count)))
    else:
        parts.append("LIMIT {}".format(int(limit_row_count)))
    return " ".join(parts)


def _extract_events(table_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """原样返回 DRS 行数据, 列名随 MySQL 版本可能不同。"""
    return [dict(row) for row in table_data]


def show_binlog_events(
    bk_cloud_id: int,
    address: str,
    machine_type: MachineType,
    log_name: Optional[str],
    from_pos: Optional[int],
    limit_offset: Optional[int],
    limit_row_count: int,
) -> Dict:
    if machine_type not in [MachineType.SINGLE, MachineType.BACKEND, MachineType.REMOTE, MachineType.SPIDER]:
        raise DBMMcpNotSupportMachineTypeException(machine_type=machine_type)

    cmd = _build_show_binlog_events_sql(log_name, from_pos, limit_offset, limit_row_count)
    raw_drs_res = DRSApi.rpc({"addresses": [address], "cmds": [cmd], "bk_cloud_id": bk_cloud_id})
    address_res = raw_drs_res[0]
    if address_res["error_msg"]:
        raise DBMMcpBaseException(msg=address_res["error_msg"])

    cmd_res = address_res["cmd_results"][0]
    if cmd_res["error_msg"]:
        raise DBMMcpBaseException(msg=cmd_res["error_msg"])

    return {
        "events": _extract_events(cmd_res.get("table_data") or []),
    }
