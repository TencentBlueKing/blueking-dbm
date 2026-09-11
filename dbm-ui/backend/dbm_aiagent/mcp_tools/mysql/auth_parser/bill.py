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


def _auth_parse_infos_clusters(request, cluster_type: ClusterType):
    """
    从多行 infos 中提取 cluster_domain 并解析集群列表，供鉴权使用。
    request 接收 params:
    - infos: 信息列表，每行包含 cluster_domain
    """
    data = request.query_params if request.method == "GET" else request.data
    infos = data.get("infos") or []
    cluster_domains = [info.get("cluster_domain") for info in infos if info.get("cluster_domain")]

    if not cluster_domains:
        raise ValueError("no cluster_domain found in infos")

    clusters = Cluster.objects.using(MYSQL_MCP_DB_READ).filter(
        immute_domain__in=cluster_domains, cluster_type=cluster_type
    )

    if not clusters.exists():
        raise ValueError("No clusters found for the given infos")

    return list(clusters.values_list("id", flat=True))


def auth_parse_mysql_proxy_conf_change(request, *args, **kwargs):
    """
    解析 proxy 升降配多行参数 - 获取集群列表鉴权
    request 接收 params:
    - infos: 升降配信息列表，每行包含 cluster_domain、target_spec_id、labels
    """
    return _auth_parse_infos_clusters(request, ClusterType.TenDBHA)


def auth_parse_mysql_migrate(request, *args, **kwargs):
    """
    解析 TenDBHA 主从迁移多行参数 - 获取集群列表鉴权
    request 接收 params:
    - infos: 迁移信息列表，每行包含 cluster_domain、spec_id、count、labels
    """
    return _auth_parse_infos_clusters(request, ClusterType.TenDBHA)


def auth_parse_spider_conf_change(request, *args, **kwargs):
    """
    解析 TenDBCluster 接入层升降配多行参数 - 获取集群列表鉴权
    request 接收 params:
    - infos: 升降配信息列表，每行包含 cluster_domain、spider_role、target_spec_id、labels
    """
    return _auth_parse_infos_clusters(request, ClusterType.TenDBCluster)


def auth_parse_tendbcluster_node_rebalance(request, *args, **kwargs):
    """
    解析 TenDBCluster 集群容量变更多行参数 - 获取集群列表鉴权
    request 接收 params:
    - infos: 容量变更信息列表，每行包含 cluster_domain、spec_id、count、labels
    """
    return _auth_parse_infos_clusters(request, ClusterType.TenDBCluster)
