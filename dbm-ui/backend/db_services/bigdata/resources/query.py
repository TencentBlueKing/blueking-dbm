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
from typing import Any, Dict, List

from django.db.models import Count, F, Prefetch, Q, QuerySet, Value
from django.utils.translation import ugettext_lazy as _

from backend import env
from backend.db_meta.enums.cluster_type import ClusterType
from backend.db_meta.models import AppCache
from backend.db_meta.models.cluster import Cluster
from backend.db_meta.models.cluster_entry import ClusterEntry
from backend.db_meta.models.instance import StorageInstance
from backend.db_proxy.models import ClusterExtension
from backend.db_services.dbbase.constants import IP_PORT_DIVIDER
from backend.db_services.dbbase.resources import query
from backend.db_services.ipchooser.query.resource import ResourceQueryHelper
from backend.ticket.constants import InstanceType, TicketType
from backend.ticket.models import ClusterOperateRecord, InstanceOperateRecord
from backend.utils.time import datetime2str


class BigDataBaseListRetrieveResource(query.ListRetrieveResource):
    """
    大数据相关组件资详情基类
    es/kafka/hdfs 分别继承实现各自的资源详情类
    """

    cluster_types = []
    instance_roles = []
    fields = [
        {"name": _("集群名"), "key": "cluster_name"},
        {"name": _("集群别名"), "key": "cluster_alias"},
        {"name": _("集群类型"), "key": "cluster_type"},
        {"name": _("集群类型名"), "key": "cluster_type_name"},
        {"name": _("域名"), "key": "domain"},
        {"name": _("版本"), "key": "major_version"},
        {"name": _("创建人"), "key": "creator"},
        {"name": _("创建人"), "key": "creator"},
        {"name": _("创建时间"), "key": "create_at"},
        {"name": _("更新人"), "key": "updater"},
        {"name": _("更新时间"), "key": "update_at"},
    ]

    @classmethod
    def _list_clusters(cls, bk_biz_id: int, query_params: Dict, limit: int, offset: int) -> query.ResourceList:
        """查询集群信息

        :param bk_biz_id: 业务 ID
        :param query_params: 查询条件. 通过 .serializers.ListResourceSLZ 完成数据校验
        :param limit: 分页查询, 每页展示的数目
        :param offset: 分页查询, 当前页的偏移数
        """

        instance_query = {"bk_biz_id": bk_biz_id, "cluster_type__in": cls.cluster_types}
        cluster_query = instance_query.copy()

        if query_params.get("id"):
            cluster_query["id"] = query_params["id"]

        if query_params.get("domain"):
            cluster_query["immute_domain__icontains"] = query_params["domain"]

        if query_params.get("creator"):
            cluster_query["creator__icontains"] = query_params["creator"]

        clusters = Cluster.objects.filter(**cluster_query)

        if query_params.get("ip"):
            ip_keyword = query_params.get("ip").split(",")
            storages_filter = StorageInstance.objects.filter(machine__ip__in=ip_keyword, **instance_query)
            clusters = clusters.filter(Q(storageinstance__in=storages_filter)).distinct()

        if query_params.get("name"):
            name_keyword = query_params["name"]
            clusters = clusters.filter(Q(name__icontains=name_keyword) | Q(alias__icontains=name_keyword))

        storages = StorageInstance.objects.filter(**instance_query)
        return cls._list(clusters, storages, limit, offset)

    @classmethod
    def list_instances(cls, bk_biz_id: int, query_params: Dict, limit: int, offset: int) -> query.ResourceList:
        instance_filter = Q(bk_biz_id=bk_biz_id, cluster_type__in=cls.cluster_types)

        if query_params.get("ip"):
            ip_keyword = query_params.get("ip").split(",")
            instance_filter = instance_filter & Q(machine__ip__in=ip_keyword)

        if query_params.get("port"):
            instance_filter = instance_filter & Q(port=query_params["port"])

        if query_params.get("status"):
            instance_filter = instance_filter & Q(status=query_params["status"])

        if query_params.get("domain"):
            instance_filter = instance_filter & Q(cluster__immute_domain__icontains=query_params["domain"])

        if query_params.get("role"):
            instance_filter = instance_filter & Q(role=query_params["role"])

        if query_params.get("cluster_id"):
            instance_filter = instance_filter & Q(cluster__id=query_params["cluster_id"])

        # 此处的实例视图仅涉及 storage instance
        storage_instances_queryset = StorageInstance.objects.annotate(
            role=F("instance_role"), type=Value(InstanceType.STORAGE.value)
        ).filter(instance_filter)

        instances_queryset = storage_instances_queryset.values(
            "role",
            "port",
            "status",
            "update_at",
            "create_at",
            "name",
            "type",
            "id",
            "cluster__id",
            "cluster__name",
            "cluster__db_module_id",
            "machine__ip",
            "machine__bk_host_id",
            "machine__bk_cloud_id",
        ).order_by("-create_at")

        instances = instances_queryset[offset : limit + offset]
        cluster_ids = [instance["cluster__id"] for instance in instances]
        cluster_entry_map = ClusterEntry.get_cluster_entry_map_by_cluster_ids(cluster_ids)

        restart_records = InstanceOperateRecord.objects.filter(
            instance_id__in=[instance["id"] for instance in instances],
            ticket__ticket_type__in=[
                TicketType.ES_REBOOT,
                TicketType.HDFS_REBOOT,
                TicketType.KAFKA_REBOOT,
                TicketType.PULSAR_REBOOT,
            ],
        ).order_by("create_at")

        restart_map = {record.instance_id: record.create_at for record in restart_records}

        instances = [cls._to_instance_list(instance, cluster_entry_map, restart_map) for instance in instances]

        return query.ResourceList(count=instances_queryset.count(), data=instances)

    @classmethod
    def _retrieve_cluster(cls, bk_biz_id: int, cluster_id: int) -> dict:
        """获取单个集群详情"""
        cluster = Cluster.objects.get(id=cluster_id)

        cluster.storages = cluster.storageinstance_set.filter(cluster_type=cluster.cluster_type, bk_biz_id=bk_biz_id)
        cluster_entry_map = ClusterEntry.get_cluster_entry_map_by_cluster_ids([cluster.id])

        return cls._to_cluster_detail(cluster, cluster_entry_map)

    @classmethod
    def list_nodes(cls, bk_biz_id: int, query_params: Dict, limit: int, offset: int) -> query.ResourceList:
        cluster_id = query_params["cluster_id"]
        fields = ["machine__ip", "machine__bk_host_id", "machine__bk_cloud_id", "node_count", "role", "create_at"]

        # 聚合实例角色和ip，统计同一ip下同一角色的数量
        # 注意这里一定要用order by覆盖meta中的order by，否则会导致聚合错误
        storage_queryset = (
            StorageInstance.objects.filter(cluster__id=cluster_id, bk_biz_id=bk_biz_id)
            .values("instance_role", "machine__ip")
            .annotate(node_count=Count("id"), role=F("instance_role"))
            .values(*fields)
            .order_by("node_count")
        )

        node_list = list(storage_queryset)
        return cls._to_nodes_list(bk_biz_id=bk_biz_id, node_list=node_list, limit=limit, offset=offset)

    @classmethod
    def get_topo_graph(cls, bk_biz_id: int, cluster_id: int) -> dict:
        # TODO: 暂时不做拓扑
        raise NotImplementedError()

    @classmethod
    def get_nodes(cls, bk_biz_id: int, cluster_id: int, role: str, keyword: str = None) -> list:
        # 由子类来具体实现node节点的筛选逻辑
        raise NotImplementedError()

    @classmethod
    def _list(
        cls,
        clusters: QuerySet,
        qs_storage: QuerySet,
        limit: int,
        offset: int,
    ) -> query.ResourceList:

        count = clusters.count()
        if not count:
            return query.ResourceList(count=0, data=[])

        clusters = clusters.order_by("-create_at")[offset : limit + offset].prefetch_related(
            Prefetch("storageinstance_set", queryset=qs_storage.select_related("machine"), to_attr="storages"),
        )

        cluster_entry_map = ClusterEntry.get_cluster_entry_map_by_cluster_ids(
            list(clusters.values_list("id", flat=True))
        )

        return query.ResourceList(
            count=count, data=[cls._to_cluster_detail(cluster, cluster_entry_map) for cluster in clusters]
        )

    @classmethod
    def _fill_instance_info_in_cluster_detail(cls, cluster: Cluster, cluster_info: Dict) -> Dict[str, Any]:
        """
        为集群信息填充角色实例列表
        :param cluster: model Cluster 对象
        :param cluster_info: 当前的cluster信息
        """
        for role in cls.instance_roles:
            cluster_info.update({role: [inst.simple_desc for inst in cluster.storages if inst.instance_role == role]})

        return cluster_info

    @classmethod
    def _to_cluster_list(cls, cluster: Cluster, cluster_entry_map: Dict[int, Dict[str, str]]) -> Dict[str, Any]:
        """
        集群序列化 - 需要子类继承，展示各自的信息
        :param cluster: model Cluster 对象, 增加了 storages属性
        :param cluster_entry_map: key 是 cluster.id, value 是当前集群对应的 entry 映射
        """

        cluster_entry = cluster_entry_map.get(cluster.id, {})
        cloud_info = ResourceQueryHelper.search_cc_cloud(get_cache=True)
        cluster_info = {
            "id": cluster.id,
            "phase": cluster.phase,
            "phase_name": cluster.get_phase_display(),
            "status": cluster.status,
            "cluster_name": cluster.name,
            "cluster_alias": cluster.alias,
            "major_version": cluster.major_version,
            "bk_biz_id": cluster.bk_biz_id,
            "bk_biz_name": AppCache.objects.get(bk_biz_id=cluster.bk_biz_id).bk_biz_name,
            "bk_cloud_id": cluster.bk_cloud_id,
            "bk_cloud_name": cloud_info[str(cluster.bk_cloud_id)]["bk_cloud_name"],
            "cluster_type": cluster.cluster_type,
            "cluster_type_name": ClusterType.get_choice_label(cluster.cluster_type),
            "operations": ClusterOperateRecord.objects.get_cluster_operations(cluster.id),
            "domain": cluster_entry.get("master_domain", ""),
            "creator": cluster.creator,
            "updater": cluster.updater,
            "create_at": datetime2str(cluster.create_at),
            "update_at": datetime2str(cluster.update_at),
            "access_url": ClusterExtension.get_cluster_service_url(cluster),
        }
        return cls._fill_instance_info_in_cluster_detail(cluster, cluster_info)

    @classmethod
    def _to_cluster_detail(cls, cluster: Cluster, cluster_entry_map: Dict[int, Dict[str, str]]) -> Dict[str, Any]:
        """
        集群序列化
        :param cluster: model Cluster 对象, 增加了 storages属性
        :param cluster_entry_map: key 是 cluster.id, value 是当前集群对应的 entry 映射
        """
        detail = cls._to_cluster_list(cluster, cluster_entry_map)

        # TODO-monitor: 假数据，待监控完善后补齐
        # detail["status"] = 1
        detail["cap_usage"] = 93

        return detail

    @classmethod
    def _to_instance_list(cls, instance: dict, cluster_entry_map: dict, restart_map: dict) -> Dict[str, Any]:
        """实例序列化"""

        instance_id = instance["id"]
        restart_at = restart_map.get(instance_id, "")
        cloud_info = ResourceQueryHelper.search_cc_cloud(get_cache=True)
        return {
            "id": instance_id,
            "cluster_id": instance["cluster__id"],
            "cluster_name": instance["cluster__name"],
            "instance_address": f"{instance['machine__ip']}{IP_PORT_DIVIDER}{instance['port']}",
            "instance_name": instance["name"],
            "bk_host_id": instance["machine__bk_host_id"],
            "bk_cloud_id": instance["machine__bk_cloud_id"],
            "bk_cloud_name": cloud_info[str(instance["machine__bk_cloud_id"])]["bk_cloud_name"],
            "role": instance["role"],
            "domain": cluster_entry_map.get(instance["cluster__id"], {}).get("master_domain", ""),
            "status": instance["status"],
            "create_at": datetime2str(instance["create_at"]),
            "update_at": datetime2str(instance["update_at"]),
            "restart_at": datetime2str(restart_at) if restart_at else restart_at,
            "operations": InstanceOperateRecord.objects.get_locking_operations(instance["id"]),
        }

    @classmethod
    def _to_nodes_list(
        cls, bk_biz_id: int, node_list: List[Dict[str, Any]], limit: int, offset: int
    ) -> query.ResourceList:
        """节点列表序列化"""

        cloud_info = ResourceQueryHelper.search_cc_cloud(get_cache=True)
        host_id__node_list_map = {node["machine__bk_host_id"]: node for node in node_list}
        host_info_map = ResourceQueryHelper.search_cc_hosts(
            env.DBA_APP_BK_BIZ_ID, list(host_id__node_list_map.keys()), keyword=None
        )
        host_id__host_info_map = {host_info["bk_host_id"]: host_info for host_info in host_info_map}
        for host_id, node in host_id__node_list_map.items():
            node["bk_host_id"] = node.pop("machine__bk_host_id")
            node["bk_cloud_id"] = node.pop("machine__bk_cloud_id")
            node["bk_cloud_name"] = cloud_info[str(node["bk_cloud_id"])]["bk_cloud_name"]
            node["ip"] = node.pop("machine__ip")

            # 更新主机cc信息
            host_info = host_id__host_info_map.get(host_id)
            if host_info:
                node.update(
                    {
                        # TODO: 磁盘使用率信息暂时没有
                        "status": host_info.get("status"),
                        "cpu": host_info.get("bk_cpu"),
                        "mem": host_info.get("bk_mem"),
                        "disk": host_info.get("bk_disk"),
                        "machine_type": host_info.get("machine_type"),
                        "bk_host_name": host_info.get("bk_host_name"),
                    }
                )

        group_list = list(host_id__node_list_map.values())
        count = len(group_list)
        paginated_group_list = group_list if limit == -1 else group_list[offset : limit + offset]
        # 按照角色进行排序
        paginated_group_list.sort(key=lambda x: x.get("role") or x.get("role_set"))

        return query.ResourceList(count=count, data=paginated_group_list)
