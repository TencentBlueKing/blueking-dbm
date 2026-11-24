# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making
蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except
in compliance with the License. You may obtain a copy of the License at
https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed
under the License is distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
import logging
import re

from django.utils.translation import gettext as _

from backend.db_meta.enums import ClusterPhase, ClusterType
from backend.db_meta.models import Cluster
from backend.db_periodic_task import clb_snapshot

logger = logging.getLogger("root")

# 和 tendbcluster_topo_daily_check 跳过的临时域名是同一条规则。
TMP_CLUSTER_DOMAIN = re.compile(r"^.*-tmp[0-9]{8}-[0-9]{7}.*$")


def mysql_clb_snapshot_cluster_ids():
    """online 的 TenDBHA，以及 online 且不是临时域名的 TenDBCluster。"""
    cluster_ids = list(
        Cluster.objects.filter(cluster_type=ClusterType.TenDBHA, phase=ClusterPhase.ONLINE).values_list(
            "id", flat=True
        )
    )
    tendbcluster_rows = Cluster.objects.filter(
        cluster_type=ClusterType.TenDBCluster, phase=ClusterPhase.ONLINE
    ).values_list("id", "immute_domain")
    for cluster_id, domain in tendbcluster_rows:
        if TMP_CLUSTER_DOMAIN.match((domain or "").lower()):
            continue
        cluster_ids.append(cluster_id)
    return cluster_ids


def submit_mysql_clb_snapshot():
    """把名单交给现成的 clb_snapshot.submit。没有 CLB 入口的集群由 submit 跳过，不入队。"""
    cluster_ids = mysql_clb_snapshot_cluster_ids()
    summary = clb_snapshot.submit(cluster_ids)
    logger.info(_("已提交 MySQL CLB 快照，集群 {} 个：{}").format(len(cluster_ids), summary))
