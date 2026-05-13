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
from backend.db_meta.enums import ClusterType
from backend.dbm_aiagent.mcp_tools.exceptions import DBMMcpBaseException
from backend.dbm_aiagent.mcp_tools.mysql.helpers.get_slave_address_and_dbname import get_cloud_slave_address_and_dbname
from backend.dbm_aiagent.mcp_tools.mysql.helpers.sql_safety import quote_ident, sanitize_select_sql


def explain_sql(cluster_type: ClusterType, cluster_domain: str, dbname: str, query_sql: str) -> Dict:
    # 校验并归一化用户提交的 SQL；UPDATE/DELETE/INSERT...SELECT 会被改写为等价 SELECT，
    # 以便在只读账号下也能拿到执行计划
    explained_sql, was_rewritten = sanitize_select_sql(query_sql)

    # 如果是 spider集群， db_name 会添加分片信息
    bk_cloud_id, address, dbname = get_cloud_slave_address_and_dbname(
        cluster_type=cluster_type, cluster_domain=cluster_domain, dbname=dbname
    )
    cmds = [f"EXPLAIN {explained_sql}"]
    if dbname:
        cmds.insert(0, f"USE {quote_ident(dbname)}")
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

    use_db_res = address_res["cmd_results"][0]
    if use_db_res["error_msg"]:
        raise DBMMcpBaseException(msg=f"change db to {dbname} failed: {use_db_res['error_msg']}")

    explain_sql_res = address_res["cmd_results"][1]
    if explain_sql_res["error_msg"]:
        raise DBMMcpBaseException(msg=f"explain sql failed: {explain_sql_res['error_msg']}")

    return {
        "explain_result": explain_sql_res["table_data"][0],
        # sql 原文可能很大，mcp返回会超长，占用上下文。先不返回了
        # "explained_sql": explained_sql,
        "rewritten": was_rewritten,
    }
