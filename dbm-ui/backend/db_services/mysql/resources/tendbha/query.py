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
from typing import Any, Callable, Dict, List

from django.db.models import F, Q, QuerySet
from django.forms import model_to_dict
from django.utils.translation import ugettext_lazy as _

from backend.db_meta.api.cluster.tendbha.detail import scan_cluster
from backend.db_meta.enums import ClusterEntryRole, InstanceInnerRole
from backend.db_meta.enums.cluster_type import ClusterType
from backend.db_meta.enums.spec import SpecClusterType
from backend.db_meta.models import AppCache, Spec, StorageInstance
from backend.db_meta.models.cluster import Cluster
from backend.db_services.dbbase.resources import query
from backend.db_services.dbbase.resources.query import ResourceList
from backend.db_services.dbbase.resources.query_base import build_q_for_domain_by_cluster
from backend.db_services.dbbase.resources.register import register_resource_decorator


@register_resource_decorator()
class ListRetrieveResource(query.ListRetrieveResource):
    """查看 mysql dbha 架构的资源"""

    cluster_types = [ClusterType.TenDBHA]

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
    def _list_clusters(
        cls,
        bk_biz_id: int,
        query_params: Dict,
        limit: int,
        offset: int,
        filter_params_map: Dict[str, Q] = None,
        filter_func_map: Dict[str, Callable] = None,
        **kwargs,
    ) -> ResourceList:
        """查询集群信息"""
        filter_params_map = {
            # 精确查询主从域名
            "master_domain": build_q_for_domain_by_cluster(
                domains=query_params.get("master_domain", "").split(","), role=ClusterEntryRole.MASTER_ENTRY
            ),
            "slave_domain": build_q_for_domain_by_cluster(
                domains=query_params.get("slave_domain", "").split(","), role=ClusterEntryRole.SLAVE_ENTRY
            ),
        }
        return super()._list_clusters(
            bk_biz_id, query_params, limit, offset, filter_params_map, filter_func_map, **kwargs
        )

    @classmethod
    def _list_instances(
        cls,
        bk_biz_id: int,
        query_params: Dict,
        limit: int,
        offset: int,
        filter_params_map: Dict[str, Q] = None,
        **kwargs,
    ) -> query.ResourceList:
        filter_params_map = filter_params_map or {}
        filter_params_map.update(role_exclude=(~Q(role=query_params.get("role_exclude"))))
        return super()._list_instances(bk_biz_id, query_params, limit, offset, filter_params_map)

    @classmethod
    def get_topo_graph(cls, bk_biz_id: int, cluster_id: int) -> dict:
        cluster = Cluster.objects.get(bk_biz_id=bk_biz_id, id=cluster_id)
        graph = scan_cluster(cluster).to_dict()
        return graph

    @classmethod
    def _filter_cluster_hook(
        cls,
        bk_biz_id,
        cluster_queryset: QuerySet,
        proxy_queryset: QuerySet,
        storage_queryset: QuerySet,
        limit: int,
        offset: int,
        **kwargs,
    ) -> ResourceList:
        # 提前预取storage的tuple
        storage_queryset = storage_queryset.prefetch_related("as_receiver__ejector")
        # 预取remote的spec
        remote_spec_map = {spec.spec_id: spec for spec in Spec.objects.filter(spec_cluster_type=SpecClusterType.MySQL)}
        return super()._filter_cluster_hook(
            bk_biz_id,
            cluster_queryset,
            proxy_queryset,
            storage_queryset,
            limit,
            offset,
            remote_spec_map=remote_spec_map,
            **kwargs,
        )

    @classmethod
    def _to_cluster_representation(
        cls,
        cluster: Cluster,
        cluster_entry: List[Dict[str, str]],
        db_module_names_map: Dict[int, str],
        cluster_entry_map: Dict[int, Dict[str, str]],
        cluster_operate_records_map: Dict[int, List],
        cloud_info: Dict[str, Any],
        biz_info: AppCache,
        cluster_stats_map: Dict[str, Dict[str, int]],
        **kwargs,
    ) -> Dict[str, Any]:
        """将集群对象转为可序列化的 dict 结构"""
        proxies = [m.simple_desc for m in cluster.proxies]
        masters = [m.simple_desc for m in cluster.storages if m.instance_inner_role == InstanceInnerRole.MASTER]
        # slave的对等点必须是master,此时slave要考虑repeater，对等点也是master
        slaves = [
            m.simple_desc
            for m in cluster.storages
            if m.instance_inner_role in [InstanceInnerRole.SLAVE, InstanceInnerRole.REPEATER]
            if len(m.as_receiver.all())
            and m.as_receiver.all()[0].ejector.instance_inner_role == InstanceInnerRole.MASTER
        ]

        cluster_role_info = {"proxies": proxies, "masters": masters, "slaves": slaves}

        # 补充cluster_spec参数
        master_storages = list(filter(lambda storage: storage.instance_inner_role == "master", cluster.storages))
        # 获取master规格
        if master_storages:
            spec_id = master_storages[0].machine.spec_id
            spec = kwargs["remote_spec_map"].get(spec_id)
        else:
            spec = None
        cluster_spec_info = {"cluster_spec": model_to_dict(spec) if spec else None}

        cluster_info = super()._to_cluster_representation(
            cluster,
            cluster_entry,
            db_module_names_map,
            cluster_entry_map,
            cluster_operate_records_map,
            cloud_info,
            biz_info,
            cluster_stats_map,
            **kwargs,
        )
        cluster_info.update(cluster_role_info)
        cluster_info.update(cluster_spec_info)
        return cluster_info

    @classmethod
    def _filter_instance_qs_hook(cls, storage_queryset, proxy_queryset, inst_fields, query_filters, query_params):
        # mysql的storage角色取instance_inner_role，需要重新根据query_filters获取queryset
        storage_queryset = (
            StorageInstance.objects.select_related("machine")
            .prefetch_related("cluster")
            .annotate(role=F("instance_inner_role"))
            .filter(query_filters)
        )
        instance_queryset = storage_queryset.union(proxy_queryset).values(*inst_fields).order_by("create_at")
        #  部署时间表头排序
        if query_params.get("ordering"):
            instance_queryset = instance_queryset.order_by(query_params.get("ordering"))
        return instance_queryset
