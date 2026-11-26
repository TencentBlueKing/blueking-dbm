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
from typing import Dict, List, Optional

from django.core.cache import cache

from backend import env
from backend.components import BKMonitorV3Api
from backend.db_meta.enums import ClusterType
from backend.db_meta.models import AppCache, Cluster
from backend.db_services.plugin.constants import SubscribeAggregateType

SUBSCRIBE_RELATIONS_CACHE_KEY = "monitor_subscribe_relations"
SUBSCRIBE_RELATIONS_CACHE_TTL = 5 * 60
SUBSCRIBE_AGGREGATE_SEPARATOR = ","


class SubscribeRelationHandler:
    """个人告警订阅关系(账号 x 集群)，供 BKVision 订阅仪表盘使用"""

    @classmethod
    def list_relations(
        cls,
        bk_biz_name: str = "",
        db_types: Optional[List[str]] = None,
        cluster_domain: str = "",
        username: str = "",
        aggregate: str = "",
    ) -> List[Dict]:
        relations = cls.get_cached_relations()
        if bk_biz_name:
            relations = [r for r in relations if r["bk_biz_name"] == bk_biz_name]
        if db_types:
            relations = [r for r in relations if r["db_type"] in db_types]
        if cluster_domain:
            relations = [r for r in relations if cluster_domain in r["cluster_domain"]]
        if username:
            relations = [r for r in relations if username in r["username"]]

        if aggregate == SubscribeAggregateType.CLUSTER:
            return cls.aggregate_by_cluster(relations)
        if aggregate == SubscribeAggregateType.ACCOUNT:
            return cls.aggregate_by_account(relations)
        return relations

    @staticmethod
    def aggregate_by_cluster(relations: List[Dict]) -> List[Dict]:
        cluster_map: Dict[str, Dict] = {}
        for relation in relations:
            info = cluster_map.setdefault(
                relation["cluster_domain"],
                {
                    "cluster_domain": relation["cluster_domain"],
                    "bk_biz_name": relation["bk_biz_name"],
                    "db_type": relation["db_type"],
                    "subscribers": [],
                },
            )
            info["subscribers"].append(relation["username"])

        results = [
            {
                **info,
                "subscribers": SUBSCRIBE_AGGREGATE_SEPARATOR.join(info["subscribers"]),
                "subscriber_count": len(info["subscribers"]),
            }
            for info in cluster_map.values()
        ]
        return sorted(results, key=lambda r: (-r["subscriber_count"], r["cluster_domain"]))

    @staticmethod
    def aggregate_by_account(relations: List[Dict]) -> List[Dict]:
        account_map: Dict[str, List[str]] = {}
        for relation in relations:
            account_map.setdefault(relation["username"], []).append(relation["cluster_domain"])

        results = [
            {
                "username": username,
                "cluster_count": len(domains),
                "clusters": SUBSCRIBE_AGGREGATE_SEPARATOR.join(domains),
            }
            for username, domains in account_map.items()
        ]
        return sorted(results, key=lambda r: (-r["cluster_count"], r["username"]))

    @classmethod
    def get_cached_relations(cls) -> List[Dict]:
        relations = cache.get(SUBSCRIBE_RELATIONS_CACHE_KEY)
        if relations is None:
            relations = cls.build_relations()
            cache.set(SUBSCRIBE_RELATIONS_CACHE_KEY, relations, SUBSCRIBE_RELATIONS_CACHE_TTL)
        return relations

    @classmethod
    def build_relations(cls) -> List[Dict]:
        subscribes = BKMonitorV3Api.list_full_subscribe(bk_biz_id=env.DBA_APP_BK_BIZ_ID)

        user_domains = []
        for sub in subscribes:
            conditions_map = {c["field"]: c["value"] for c in sub.get("conditions") or []}
            domains = conditions_map.get("tags.cluster_domain")
            if sub.get("username") and domains:
                user_domains.append((sub["username"], domains[0]))

        # 仅保留当前仍存在的集群，业务以集群当前所属业务为准
        clusters = Cluster.objects.filter(immute_domain__in={domain for _, domain in user_domains}).values(
            "immute_domain", "bk_biz_id", "cluster_type"
        )
        cluster_map = {c["immute_domain"]: c for c in clusters}
        # appcache_dict 命中缓存时 key 为 str(JSON 序列化)，未命中时为 int，统一转为 int
        bizs = AppCache.get_appcache(key="appcache_dict") or {}
        biz_name_map = {int(bk_biz_id): biz["bk_biz_name"] for bk_biz_id, biz in bizs.items()}

        relations, seen = [], set()
        for username, domain in user_domains:
            cluster = cluster_map.get(domain)
            if not cluster or (username, domain) in seen:
                continue
            seen.add((username, domain))
            relations.append(
                {
                    "cluster_domain": domain,
                    "bk_biz_name": biz_name_map.get(cluster["bk_biz_id"]) or str(cluster["bk_biz_id"]),
                    "db_type": ClusterType.cluster_type_to_db_type(cluster["cluster_type"]),
                    "username": username,
                }
            )
        return relations
