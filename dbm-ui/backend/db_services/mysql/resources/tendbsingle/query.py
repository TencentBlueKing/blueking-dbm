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

from django.db.models import Prefetch, Q
from django.db.models.query import QuerySet
from django.utils.translation import ugettext_lazy as _

from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.api.cluster.tendbsingle.detail import scan_cluster
from backend.db_meta.enums.cluster_type import ClusterType
from backend.db_meta.models import AppCache
from backend.db_meta.models.cluster import Cluster
from backend.db_meta.models.db_module import DBModule
from backend.db_meta.models.instance import StorageInstance
from backend.db_services.dbbase.instances.handlers import InstanceHandler
from backend.db_services.dbbase.resources import query
from backend.db_services.ipchooser.query.resource import ResourceQueryHelper
from backend.ticket.models import ClusterOperateRecord
from backend.utils.time import datetime2str


class ListRetrieveResource(query.ListRetrieveResource):
    """查看 mysql 单点部署的资源"""

    cluster_type = ClusterType.TenDBSingle

    fields = [
        {"name": _("集群名"), "key": "cluster_name"},
        {"name": _("主域名"), "key": "master_domain"},
        {"name": _("实例"), "key": "masters"},
        {"name": _("所属db模块"), "key": "db_module_name"},
        {"name": _("创建人"), "key": "creator"},
        {"name": _("创建时间"), "key": "create_at"},
    ]

    @classmethod
    def list_clusters(cls, bk_biz_id: int, query_params: Dict, limit: int, offset: int) -> query.ResourceList:
        """查询集群信息

        :param bk_biz_id: 业务 ID
        :param query_params: 查询条件. 通过 .serializers.ListResourceSLZ 完成数据校验
        :param limit: 分页查询, 每页展示的数目
        :param offset: 分页查询, 当前页的偏移数
        """
        query_filters = Q(bk_biz_id=bk_biz_id, cluster_type=cls.cluster_type)

        if query_params.get("db_module_id"):
            query_filters &= Q(db_module_id=query_params["db_module_id"])

        cluster_query = copy.deepcopy(query_filters)
        storage_query = copy.deepcopy(query_filters)

        if query_params.get("domain"):
            cluster_query &= Q(immute_domain__icontains=query_params["domain"])

        if query_params.get("cluster_ids"):
            cluster_query &= Q(id__in=query_params["cluster_ids"])

        if query_params.get("creator"):
            cluster_query &= Q(creator__icontains=query_params["creator"])

        # 查询条件不包含 IP
        if query_params.get("ip"):
            filter_ip = query_params.get("ip").split(",")
            storage_query &= Q(machine__ip__in=filter_ip)

        storage_inst_qset = StorageInstance.objects.filter(storage_query)
        if query_params.get("ip"):
            cluster_query &= Q(storageinstance__in=storage_inst_qset)

        cluster_qset = Cluster.objects.filter(cluster_query)

        db_module_names = {
            module.db_module_id: module.db_module_name
            for module in DBModule.objects.filter(bk_biz_id=bk_biz_id, cluster_type=cls.cluster_type)
        }

        return cls._list(cluster_qset, storage_inst_qset, db_module_names, limit, offset)

    @classmethod
    def list_instances(cls, bk_biz_id: int, query_params: Dict, limit: int, offset: int) -> query.ResourceList:
        instance_filters = Q(bk_biz_id=bk_biz_id, cluster_type=cls.cluster_type)
        if query_params.get("ip"):
            instance_filters &= Q(machine__ip=query_params["ip"])

        if query_params.get("port"):
            instance_filters &= Q(port=query_params["port"])

        if query_params.get("domain"):
            instance_filters &= Q(cluster__immute_domain__icontains=query_params["domain"])

        if query_params.get("cluster_id"):
            instance_filters &= Q(cluster__id=query_params["cluster_id"])

        if query_params.get("role"):
            instance_filters &= Q(instance_inner_role=query_params["role"])

        if query_params.get("status"):
            instance_filters &= Q(status=query_params["status"])

        instances_qs = StorageInstance.objects.filter(instance_filters)
        instances = [cls._to_instance_representation(instance) for instance in instances_qs[offset : limit + offset]]

        # 补充实例的额外信息
        if query_params.get("extra"):
            instances_extra_info = InstanceHandler(bk_biz_id).check_instances(query_instances=instances)
            address__instance_extra_info = {inst["instance_address"]: inst for inst in instances_extra_info}
            for inst in instances:
                extra_info = address__instance_extra_info[inst["instance_address"]]
                inst.update(host_info=extra_info["host_info"], related_clusters=extra_info["related_clusters"])

        return query.ResourceList(count=instances_qs.count(), data=instances)

    @classmethod
    def get_topo_graph(cls, bk_biz_id: int, cluster_id: int) -> dict:
        cluster = Cluster.objects.get(bk_biz_id=bk_biz_id, id=cluster_id)
        graph = scan_cluster(cluster).to_dict()
        return graph

    @classmethod
    def retrieve_cluster(cls, bk_biz_id: int, cluster_id: int) -> dict:
        """获取单个集群详情"""
        cluster = Cluster.objects.get(id=cluster_id, bk_biz_id=bk_biz_id, cluster_type=cls.cluster_type)
        cluster.masters = cluster.storageinstance_set.filter(cluster_type=cls.cluster_type, bk_biz_id=bk_biz_id)

        db_module_names = {
            module.db_module_id: module.db_module_name
            for module in DBModule.objects.filter(db_module_id=cluster.db_module_id)
        }
        return cls._to_cluster_representation(cluster, db_module_names)

    @classmethod
    def _list(
        cls,
        cluster_qset: QuerySet,
        storage_inst_qset: QuerySet,
        db_module_names: Dict[int, str],
        limit: int,
        offset: int,
    ) -> query.ResourceList:
        count = cluster_qset.count()
        if count == 0:
            return query.ResourceList(count=0, data=[])

        cluster_qset = cluster_qset.order_by("-create_at")[offset : limit + offset].prefetch_related(
            Prefetch("storageinstance_set", queryset=storage_inst_qset, to_attr="masters")
        )

        clusters = []
        for cluster in cluster_qset:
            clusters.append(cls._to_cluster_representation(cluster, db_module_names))
        return query.ResourceList(count=count, data=clusters)

    @staticmethod
    def _to_cluster_representation(cluster: Cluster, db_module_names: Dict[int, str]) -> Dict[str, Any]:
        """
        将集群对象转为可序列化的 dict 结构

        :param cluster: model Cluster 对象, 增加了 masters 属性
        :param db_module_names: 字典类型, key 是 db_module_id, value 是 db_module_name
        """
        cloud_info = ResourceQueryHelper.search_cc_cloud(get_cache=True)
        return {
            "id": cluster.id,
            "phase": cluster.phase,
            "status": cluster.status,
            "operations": ClusterOperateRecord.objects.get_cluster_operations(cluster.id),
            "cluster_name": cluster.name,
            "cluster_type": cluster.cluster_type,
            "bk_biz_id": cluster.bk_biz_id,
            "bk_biz_name": AppCache.objects.get(bk_biz_id=cluster.bk_biz_id).bk_biz_name,
            "bk_cloud_id": cluster.bk_cloud_id,
            "bk_cloud_name": cloud_info[str(cluster.bk_cloud_id)]["bk_cloud_name"],
            "master_domain": cluster.immute_domain,
            "masters": [m.simple_desc for m in cluster.masters],
            "db_module_name": db_module_names.get(cluster.db_module_id, f"id: {cluster.db_module_id}"),
            "creator": cluster.creator,
            "create_at": datetime2str(cluster.create_at),
        }

    @classmethod
    def _to_instance_representation(cls, instance: StorageInstance) -> Dict[str, Any]:
        """
        将实例对象转为可序列化的 dict 结构

        :param instance: model StorageInstance 对象
        """
        cluster = instance.cluster.first()
        cloud_info = ResourceQueryHelper.search_cc_cloud(get_cache=True)
        return {
            "cluster_id": cluster.id,
            "cluster_name": cluster.name,
            "cluster_type": cluster.cluster_type,
            "db_module_id": cluster.db_module_id,
            "bk_cloud_id": instance.machine.bk_cloud_id,
            "bk_cloud_name": cloud_info[str(instance.machine.bk_cloud_id)]["bk_cloud_name"],
            "ip": instance.machine.ip,
            "port": instance.port,
            "instance_address": instance.ip_port,
            "bk_host_id": instance.machine.bk_host_id,
            "role": instance.instance_inner_role,
            "master_domain": instance.bind_entry.first().entry,
            "status": instance.status,
            "spec_config": instance.machine.spec_config,
            "create_at": datetime2str(instance.create_at),
        }
