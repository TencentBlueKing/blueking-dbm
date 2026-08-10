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

from backend.db_meta.models import Cluster
from backend.db_services.mysql.remote_service.handlers import RemoteServiceHandler
from backend.dbm_aiagent.mcp_tools.mysql.constants import MYSQL_MCP_DB_READ


def show_databases_with_patterns(cluster_domain: str, dbs: List[str], ignore_dbs: List[str]) -> Dict:
    cluster_obj = Cluster.objects.using(MYSQL_MCP_DB_READ).get(immute_domain=cluster_domain)

    info = {
        "cluster_id": cluster_obj.pk,
        "dbs": dbs,
        "ignore_dbs": ignore_dbs,
    }

    result = RemoteServiceHandler(bk_biz_id=cluster_obj.bk_biz_id).show_databases_with_db_patterns([info])

    return {
        "cluster_id": cluster_obj.pk,
        "databases": result[0]["databases"] if result else [],
    }
