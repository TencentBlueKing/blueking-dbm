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
import json

from django.core.cache import cache
from django.forms import model_to_dict
from django.utils.translation import gettext_lazy as _

from backend.db_meta.api.cluster.doris.detail import scan_cluster
from backend.db_meta.enums import InstanceRole
from backend.db_meta.enums.cluster_type import ClusterType
from backend.db_meta.models import Machine
from backend.db_meta.models.cluster import Cluster
from backend.db_meta.models.storage_set_dtl import DorisResourceSet
from backend.db_services.bigdata.doris.upgrade_policy import DorisUpgradeVersionPolicy
from backend.db_services.bigdata.resources.query import (
    BigDataBaseExportQueryResourceMixin,
    BigDataBaseListRetrieveResource,
)
from backend.db_services.dbbase.resources.register import register_resource_decorator
from backend.db_services.ipchooser.query.resource import ResourceQueryHelper
from backend.flow.utils.doris.consts import CACHE_CLUSTER_MASTER, CACHE_DORIS_REMOTE_USED, DorisResourceTag


class DorisExportQueryResourceMixin(BigDataBaseExportQueryResourceMixin):
    """补充Doris集群列表导出所需的header及数据"""

    @classmethod
    def update_headers(cls, headers, **kwargs):
        # 补充实例为空未展示的字段
        extra_headers = [
            {"id": "doris_backend_hot", "name": _("热节点")},
            {"id": "doris_backend_warm", "name": _("温节点")},
            {"id": "doris_backend_cold", "name": _("冷节点")},
            {"id": "doris_follower", "name": _("Follower")},
            {"id": "doris_observer", "name": _("Observer")},
        ]

        return super().update_headers(headers, extra_headers=extra_headers)


