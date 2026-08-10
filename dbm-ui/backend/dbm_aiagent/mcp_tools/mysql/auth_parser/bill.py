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

from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster
from backend.dbm_aiagent.mcp_tools.mysql.constants import MYSQL_MCP_DB_READ


def auth_parse_mysql_tdbctl_upgrade_ticket(request, *args, **kwargs):
    data = request.query_params if request.method == "GET" else request.data
    bk_biz_id = data.get("bk_biz_id")
    cluster_domains = data.get("cluster_domains") or []
    cluster_ids = data.get("cluster_ids") or []

    clusters = None
    if cluster_domains:
        clusters = Cluster.objects.using(MYSQL_MCP_DB_READ).filter(
            immute_domain__in=cluster_domains, cluster_type=ClusterType.TenDBCluster
        )
    elif cluster_ids:
        clusters = Cluster.objects.using(MYSQL_MCP_DB_READ).filter(
            id__in=cluster_ids, cluster_type=ClusterType.TenDBCluster
        )
    elif bk_biz_id:
        clusters = Cluster.objects.using(MYSQL_MCP_DB_READ).filter(
            bk_biz_id=bk_biz_id, cluster_type=ClusterType.TenDBCluster
        )

    if not clusters or not clusters.exists():
        raise ValueError("No clusters found for the given params")

    return list(clusters.values_list("id", flat=True))
