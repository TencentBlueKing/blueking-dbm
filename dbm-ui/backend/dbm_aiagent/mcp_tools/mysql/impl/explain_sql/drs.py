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
import logging
from typing import Any, List, Optional

from backend.components import DRSApi
from backend.dbm_aiagent.mcp_tools.exceptions import DBMMcpBaseException
from backend.dbm_aiagent.mcp_tools.mysql.helpers.sql_safety import quote_ident

logger = logging.getLogger("root")


def run_explain(
    *,
    bk_cloud_id: int,
    address: str,
    sql: str,
    use_db: Optional[str] = None,
) -> List[Any]:
    """在指定实例上执行 EXPLAIN，可选先 USE 物理/逻辑库。

    ``use_db`` 为空时只下发 ``EXPLAIN {sql}``；否则 ``USE {use_db}`` + ``EXPLAIN``。
    """
    cmds = [f"EXPLAIN {sql}"]
    if use_db:
        cmds.insert(0, f"USE {quote_ident(use_db)}")

    logger.info(
        "explain_sql drs: address=%s use_db=%s sql_len=%d",
        address,
        use_db or "",
        len(sql),
    )

    drs_raw_res = DRSApi.v2_webconsole_rpc(
        {
            "addresses": [address],
            "cmds": cmds,
            "force": False,
            "bk_cloud_id": bk_cloud_id,
            "query_timeout": 10,
        }
    )

    address_res = drs_raw_res[0]
    if address_res["error_msg"]:
        raise DBMMcpBaseException(msg=address_res["error_msg"])

    explain_cmd_idx = 1 if use_db else 0
    if use_db:
        use_db_res = address_res["cmd_results"][0]
        if use_db_res["error_msg"]:
            raise DBMMcpBaseException(msg=f"change db to {use_db} failed: {use_db_res['error_msg']}")

    explain_sql_res = address_res["cmd_results"][explain_cmd_idx]
    if explain_sql_res["error_msg"]:
        raise DBMMcpBaseException(msg=f"explain sql failed: {explain_sql_res['error_msg']}")

    return explain_sql_res["table_data"]
