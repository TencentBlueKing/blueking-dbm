# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

SQLServer DRS RPC 通用执行器。

抽离原 index_analysis/common.py 中的 RPC 执行流程，下沉到 helpers，
便于跨功能域复用（list_table_status、index_analysis 等）。

------------------------------------------------------------------
RPC 通道选择规则（与 DRS 后端账号权限一一对应）
------------------------------------------------------------------
- DRSApi.sqlserver_sys_read_rpc
    账号仅对系统库只读：master / msdb / model / tempdb / Monitor。
    用于实例级、不依赖业务库上下文的查询（实例信息、备份/作业历史、
    巡检表 Monitor.* 等）。
- DRSApi.sqlserver_data_read_rpc
    账号对业务库只读 + 已授予 VIEW SERVER STATE。
    只要 SQL 需要 USE [业务库]，或要从业务库的 sys.* / DMV 读对象元数据，
    都必须走这条通道。
"""
from typing import Dict, List

from backend.components import DRSApi
from backend.dbm_aiagent.mcp_tools.exceptions import DBMMcpBaseException


def run_user_db_read(
    bk_cloud_id: int,
    target_address: str,
    quoted_db: str,
    select_sql: str,
    op_name: str,
) -> List[Dict]:
    """在指定业务库下执行单条 SELECT，返回 table_data。

    cmds 顺序：USE [dbname] → SELECT
    使用通道：sqlserver_data_read_rpc（业务库只读账号；具备对业务库
              的 CONNECT 与 sys.* / DMV 只读权限）

    :param bk_cloud_id:    云区域 ID
    :param target_address: 目标实例地址 ip:port
    :param quoted_db:      已经过 quote_sqlserver_ident 包裹的 [dbname]
    :param select_sql:     SELECT 语句（必须是单条且只读）
    :param op_name:        操作名（仅用于错误信息），如 "get_table_schema"
    :return: 单条 SELECT 的 table_data；为 None 时返回 []
    :raises DBMMcpBaseException: RPC 整体错误 / USE 阶段错误 / SELECT 阶段错误
    """
    cmds = [f"USE {quoted_db};", select_sql]

    rpc_results = DRSApi.sqlserver_data_read_rpc(
        {
            "bk_cloud_id": bk_cloud_id,
            "addresses": [target_address],
            "cmds": cmds,
        }
    )

    rpc_res = rpc_results[0]
    if rpc_res.get("error_msg"):
        raise DBMMcpBaseException(msg=rpc_res["error_msg"])

    cmd_results = rpc_res.get("cmd_results") or []
    if len(cmd_results) < 2:
        raise DBMMcpBaseException(msg=f"unexpected rpc result: missing cmd_results in {op_name}")

    if cmd_results[0].get("error_msg"):
        raise DBMMcpBaseException(msg=f"change db failed in {op_name}: {cmd_results[0]['error_msg']}")

    select_res = cmd_results[1]
    if select_res.get("error_msg"):
        raise DBMMcpBaseException(msg=f"{op_name} failed: {select_res['error_msg']}")

    return select_res.get("table_data") or []
