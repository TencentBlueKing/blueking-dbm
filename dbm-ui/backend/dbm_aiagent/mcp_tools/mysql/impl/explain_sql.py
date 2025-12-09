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


def explain_sql(cluster_type: ClusterType, cluster_domain: str, dbname: str, query_sql: str) -> Dict:
    raw_dbname = dbname

    bk_cloud_id, address, dbname = get_cloud_slave_address_and_dbname(
        cluster_type=cluster_type, cluster_domain=cluster_domain, dbname=dbname
    )

    drs_raw_res = DRSApi.rpc(
        {
            "addresses": [address],
            "cmds": [f"USE `{dbname}`", f"EXPLAIN {query_sql}"],
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
        "cluster_domain": cluster_domain,
        "cluster_type": cluster_type,
        "dbname": raw_dbname,
        "query_sql": query_sql,
        "explain_result": explain_sql_res["table_data"][0],
    }