@register_resource_decorator()
class DorisListRetrieveResource(BigDataBaseListRetrieveResource, DorisExportQueryResourceMixin):
    cluster_types = [ClusterType.Doris]
    instance_roles = [
        InstanceRole.DORIS_FOLLOWER.value,
        InstanceRole.DORIS_OBSERVER.value,
        InstanceRole.DORIS_BACKEND_HOT.value,
        InstanceRole.DORIS_BACKEND_WARM.value,
    ]
    fields = [
        *BigDataBaseListRetrieveResource.fields,
        {"name": _("Follower节点"), "key": "doris_follower_nodes"},
        {"name": _("Observer节点"), "key": "doris_observer_nodes"},
        {"name": _("热节点"), "key": "doris_hot_nodes"},
        {"name": _("冷节点"), "key": "doris_cold_nodes"},
    ]

    @classmethod
    def _get_cached_master_map(cls, bk_biz_id: int) -> dict:
        master_map = {}
        for cluster_type in cls.cluster_types:
            master_map.update(json.loads(cache.get(f"{CACHE_CLUSTER_MASTER}_{bk_biz_id}_{cluster_type}", "{}")))
        return master_map

    @classmethod
    def _to_cluster_representation(
        cls,
        cluster,
        cluster_entry,
        db_module_names_map,
        cluster_entry_map,
        cluster_operate_records_map,
        cloud_info,
        biz_info,
        cluster_stats_map,
        cluster_zone_map,
        dns_to_clb=False,
        **kwargs,
    ) -> dict:
        cluster_info = super()._to_cluster_representation(
            cluster=cluster,
            cluster_entry=cluster_entry,
            db_module_names_map=db_module_names_map,
            cluster_entry_map=cluster_entry_map,
            cluster_operate_records_map=cluster_operate_records_map,
            cloud_info=cloud_info,
            biz_info=biz_info,
            cluster_stats_map=cluster_stats_map,
            cluster_zone_map=cluster_zone_map,
            dns_to_clb=dns_to_clb,
            **kwargs,
        )

        master_address = cls._get_cached_master_map(cluster.bk_biz_id).get(cluster.immute_domain)
        for follower in cluster_info.get(InstanceRole.DORIS_FOLLOWER.value, []):
            follower["is_master"] = follower["instance"] == master_address

        return cluster_info

    @classmethod
    def _filter_instance_hook(cls, bk_biz_id, query_params, instances, **kwargs):
        instances = list(instances)
        cluster_ids = list({instance["cluster__id"] for instance in instances})
        kwargs["master_map"] = cls.get_clusters_master(bk_biz_id, cluster_ids)
        return super()._filter_instance_hook(bk_biz_id, query_params, instances, **kwargs)

    @classmethod
    def _to_instance_representation(
        cls, instance: dict, cluster_entry_map: dict, db_module_names_map: dict, **kwargs
    ) -> dict:
        instance_info = super()._to_instance_representation(instance, cluster_entry_map, db_module_names_map, **kwargs)
        master_address = kwargs.get("master_map", {}).get(instance["cluster__id"], "")
        instance_info["is_master"] = (
            instance["role"] == InstanceRole.DORIS_FOLLOWER.value
            and instance_info["instance_address"] == master_address
        )
        return instance_info

    @classmethod
    def get_nodes(cls, bk_biz_id: int, cluster_id: int, role: str, keyword: str = None) -> list:
        cluster = Cluster.objects.get(id=cluster_id, bk_biz_id=bk_biz_id)

        storage_instances = cluster.storageinstance_set.filter(instance_role=role)
        machines = Machine.objects.filter(bk_host_id__in=storage_instances.values_list("machine", flat=True))

        role_host_ids = list(machines.values_list("bk_host_id", flat=True))
        return ResourceQueryHelper.search_cc_hosts(role_host_ids, keyword)

    @classmethod
    def get_topo_graph(cls, bk_biz_id: int, cluster_id: int) -> dict:
        cluster = Cluster.objects.get(bk_biz_id=bk_biz_id, id=cluster_id)
        graph = scan_cluster(cluster).to_dict()
        return graph

    @classmethod
    def get_cold_resource(cls, bk_biz_id: int, cluster_id: int) -> dict:
        """获取Doris集群冷存储资源, 仅从Cache中获取资源用量"""
        cluster = Cluster.objects.get(bk_biz_id=bk_biz_id, id=cluster_id)
        res_set = DorisResourceSet.objects.filter(cluster=cluster, resource__tag=DorisResourceTag.PRIVATE.value)
        res = res_set.first().resource if res_set.exists() else None
        # 若 冷存储资源存在，获取资源用量
        if res:
            # 从cache获取Doris集群远程存储用量(按业务ID维度)
            cache_remote_used = cache.get(f"{CACHE_DORIS_REMOTE_USED}_{bk_biz_id}", {})
            # cache中内容为域名:用量
            used = cache_remote_used.get(cluster.immute_domain, 0)
            res_dict = model_to_dict(res, fields=["id", "name", "region"])
            res_dict["used"] = used
            return res_dict
        else:
            return {}

    @classmethod
    def get_clusters_master(cls, bk_biz_id: int, cluster_ids: list) -> dict:
        """获取Doris集群主节点信息，只从Cache中获取"""
        cache_master_stats = {}
        for cluster_type in cls.cluster_types:
            cache_master_stats.update(
                json.loads(cache.get(f"{CACHE_CLUSTER_MASTER}_{bk_biz_id}_{cluster_type.value}", "{}"))
            )
        # 获取集群域名和集群ID的映射
        cluster_domain_qs = Cluster.objects.filter(
            bk_biz_id=bk_biz_id, id__in=cluster_ids, cluster_type=ClusterType.Doris
        ).values("immute_domain", "id")
        domain_ids = {cluster["immute_domain"]: cluster["id"] for cluster in cluster_domain_qs}

        # 返回集群ID和主节点信息的映射
        cluster_stat_map = {
            domain_ids[domain]: master for domain, master in cache_master_stats.items() if domain in domain_ids
        }

        return cluster_stat_map

    @classmethod
    def retrieve_cluster(cls, bk_biz_id: int, cluster_id: int) -> dict:
        """查询集群详情"""
        cluster_details = cls.list_clusters(bk_biz_id, {"id": cluster_id}, limit=1, offset=0).data[0]
        details = cls._retrieve_cluster(cluster_details, cluster_id)
        details["cold_resource"] = cls.get_cold_resource(bk_biz_id, cluster_id)
        return details

    @classmethod
    def list_upgradable_versions(cls, bk_biz_id: int, cluster_id: int) -> list:
        """
        查询 Doris 集群可升级到的版本列表

        规则收敛在 DorisUpgradeVersionPolicy 中（series 白名单 + 严格大于 + 介质存在性），
        此处只负责定位集群、调用 policy 并对结果做保序去重。
        """
        cluster = Cluster.objects.get(id=cluster_id, bk_biz_id=bk_biz_id, cluster_type=ClusterType.Doris)
        candidates = DorisUpgradeVersionPolicy.list_candidates(cluster.major_version)
        # 保序去重（同一 version 可能因 priority/update_at 维度有多条 Package 记录）
        return list(dict.fromkeys(candidates.values_list("version", flat=True)))
