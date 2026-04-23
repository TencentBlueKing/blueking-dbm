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
from typing import List, Optional

from django.db.models import Q

from backend.configuration.models import DBAdministrator
from backend.db_meta.enums import ClusterEntryType, ClusterType
from backend.db_meta.models import Cluster
from backend.db_meta.models.cluster_entry import ClusterEntry


def list_biz_clusters(
    ips: Optional[List[str]] = None,
    instances: Optional[List[str]] = None,
    cluster_domains: Optional[List[str]] = None,
    bk_biz_id: Optional[int] = None,
) -> List[dict]:
    """根据 IP / 实例 / 域名查询集群基本信息"""

    # 收集所有匹配的 cluster id，每种条件独立查询，避免多表 JOIN 产生笛卡尔积
    cluster_id_sets: List[set] = []

    if ips:
        # storageinstance 关联的集群
        storage_ids = set(Cluster.objects.filter(storageinstance__machine__ip__in=ips).values_list("id", flat=True))
        # proxyinstance 关联的集群
        proxy_ids = set(Cluster.objects.filter(proxyinstance__machine__ip__in=ips).values_list("id", flat=True))
        # CLB entry 关联的集群
        clb_ids = set(
            ClusterEntry.objects.filter(cluster_entry_type=ClusterEntryType.CLB, entry__in=ips).values_list(
                "cluster_id", flat=True
            )
        )
        cluster_id_sets.append(storage_ids | proxy_ids | clb_ids)

    if instances:
        instance_ids: set = set()
        for instance in instances:
            ip, port = instance.split(":")
            # storageinstance 匹配
            instance_ids.update(
                Cluster.objects.filter(storageinstance__machine__ip=ip, storageinstance__port=port).values_list(
                    "id", flat=True
                )
            )
            # proxyinstance 匹配
            instance_ids.update(
                Cluster.objects.filter(proxyinstance__machine__ip=ip, proxyinstance__port=port).values_list(
                    "id", flat=True
                )
            )
        cluster_id_sets.append(instance_ids)

    if cluster_domains:
        # DNS / CLBDNS entry 关联的集群
        domain_ids = set(
            ClusterEntry.objects.filter(
                cluster_entry_type__in=[ClusterEntryType.DNS, ClusterEntryType.CLBDNS], entry__in=cluster_domains
            ).values_list("cluster_id", flat=True)
        )
        cluster_id_sets.append(domain_ids)

    # 合并所有条件匹配的 cluster id（各条件之间是 OR 关系）
    if not cluster_id_sets:
        return []

    merged_ids: set = set()
    for id_set in cluster_id_sets:
        merged_ids |= id_set

    if not merged_ids:
        return []

    # 最终只做一次简单的 id__in 查询
    q = Q(id__in=merged_ids)
    if bk_biz_id:
        q &= Q(bk_biz_id=bk_biz_id)

    results = []
    for cluster_obj in Cluster.objects.filter(q):
        db_type = ClusterType.cluster_type_to_db_type(cluster_obj.cluster_type)
        dbas = DBAdministrator.get_biz_db_type_admins(bk_biz_id=cluster_obj.bk_biz_id, db_type=db_type)

        # 按 key 聚合 tag values，加 tag_ 前缀作为顶级动态字段
        tag_fields: dict = {}
        for tag in cluster_obj.tags.all():
            tag_fields.setdefault(f"tag_{tag.key}", []).append(tag.value)

        cluster_info = {
            "bk_biz_id": cluster_obj.bk_biz_id,
            "bk_cloud_id": cluster_obj.bk_cloud_id,
            "cluster_type": cluster_obj.cluster_type,
            "cluster_domain": cluster_obj.immute_domain,
            "region": cluster_obj.region,
            "affinity": cluster_obj.disaster_tolerance_level,
            "status": cluster_obj.status,
            "phase": cluster_obj.phase,
            "creator": cluster_obj.creator,
            "dbas": dbas[:2],
            **tag_fields,
        }
        results.append(cluster_info)
    return results
