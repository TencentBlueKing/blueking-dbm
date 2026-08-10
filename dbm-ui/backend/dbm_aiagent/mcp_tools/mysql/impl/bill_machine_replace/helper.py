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
from typing import List, Tuple

from django.db.models import QuerySet
from django.utils.translation import gettext_lazy as _

from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster
from backend.dbm_aiagent.mcp_tools.mysql.constants import MYSQL_MCP_DB_READ


def validate_clusters(cluster_domains: List[str], cluster_type: ClusterType) -> Tuple[QuerySet, int, int]:
    cluster_objs = Cluster.objects.using(MYSQL_MCP_DB_READ).filter(
        immute_domain__in=cluster_domains, cluster_type=cluster_type
    )
    if not cluster_objs.exists():
        raise Exception(_("未找到集群: {}").format(cluster_domains))

    if cluster_objs.count() != len(cluster_domains):
        found_domains = set(cluster_objs.values_list("immute_domain", flat=True))
        missing = set(cluster_domains) - found_domains
        raise Exception(_("部分集群未找到: {}").format(sorted(missing)))

    bk_biz_ids = list(set(cluster_objs.values_list("bk_biz_id", flat=True)))
    if len(bk_biz_ids) > 1:
        raise Exception("multi bk biz id found: {}".format(bk_biz_ids))

    return cluster_objs, bk_biz_ids[0], cluster_objs[0].bk_cloud_id


def check_clusters_consistency(input_clusters: QuerySet, ips: List[str], instance_objs: QuerySet):
    instance_ips = set(instance_objs.values_list("machine__ip", flat=True))
    input_ips = set(ips)
    if instance_ips != input_ips:
        missing = input_ips - instance_ips
        raise Exception(_("部分 IP 未找到对应实例: {}").format(sorted(missing)))

    input_set = set(input_clusters.values_list("id", "immute_domain", "cluster_type"))

    inconsistencies = []
    for ip in ips:
        ip_instances = instance_objs.filter(machine__ip=ip)
        per_ip_clusters = set(
            Cluster.objects.using(MYSQL_MCP_DB_READ)
            .filter(pk__in=ip_instances.values_list("cluster", flat=True))
            .distinct()
            .values_list("id", "immute_domain", "cluster_type")
        )
        if per_ip_clusters != input_set:
            inconsistencies.append(
                _("IP {ip}: 归属集群={ip_clusters}").format(
                    ip=ip,
                    ip_clusters=sorted(t[1] for t in per_ip_clusters),
                )
            )

    if inconsistencies:
        raise Exception(
            _("IP 归属集群与输入集群不一致: 输入集群={input_clusters}, {detail}").format(
                input_clusters=sorted(t[1] for t in input_set),
                detail="; ".join(inconsistencies),
            )
        )
