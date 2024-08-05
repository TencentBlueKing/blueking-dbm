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

from django.db.models import F, Q, QuerySet, Value
from django.forms import model_to_dict
from django.utils.translation import ugettext_lazy as _

from backend.configuration.constants import DBType
from backend.db_meta.api.cluster.tendbcluster.detail import scan_cluster
from backend.db_meta.enums import InstanceInnerRole, TenDBClusterSpiderRole
from backend.db_meta.enums.cluster_type import ClusterType
from backend.db_meta.exceptions import DBMetaException
from backend.db_meta.models import AppCache, Spec
from backend.db_meta.models.cluster import Cluster
from backend.db_meta.models.instance import ProxyInstance, StorageInstance
from backend.db_services.dbbase.resources import query
from backend.db_services.dbbase.resources.query import ResourceList
from backend.db_services.dbbase.resources.register import register_resource_decorator
from backend.ticket.constants import TicketType


@register_resource_decorator()
class ListRetrieveResource(query.ListRetrieveResource):
    """查看 mysql dbha 架构的资源"""

    cluster_type = ClusterType.TenDBCluster
    cluster_types = [ClusterType.TenDBCluster]

    fields = [
        {"name": _("集群名"), "key": "cluster_name"},
        {"name": _("主域名"), "key": "master_domain"},
        {"name": _("从域名"), "key": "slave_domain"},
        {"name": "Spider Master", "key": "spider_master"},
        {"name": "Spider Slave", "key": "spider_slave"},
        {"name": "Remote DB", "key": "remote_db"},
        {"name": "Remote DR", "key": "remote_dr"},
        {"name": _("运维节点"), "key": "spider_mnt"},
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
        return super()._list_clusters(
            bk_biz_id, query_params, limit, offset, filter_params_map, filter_func_map, **kwargs
        )

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
        storage_queryset = storage_queryset.prefetch_related(
            "as_ejector__tendbclusterstorageset", "as_receiver__tendbclusterstorageset"
        )
        proxy_queryset = proxy_queryset.prefetch_related("tendbclusterspiderext")
        # 预取remote的spec
        remote_spec_map = {
            spec.spec_id: spec for spec in Spec.objects.filter(spec_cluster_type=ClusterType.TenDBCluster)
        }
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

        def get_remote_infos(insts: List[StorageInstance]):
            """获取remote信息，并补充分片信息"""
            remote_infos = {InstanceInnerRole.MASTER.value: [], InstanceInnerRole.SLAVE.value: []}
            for inst in insts:
                try:
                    related = "as_ejector" if inst.instance_inner_role == InstanceInnerRole.MASTER else "as_receiver"
                    shard_id = getattr(inst, related).all()[0].tendbclusterstorageset.shard_id
                except Exception:
                    # 如果无法找到shard_id，则默认为-1。有可能实例处于restoring状态(比如集群容量变更时)
                    shard_id = -1

                remote_infos[inst.instance_inner_role].append({**inst.simple_desc, "shard_id": shard_id})

            remote_infos[InstanceInnerRole.MASTER.value].sort(key=lambda x: x.get("shard_id", -1))
            remote_infos[InstanceInnerRole.SLAVE.value].sort(key=lambda x: x.get("shard_id", -1))
            return remote_infos[InstanceInnerRole.MASTER.value], remote_infos[InstanceInnerRole.SLAVE.value]

        # 获取spider，remote角色实例信息
        spider = {
            role: [inst.simple_desc for inst in cluster.proxies if inst.tendbclusterspiderext.spider_role == role]
            for role in TenDBClusterSpiderRole.get_values()
        }
        remote_db, remote_dr = get_remote_infos(cluster.storages)
        # 计算machine分组
        machine_list = list(set([inst["bk_host_id"] for inst in [*remote_db, *remote_dr]]))
        machine_pair_cnt = len(machine_list) / 2
        # 获取集群规格
        spec_id = cluster.storages[0].machine.spec_id
        spec = kwargs["remote_spec_map"].get(spec_id)

        cluster_extra_info = {
            "cluster_spec": model_to_dict(spec) if spec else None,
            "cluster_capacity": spec.capacity * machine_pair_cnt if spec else None,
            "spider_master": spider[TenDBClusterSpiderRole.SPIDER_MASTER],
            "spider_slave": spider[TenDBClusterSpiderRole.SPIDER_SLAVE],
            "spider_mnt": spider[TenDBClusterSpiderRole.SPIDER_MNT],
            "cluster_shard_num": len(remote_db),
            "remote_shard_num": len(remote_db) / machine_pair_cnt,
            "machine_pair_cnt": machine_pair_cnt,
            "remote_db": remote_db,
            "remote_dr": remote_dr,
            "temporary_info": cls.get_temporary_cluster_info(cluster, TicketType.TENDBCLUSTER_ROLLBACK_CLUSTER),
        }
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
        cluster_info.update(cluster_extra_info)
        return cluster_info

    @classmethod
    def _retrieve_cluster(cls, cluster_details: dict, cluster_id: int) -> dict:
        """补充集群详情信息，子类可继承实现"""
        cluster = Cluster.objects.get(id=cluster_id)
        cluster_details["cluster_entry_details"] = cls.query_cluster_entry_details(cluster_details)

        try:
            cluster_details["spider_ctl_primary"] = cluster.tendbcluster_ctl_primary_address()
        except DBMetaException:
            cluster_details["spider_ctl_primary"] = ""

        return cluster_details

    @classmethod
    def _filter_instance_qs(cls, query_filters, query_params):
        fields = [
            "id",
            "cluster__id",
            "cluster__major_version",
            "cluster__cluster_type",
            "cluster__db_module_id",
            "cluster__name",
            "role",
            "inst_port",
            "status",
            "create_at",
            "machine__bk_host_id",
            "machine__spec_config",
            "machine__ip",
            "machine__bk_cloud_id",
            "machine__machine_type",
        ]

        # 获取remote实例的查询集
        remote_insts = (
            StorageInstance.objects.select_related("machine")
            .prefetch_related("cluster")
            .annotate(role=F("instance_role"), inst_port=F("port"))
            .filter(query_filters)
        )
        # 获取spider实例的查询集
        spider_insts = (
            ProxyInstance.objects.select_related("machine")
            .prefetch_related("cluster")
            .annotate(role=F("tendbclusterspiderext__spider_role"), inst_port=F("port"))
            .filter(query_filters)
        )
        # 涉及spider_controller的查询
        if query_params.get("spider_ctl"):
            # 额外获取spider master混部的中控节点的查询集 这里有一点: 通过value和annotate来将admin_port覆写port，达到过滤效果
            filter_spider_master = Q(tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_MASTER.value)
            controller_insts = (
                ProxyInstance.objects.select_related("machine")
                .prefetch_related("cluster")
                .values("admin_port")
                .annotate(port=F("admin_port"))
                .values(role=Value("spider_ctl"), inst_port=F("admin_port"))
                .filter(query_filters & filter_spider_master)
            )
            # ⚠️这里的union不要用链式union(eg: s1.union(s2).union(s3))，否则django解析sql语句会生成额外的扩号导致mysql语法错误。
            instances = remote_insts.union(spider_insts, controller_insts).values(*fields).order_by("-create_at")
        else:
            instances = remote_insts.union(spider_insts).values(*fields).order_by("-create_at")

        return instances

    @classmethod
    def _filter_instance_hook(cls, bk_biz_id, query_params, instances, **kwargs):
        # cluster handler
        kwargs.update(handler_db_type=DBType.MySQL.value)
        return super()._filter_instance_hook(bk_biz_id, query_params, instances, **kwargs)

    @classmethod
    def _to_instance_representation(
        cls, instance: dict, cluster_entry_map: dict, db_module_names_map: dict, **kwargs
    ) -> Dict[str, Any]:
        """
        将实例对象转为可序列化的 dict 结构
        @param instance: 实例信息
        @param cluster_entry_map: key 是 cluster.id, value 是当前集群对应的 entry 映射
        """
        instance["port"] = instance["inst_port"]
        return super()._to_instance_representation(instance, cluster_entry_map, db_module_names_map, **kwargs)

    @classmethod
    def _list_machines(
        cls,
        bk_biz_id: int,
        query_params: Dict,
        limit: int,
        offset: int,
        filter_params_map: Dict[str, Q] = None,
        **kwargs,
    ) -> ResourceList:
        filter_params_map = {
            "spider_role": Q(proxyinstance__tendbclusterspiderext__spider_role=query_params.get("spider_role"))
        }
        return super()._list_machines(bk_biz_id, query_params, limit, offset, filter_params_map, **kwargs)

    @classmethod
    def get_topo_graph(cls, bk_biz_id: int, cluster_id: int) -> dict:
        cluster = Cluster.objects.get(bk_biz_id=bk_biz_id, id=cluster_id)
        graph = scan_cluster(cluster).to_dict()
        return graph
