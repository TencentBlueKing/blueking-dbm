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

from backend.components import DRSApi
from backend.dbm_aiagent.mcp_tools.exceptions import DBMMcpBaseException

# 查询超过 1 小时未提交的长事务
QUERY_LONG_RUNNING_TRX_SQL = (
    "select trx_state, trx_started, trx_mysql_thread_id, "
    "t2.ID, t2.USER, t2.HOST, t2.DB, t2.COMMAND, t2.TIME, t2.STATE, t2.INFO "
    "from information_schema.innodb_trx t1 "
    "join information_schema.processlist t2 on t1.trx_mysql_thread_id = t2.id "
    "where trx_started < DATE_SUB(now(), INTERVAL 1 hour)"
)


def query_long_running_trx(bk_cloud_id: int, address: str):
    """查询 MySQL 长事务，事务未关闭，当前可能正在执行 SQL，也可能 Sleep 未提交"""
    drs_raw_res = DRSApi.v2_mysql_rpc(
        {
            "addresses": [address],
            "cmds": [QUERY_LONG_RUNNING_TRX_SQL],
            "bk_cloud_id": bk_cloud_id,
        }
    )
    if drs_raw_res[0]["error_msg"]:
        raise DBMMcpBaseException(msg=drs_raw_res[0]["error_msg"])

    if drs_raw_res[0]["cmd_results"][0]["error_msg"]:
        raise DBMMcpBaseException(msg=drs_raw_res[0]["cmd_results"][0]["error_msg"])

    table_data = drs_raw_res[0]["cmd_results"][0]["table_data"]
    res = []
    for item in table_data:
        res.append(
            {
                "trx_state": item.get("trx_state", ""),
                "trx_started": item.get("trx_started", ""),
                "trx_mysql_thread_id": item.get("trx_mysql_thread_id", ""),
                "id": item.get("ID", ""),
                "source_host": item.get("HOST", ""),
                "command": item.get("COMMAND", ""),
                "user": item.get("USER", ""),
                "db": item.get("DB", ""),
                "time": int(item["TIME"]) if isinstance(item.get("TIME"), str) else item.get("TIME", 0),
                "state": item.get("STATE", ""),
                "info": item.get("INFO"),
            }
        )

    return res
