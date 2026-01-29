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


def auth_parse_mysql_tdbctl_upgrade_ticket(request, *args, **kwargs):
    data = request.query_params if request.method == "GET" else request.data
    bk_biz_id = data.get("bk_biz_id")
    cluster_domain = data.get("cluster_domain")
    cluster_id = data.get("cluster_id")

    clusters = None
    if cluster_domain:
        clusters = Cluster.objects.filter(immute_domain=cluster_domain, cluster_type=ClusterType.TenDBCluster)
    elif cluster_id:
        clusters = Cluster.objects.filter(id=cluster_id, cluster_type=ClusterType.TenDBCluster)
    elif bk_biz_id:
        clusters = Cluster.objects.filter(bk_biz_id=bk_biz_id, cluster_type=ClusterType.TenDBCluster)

    if not clusters or not clusters.exists():
        raise ValueError("No clusters found for the given params")

    cluster_ids = list(clusters.values_list("id", flat=True))
    return cluster_ids
