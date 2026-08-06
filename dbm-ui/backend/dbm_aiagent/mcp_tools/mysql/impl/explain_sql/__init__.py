# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

MySQL EXPLAIN MCP 入口。

公共前缀：``sanitize_select_sql``（安全校验 + DML→SELECT，不改库名）。

之后按 ``cluster_type`` 分叉：

- TenDBSingle / TenDBHA → ``single_ha.explain_single_ha``
- TenDBCluster → ``tendbcluster.explain_tendbcluster``（分片路由 7 步）
"""
import logging
from typing import Dict

from backend.db_meta.enums import ClusterType
from backend.dbm_aiagent.mcp_tools.mysql.helpers.sql_safety import sanitize_select_sql
from backend.dbm_aiagent.mcp_tools.mysql.impl.explain_sql.single_ha import explain_single_ha
from backend.dbm_aiagent.mcp_tools.mysql.impl.explain_sql.tendbcluster import explain_tendbcluster

logger = logging.getLogger("root")


def explain_sql(cluster_type: ClusterType, cluster_domain: str, dbname: str, query_sql: str) -> Dict:
    """对 MySQL 集群执行 EXPLAIN，返回 MCP 标准结构 ``{explain_result, rewritten}``。"""
    # Step 1（公共）：安全校验 + DML→SELECT
    explained_sql, was_rewritten = sanitize_select_sql(query_sql)

    logger.info(
        "explain_sql start: cluster=%s type=%s db=%s rewritten=%s",
        cluster_domain,
        cluster_type,
        dbname or "",
        was_rewritten,
    )

    if cluster_type == ClusterType.TenDBCluster:
        return explain_tendbcluster(
            cluster_domain=cluster_domain,
            dbname=dbname,
            explained_sql=explained_sql,
            was_rewritten=was_rewritten,
        )

    return explain_single_ha(
        cluster_type=cluster_type,
        cluster_domain=cluster_domain,
        dbname=dbname,
        explained_sql=explained_sql,
        was_rewritten=was_rewritten,
    )
