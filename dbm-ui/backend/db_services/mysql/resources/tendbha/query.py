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
import copy
from typing import Any, Dict

from django.db.models import F, Prefetch, Q, QuerySet
from django.utils.translation import ugettext_lazy as _

from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.api.cluster.tendbha.detail import scan_cluster
from backend.db_meta.enums import InstanceInnerRole
from backend.db_meta.enums.cluster_type import ClusterType
from backend.db_meta.models import AppCache
from backend.db_meta.models.cluster import Cluster
from backend.db_meta.models.cluster_entry import ClusterEntry
from backend.db_meta.models.db_module import DBModule
from backend.db_meta.models.instance import ProxyInstance, StorageInstance
from backend.db_services.dbbase.instances.handlers import InstanceHandler
from backend.db_services.dbbase.resources import query
from backend.db_services.ipchooser.query.resource import ResourceQueryHelper
from backend.ticket.models import ClusterOperateRecord
from backend.utils.time import datetime2str


class ListRetrieveResource(query.ListRetrieveResource):
    """查看 mysql dbha 架构的资源"""

    cluster_type = ClusterType.TenDBHA

    fields = [
        {"name": _("集群名"), "key": "cluster_name"},
        {"name": _("主域名"), "key": "master_domain"},
        {"name": _("从域名"), "key": "slave_domain"},
        {"name": "Proxy", "key": "proxies"},
        {"name": "Master", "key": "masters"},
        {"name": "Slave", "key": "slaves"},
        {"name": _("所属db模块"), "key": "db_module_name"},
        {"name": _("创建人"), "key": "creator"},
        {"name": _("创建时间"), "key": "create_at"},
    ]

    @classmethod
    def _list_clusters(cls, bk_biz_id: int, query_params: Dict, limit: int, offset: int) -> query.ResourceList:
        """
        查询集群信息
        :param bk_biz_id: 业务 ID
        :param query_params: 查询条件. 通过 .serializers.ListResourceSLZ 完成数据校验
        :param limit: 分页查询, 每页展示的数目
        :param offset: 分页查询, 当前页的偏移数
        """
        query_filters = Q(bk_biz_id=bk_biz_id, cluster_type=cls.cluster_type)
        if query_params.get("db_module_id"):
            query_filters &= Q(db_module_id=query_params["db_module_id"])

        cluster_query = copy.deepcopy(query_filters)
        proxy_query = copy.deepcopy(query_filters)
        storage_query = copy.deepcopy(query_filters)

        proxy_inst_qset = ProxyInstance.objects.filter(proxy_query)
        storage_inst_qset = StorageInstance.objects.filter(storage_query)

        if query_params.get("id"):
            cluster_query &= Q(id=query_params["id"])

        if query_params.get("name"):
            cluster_query &= Q(name__icontains=query_params["name"])

        if query_params.get("version"):
            cluster_query &= Q(major_version=query_params["version"])

        if query_params.get("region"):
            cluster_query &= Q(region=query_params["region"])

        if query_params.get("domain"):
            # 考虑从域名的筛选
            cluster_entry_set = ClusterEntry.objects.filter(entry__icontains=query_params["domain"])
            cluster_query &= Q(clusterentry__in=cluster_entry_set)

        if query_params.get("cluster_ids"):
            cluster_query &= Q(id__in=query_params["cluster_ids"])

        if query_params.get("creator"):
            cluster_query &= Q(creator__icontains=query_params["creator"])

        # 这里需要加distinct，否则domain的过滤会导致出现重复集群
        cluster_qset = Cluster.objects.filter(cluster_query).distinct()

        if query_params.get("ip"):
            filter_ip = query_params.get("ip").split(",")
            proxy_ip_filter = proxy_inst_qset.filter(machine__ip__in=filter_ip)
            storage_ip_filter = storage_inst_qset.filter(machine__ip__in=filter_ip)
            # 这里如果不用distinct，会查询出重复记录。TODO: 排查查询重复记录的原因
            cluster_qset = cluster_qset.filter(
                Q(proxyinstance__in=proxy_ip_filter) | Q(storageinstance__in=storage_ip_filter)
            ).distinct()

        db_module_names = {
            module.db_module_id: module.db_module_name
            for module in DBModule.objects.filter(bk_biz_id=bk_biz_id, cluster_type=cls.cluster_type)
        }

        cluster_infos = cls._list(cluster_qset, proxy_inst_qset, storage_inst_qset, db_module_names, limit, offset)
        return cluster_infos

    @staticmethod
    def _filter_instance_qs(query_conditions, query_params):
        """获取过滤的queryset"""
        instances_qs = (
            # 此处的实例视图需要同时得到 storage instance 和 proxy instance
            StorageInstance.objects.select_related("machine")
            .prefetch_related("cluster")
            .annotate(role=F("instance_inner_role"))
            .filter(query_conditions)
            .union(
                ProxyInstance.objects.annotate(role=F("access_layer"))
                .select_related("machine")
                .prefetch_related("cluster")
                .filter(query_conditions)
            )
            .values(
                "id",
                "role",
                "port",
                "status",
                "create_at",
                "cluster__id",
                "cluster__major_version",
                "cluster__cluster_type",
                "cluster__db_module_id",
                "cluster__name",
                "machine__ip",
                "machine__bk_cloud_id",
                "machine__bk_host_id",
                "machine__spec_config",
            )
            .order_by("-create_at")
        )
        return instances_qs

    @classmethod
    def list_instances(cls, bk_biz_id: int, query_params: Dict, limit: int, offset: int) -> query.ResourceList:
        query_conditions = Q(bk_biz_id=bk_biz_id, cluster_type=cls.cluster_type)

        if query_params.get("ip"):
            filter_ip = query_params.get("ip").split(",")
            query_conditions &= Q(machine__ip__in=filter_ip)

        if query_params.get("port"):
            query_conditions &= Q(port=query_params["port"])

        if query_params.get("status"):
            query_conditions &= Q(status=query_params["status"])

        if query_params.get("cluster_id"):
            query_conditions &= Q(cluster__id=query_params["cluster_id"])

        if query_params.get("role"):
            query_conditions &= Q(role=query_params["role"])

        if query_params.get("role_exclude"):
            query_conditions &= ~Q(role=query_params["role_exclude"])

        if query_params.get("domain"):
            master_domain_query = Q(cluster__immute_domain__icontains=query_params["domain"])
            slave_domain_query = Q(bind_entry__entry__icontains=query_params["domain"])
            query_conditions &= master_domain_query | slave_domain_query

        instances_qs = cls._filter_instance_qs(query_conditions, query_params)
        instances = instances_qs[offset : limit + offset]
        cluster_ids = [instance["cluster__id"] for instance in instances]
        cluster_entry_map = ClusterEntry.get_cluster_entry_map_by_cluster_ids(cluster_ids)
        instances = [cls._to_instance_representation(instance, cluster_entry_map) for instance in instances]

        # 补充实例的额外信息
        if query_params.get("extra"):
            instances_extra_info = InstanceHandler(bk_biz_id).check_instances(query_instances=instances)
            address__instance_extra_info = {inst["instance_address"]: inst for inst in instances_extra_info}
            for inst in instances:
                extra_info = address__instance_extra_info[inst["instance_address"]]
                inst.update(host_info=extra_info["host_info"], related_clusters=extra_info["related_clusters"])

        return query.ResourceList(count=instances_qs.count(), data=instances)

    @classmethod
    def _retrieve_cluster(cls, bk_biz_id: int, cluster_id: int) -> dict:
        """获取单个集群详情"""
        cluster = Cluster.objects.get(id=cluster_id, bk_biz_id=bk_biz_id, cluster_type=cls.cluster_type)

        cluster.storages = cluster.storageinstance_set.filter(cluster_type=cls.cluster_type, bk_biz_id=bk_biz_id)
        cluster.proxies = cluster.proxyinstance_set.filter(cluster_type=cls.cluster_type, bk_biz_id=bk_biz_id)

        db_module_names = {
            module.db_module_id: module.db_module_name
            for module in DBModule.objects.filter(db_module_id=cluster.db_module_id)
        }
        cluster_entry_map = ClusterEntry.get_cluster_entry_map_by_cluster_ids([cluster.id])
        return cls._to_cluster_representation_with_instances(cluster, db_module_names, cluster_entry_map)

    @classmethod
    def get_topo_graph(cls, bk_biz_id: int, cluster_id: int) -> dict:
        cluster = Cluster.objects.get(bk_biz_id=bk_biz_id, id=cluster_id)
        graph = scan_cluster(cluster).to_dict()
        return graph

    @classmethod
    def _list(
        cls,
        cluster_qset: QuerySet,
        proxy_inst_qset: QuerySet,
        storage_inst_qset: QuerySet,
        db_module_names: Dict[int, str],
        limit: int,
        offset: int,
    ) -> query.ResourceList:
        """
        为查询的集群填充额外信息
        @param cluster_qset: 过滤集群查询集
        @param proxy_inst_qset: 过滤的proxy查询集
        @param storage_inst_qset: 过滤的storage查询集
        @param db_module_names: 模块ID与模块名的映射
        @param limit: 分页限制
        @param offset: 分页起始
        """

        count = cluster_qset.count()
        limit = count if limit == -1 else limit
        if count == 0:
            return query.ResourceList(count=0, data=[])

        cluster_qset = cluster_qset.order_by("-create_at")[offset : limit + offset].prefetch_related(
            Prefetch("proxyinstance_set", queryset=proxy_inst_qset.select_related("machine"), to_attr="proxies"),
            Prefetch("storageinstance_set", queryset=storage_inst_qset.select_related("machine"), to_attr="storages"),
            "tag_set",
        )
        cluster_entry_map = ClusterEntry.get_cluster_entry_map_by_cluster_ids([cluster.id for cluster in cluster_qset])

        clusters = []
        for cluster in cluster_qset:
            clusters.append(cls._to_cluster_representation(cluster, db_module_names, cluster_entry_map))

        return query.ResourceList(count=count, data=clusters)

    @classmethod
    def _to_cluster_representation(
        cls, cluster: Cluster, db_module_names: Dict[int, str], cluster_entry_map: Dict[int, Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        将集群对象转为可序列化的 dict 结构

        :param cluster: model Cluster 对象, 增加了 storages 和 proxies 属性
        :param db_module_names: key 是 db_module_id, value 是 db_module_name
        :param cluster_entry_map: key 是 cluster.id, value 是当前集群对应的 entry 映射
        """
        cluster_entry = cluster_entry_map.get(cluster.id, {})
        proxies = [m.simple_desc for m in cluster.proxies]
        masters = [m.simple_desc for m in cluster.storages if m.instance_inner_role == InstanceInnerRole.MASTER]
        slaves = [m.simple_desc for m in cluster.storages if m.instance_inner_role == InstanceInnerRole.SLAVE]
        cloud_info = ResourceQueryHelper.search_cc_cloud(get_cache=True)
        return {
            "id": cluster.id,
            "phase": cluster.phase,
            "phase_name": cluster.get_phase_display(),
            "status": cluster.status,
            "operations": ClusterOperateRecord.objects.get_cluster_operations(cluster.id),
            "cluster_name": cluster.name,
            "cluster_type": cluster.cluster_type,
            "master_domain": cluster_entry.get("master_domain", ""),
            "slave_domain": cluster_entry.get("slave_domain", ""),
            "bk_biz_id": cluster.bk_biz_id,
            "bk_biz_name": AppCache.objects.get(bk_biz_id=cluster.bk_biz_id).bk_biz_name,
            "bk_cloud_id": cluster.bk_cloud_id,
            "bk_cloud_name": cloud_info[str(cluster.bk_cloud_id)]["bk_cloud_name"],
            "proxies": proxies,
            "masters": masters,
            "slaves": slaves,
            "db_module_name": db_module_names.get(cluster.db_module_id, ""),
            "db_module_id": cluster.db_module_id,
            "creator": cluster.creator,
            "create_at": datetime2str(cluster.create_at),
        }

    @classmethod
    def _to_cluster_representation_with_instances(
        cls, cluster: Cluster, db_module_names: Dict[int, str], cluster_entry_map: Dict[int, Dict[str, str]]
    ) -> Dict[str, Any]:
        """
        添加实例的相关信息
        """
        instances = [inst.ip_port for inst in [*cluster.proxies, *cluster.storages]]
        cluster_info = cls._to_cluster_representation(cluster, db_module_names, cluster_entry_map)
        cluster_info.update(instances=InstanceHandler(bk_biz_id=cluster.bk_biz_id).check_instances(instances))
        return cluster_info

    @classmethod
    def _to_instance_representation(cls, instance: dict, cluster_entry_map: dict) -> Dict[str, Any]:
        """
        instance: Dict
            {
            }
        """
        cloud_info = ResourceQueryHelper.search_cc_cloud(get_cache=True)
        # 适配spider的port获取方式
        port = instance.get("port") or instance.get("inst_port")
        return {
            "id": instance["id"],
            "cluster_id": instance["cluster__id"],
            "cluster_type": instance["cluster__cluster_type"],
            "cluster_name": instance["cluster__name"],
            "version": instance["cluster__major_version"],
            "db_module_id": instance["cluster__db_module_id"],
            "bk_cloud_id": instance["machine__bk_cloud_id"],
            "bk_cloud_name": cloud_info[str(instance["machine__bk_cloud_id"])]["bk_cloud_name"],
            "ip": instance["machine__ip"],
            "port": port,
            "instance_address": f"{instance['machine__ip']}{IP_PORT_DIVIDER}{port}",
            "bk_host_id": instance["machine__bk_host_id"],
            "role": instance["role"],
            "master_domain": cluster_entry_map.get(instance["cluster__id"], {}).get("master_domain", ""),
            "slave_domain": cluster_entry_map.get(instance["cluster__id"], {}).get("slave_domain", ""),
            "status": instance["status"],
            "create_at": datetime2str(instance["create_at"]),
            "spec_config": instance["machine__spec_config"],
        }
