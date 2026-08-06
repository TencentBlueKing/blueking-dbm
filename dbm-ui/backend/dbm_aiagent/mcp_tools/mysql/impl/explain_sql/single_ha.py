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
from typing import Dict

from backend.db_meta.enums import ClusterType
from backend.dbm_aiagent.mcp_tools.mysql.helpers.get_slave_address_and_dbname import get_cloud_slave_address_and_dbname
from backend.dbm_aiagent.mcp_tools.mysql.impl.explain_sql.drs import run_explain

logger = logging.getLogger("root")


def explain_single_ha(
    cluster_type: ClusterType,
    cluster_domain: str,
    dbname: str,
    explained_sql: str,
    was_rewritten: bool,
) -> Dict:
    """TenDBSingle / TenDBHA：在 slave 上对 sanitize 后的 SQL 直接 EXPLAIN。"""
    bk_cloud_id, address, resolved_dbname = get_cloud_slave_address_and_dbname(
        cluster_type=cluster_type,
        cluster_domain=cluster_domain,
        dbname=dbname,
    )

    logger.info(
        "explain_sql single/ha: cluster=%s type=%s address=%s use_db=%s rewritten=%s",
        cluster_domain,
        cluster_type,
        address,
        resolved_dbname or "",
        was_rewritten,
    )

    explain_result = run_explain(
        bk_cloud_id=bk_cloud_id,
        address=address,
        sql=explained_sql,
        use_db=resolved_dbname or None,
    )

    return {
        "explain_result": explain_result,
        "rewritten": was_rewritten,
    }
