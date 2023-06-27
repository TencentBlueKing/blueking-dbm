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
from typing import Any, Dict

from django.db.models import F, Prefetch, Q, QuerySet
from django.utils.translation import ugettext_lazy as _

from backend import env
from backend.db_meta.api.cluster.tendiscache.handler import TendisCacheClusterHandler
from backend.db_meta.api.cluster.tendispluscluster.handler import TendisPlusClusterHandler
from backend.db_meta.api.cluster.tendisssd.handler import TendisSSDClusterHandler
from backend.db_meta.enums import InstanceRole
from backend.db_meta.enums.cluster_type import ClusterType
from backend.db_meta.models import AppCache, Machine
from backend.db_meta.models.cluster import Cluster
from backend.db_meta.models.cluster_entry import ClusterEntry
from backend.db_meta.models.instance import ProxyInstance, StorageInstance
from backend.db_services.dbbase.constants import IP_PORT_DIVIDER
from backend.db_services.dbbase.instances.handlers import InstanceHandler
from backend.db_services.dbbase.resources import query
from backend.db_services.ipchooser.query.resource import ResourceQueryHelper
from backend.ticket.models import ClusterOperateRecord
from backend.utils.time import datetime2str


class ListRetrieveResource(query.ListRetrieveResource):
    """查看twemproxy-redis架构的资源"""

    cluster_types = [
        ClusterType.TendisPredixyRedisCluster,
        ClusterType.TendisPredixyTendisplusCluster,
        ClusterType.TendisTwemproxyRedisInstance,
        ClusterType.TwemproxyTendisSSDInstance,
        ClusterType.TendisTwemproxyTendisplusIns,
        ClusterType.TendisRedisInstance,
        ClusterType.TendisTendisplusInsance,
        ClusterType.TendisRedisCluster,
        ClusterType.TendisTendisplusCluster,
    ]
    handler_map = {
        ClusterType.TwemproxyTendisSSDInstance: TendisSSDClusterHandler,
        ClusterType.TendisTwemproxyRedisInstance: TendisCacheClusterHandler,
        ClusterType.TendisPredixyTendisplusCluster: TendisPlusClusterHandler,
    }

    fields = [
        {"name": _("集群名"), "key": "cluster_name"},
        {"name": _("集群别名"), "key": "cluster_alias"},
        {"name": _("集群类型"), "key": "cluster_type"},
        {"name": _("域名"), "key": "master_domain"},
        {"name": "Proxy", "key": "proxy"},
        {"name": "Master", "key": "redis_master"},
        {"name": "Slave", "key": "redis_slave"},
        {"name": _("创建人"), "key": "creator"},
        {"name": _("创建时间"), "key": "create_at"},
        {"name": _("更新人"), "key": "updater"},
        {"name": _("更新时间"), "key": "update_at"},
    ]

    @classmethod
    def list_clusters(cls, bk_biz_id: int, query_params: Dict, limit: int, offset: int) -> query.ResourceList:
        """查询集群信息

        :param bk_biz_id: 业务 ID
        :param query_params: 查询条件. 通过 .serializers.ListResourceSLZ 完成数据校验
        :param limit: 分页查询, 每页展示的数目
        :param offset: 分页查询, 当前页的偏移数
        """

        instance_query = {"bk_biz_id": bk_biz_id, "cluster_type__in": cls.cluster_types}
        cluster_query = instance_query.copy()

        if query_params.get("domain"):
            cluster_query["immute_domain__icontains"] = query_params["domain"]

        clusters = Cluster.objects.filter(**cluster_query)
        if query_params.get("ip"):
            ip_keyword = query_params.get("ip").split(",")
            proxies_filter = ProxyInstance.objects.filter(machine__ip__in=ip_keyword, **instance_query)
            storages_filter = StorageInstance.objects.filter(machine__ip__in=ip_keyword, **instance_query)
            clusters = clusters.filter(
                Q(proxyinstance__in=proxies_filter) | Q(storageinstance__in=storages_filter)
            ).distinct()

        if query_params.get("name"):
            name_keyword = query_params["name"]
            clusters = clusters.filter(Q(name__icontains=name_keyword) | Q(alias__icontains=name_keyword))

        proxies = ProxyInstance.objects.filter(**instance_query)
        storages = StorageInstance.objects.filter(**instance_query)
        return cls._list(clusters, proxies, storages, limit, offset)

    @classmethod
    def list_instances(cls, bk_biz_id: int, query_params: Dict, limit: int, offset: int) -> query.ResourceList:
        qs = Q(bk_biz_id=bk_biz_id, cluster_type__in=cls.cluster_types)

        if query_params.get("cluster_id"):
            qs = qs & Q(cluster__id=query_params["cluster_id"])

        if query_params.get("domain"):
            qs = qs & Q(cluster__immute_domain__icontains=query_params["domain"])

        if query_params.get("ip"):
            ip_keyword = query_params.get("ip").split(",")
            qs = qs & Q(machine__ip__in=ip_keyword)

        if query_params.get("port"):
            qs = qs & Q(port=query_params["port"])

        if query_params.get("status"):
            qs = qs & Q(status=query_params["status"])

        if query_params.get("role"):
            if query_params.get("role") == InstanceRole.REDIS_PROXY:
                query_objs = ProxyInstance.objects.filter(qs).annotate(role=F("access_layer"))
            else:
                qs = qs & Q(instance_role=query_params["role"])
                query_objs = StorageInstance.objects.filter(qs).annotate(role=F("instance_role"))
        else:
            # 此处的实例视图需要同时得到 storage instance 和 proxy instance
            query_objs = (
                StorageInstance.objects.filter(qs)
                .annotate(role=F("instance_role"))
                .union(
                    ProxyInstance.objects.filter(qs).annotate(
                        role=F("access_layer"),
                    )
                )
            )

        instances = query_objs.values(
            "id",
            "cluster__id",
            "cluster__major_version",
            "cluster__cluster_type",
            "cluster__name",
            "port",
            "role",
            "machine__ip",
            "machine__bk_cloud_id",
            "machine__bk_host_id",
            "machine__spec_config",
            "status",
            "create_at",
        ).order_by("port", "-create_at")

        paginated_instances = instances[offset : limit + offset]
        paginated_instances = [cls._to_instance_list(instance) for instance in paginated_instances]

        # 补充实例的额外信息
        if query_params.get("extra"):
            instances_extra_info = InstanceHandler(bk_biz_id).check_instances(query_instances=paginated_instances)
            address__instance_extra_info = {inst["instance_address"]: inst for inst in instances_extra_info}
            for inst in paginated_instances:
                extra_info = address__instance_extra_info[inst["instance_address"]]
                inst.update(host_info=extra_info["host_info"], related_clusters=extra_info["related_clusters"])

        return query.ResourceList(count=instances.count(), data=paginated_instances)

    @classmethod
    def retrieve_cluster(cls, bk_biz_id: int, cluster_id: int) -> dict:
        """获取单个集群详情"""
        cluster = Cluster.objects.get(id=cluster_id)

        cluster.storages = cluster.storageinstance_set.filter(cluster_type=cluster.cluster_type, bk_biz_id=bk_biz_id)
        cluster.proxies = cluster.proxyinstance_set.filter(cluster_type=cluster.cluster_type, bk_biz_id=bk_biz_id)
        cluster_entry_map = ClusterEntry.get_cluster_entry_map_by_cluster_ids([cluster.id])

        return cls._to_cluster_detail(cluster, cluster_entry_map)

    @classmethod
    def get_topo_graph(cls, bk_biz_id: int, cluster_id: int) -> dict:
        cluster = Cluster.objects.get(id=cluster_id)
        handler_cls = cls.handler_map.get(cluster.cluster_type)
        return handler_cls(bk_biz_id, cluster_id).topo_graph()

    @classmethod
    def get_nodes(cls, bk_biz_id: int, cluster_id: int, role: str, keyword: str = None) -> list:
        cluster = Cluster.objects.get(id=cluster_id, bk_biz_id=bk_biz_id)

        storage_instances = cluster.storageinstance_set.all()
        proxy_instances = cluster.proxyinstance_set.all()

        # 以下代码仅针对redis集群架构
        if role == InstanceRole.REDIS_PROXY:
            machines = Machine.objects.filter(ip__in=proxy_instances.values_list("machine"))
        else:
            storage_instances = storage_instances.filter(instance_role=role)
            machines = Machine.objects.filter(ip__in=storage_instances.values_list("machine"))

        role_host_ids = list(machines.values_list("bk_host_id", flat=True))
        return ResourceQueryHelper.search_cc_hosts(env.DBA_APP_BK_BIZ_ID, role_host_ids, keyword)

    @classmethod
    def _list(
        cls,
        clusters: QuerySet,
        qs_proxy: QuerySet,
        qs_storage: QuerySet,
        limit: int,
        offset: int,
    ) -> query.ResourceList:

        count = clusters.count()
        if not count:
            return query.ResourceList(count=0, data=[])

        clusters = clusters.order_by("-create_at")[offset : limit + offset].prefetch_related(
            Prefetch("proxyinstance_set", queryset=qs_proxy, to_attr="proxies"),
            Prefetch("storageinstance_set", queryset=qs_storage, to_attr="storages"),
        )

        cluster_entry_map = ClusterEntry.get_cluster_entry_map_by_cluster_ids(
            list(clusters.values_list("id", flat=True))
        )

        return query.ResourceList(
            count=count, data=[cls._to_cluster_list(cluster, cluster_entry_map) for cluster in clusters]
        )

    @staticmethod
    def _to_cluster_list(cluster, cluster_entry_map: Dict[int, Dict[str, str]]) -> Dict[str, Any]:
        """
        集群序列化
        :param cluster: model Cluster 对象, 增加了 storages 和 proxies 属性
        :param cluster_entry_map: key 是 cluster.id, value 是当前集群对应的 entry 映射
        """
        cluster_entry = cluster_entry_map.get(cluster.id, {})
        cloud_info = ResourceQueryHelper.search_cc_cloud(get_cache=True)
        return {
            "id": cluster.id,
            "phase": cluster.phase,
            "status": cluster.status,
            "cluster_name": cluster.name,
            "cluster_alias": cluster.alias,
            "bk_biz_id": cluster.bk_biz_id,
            "bk_biz_name": AppCache.objects.get(bk_biz_id=cluster.bk_biz_id).bk_biz_name,
            "bk_cloud_id": cluster.bk_cloud_id,
            "bk_cloud_name": cloud_info[str(cluster.bk_cloud_id)]["bk_cloud_name"],
            "major_version": cluster.major_version,
            "region": cluster.region,
            "cluster_type": cluster.cluster_type,
            "cluster_type_name": ClusterType.get_choice_label(cluster.cluster_type),
            "master_domain": cluster_entry.get("master_domain", ""),
            "proxy": [m.simple_desc for m in cluster.proxies],
            InstanceRole.REDIS_MASTER: [
                m.simple_desc for m in cluster.storages if m.instance_role == InstanceRole.REDIS_MASTER
            ],
            InstanceRole.REDIS_SLAVE: [
                m.simple_desc for m in cluster.storages if m.instance_role == InstanceRole.REDIS_SLAVE
            ],
            "operations": ClusterOperateRecord.objects.get_cluster_operations(cluster.id),
            "creator": cluster.creator,
            "updater": cluster.updater,
            "create_at": datetime2str(cluster.create_at),
            "update_at": datetime2str(cluster.update_at),
        }

    @classmethod
    def _to_cluster_detail(cls, cluster, cluster_entry_map: Dict[int, Dict[str, str]]) -> Dict[str, Any]:
        """
        集群序列化
        :param cluster: model Cluster 对象, 增加了 storages 和 proxies 属性
        :param cluster_entry_map: key 是 cluster.id, value 是当前集群对应的 entry 映射
        """
        detail = cls._to_cluster_list(cluster, cluster_entry_map)

        # TODO-monitor: 假数据，待监控完善后补齐
        detail["cap_usage"] = 93

        return detail

    @classmethod
    def _to_instance_list(cls, instance: dict) -> Dict[str, Any]:
        """实例序列化"""

        cloud_info = ResourceQueryHelper.search_cc_cloud(get_cache=True)
        bk_cloud_id = instance["machine__bk_cloud_id"]
        ip, port = instance["machine__ip"], instance["port"]

        return {
            "cluster_id": instance["cluster__id"],
            "cluster_type": instance["cluster__cluster_type"],
            "cluster_name": instance["cluster__name"],
            "ip": ip,
            "bk_cloud_id": bk_cloud_id,
            "bk_cloud_name": cloud_info[str(bk_cloud_id)]["bk_cloud_name"],
            "bk_host_id": instance["machine__bk_host_id"],
            "id": instance["id"],
            "port": port,
            "instance_address": f"{ip}{IP_PORT_DIVIDER}{port}",
            "role": instance["role"],
            "spec_config": instance["machine__spec_config"],
            "status": instance["status"],
            "create_at": datetime2str(instance["create_at"]),
        }
