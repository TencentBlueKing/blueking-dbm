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

from django.db.models import CharField, ExpressionWrapper, F, Q, QuerySet, Value
from django.db.models.functions import Concat
from django.utils.translation import ugettext_lazy as _

from backend.db_meta.enums import ClusterType, MachineType
from backend.db_meta.models.cluster import Cluster
from backend.db_meta.models.instance import ProxyInstance, StorageInstance
from backend.db_services.dbbase.resources import query
from backend.db_services.dbbase.resources.query import ResourceList
from backend.db_services.dbbase.resources.register import register_resource_decorator
from backend.db_services.dbresource.handlers import MongoDBShardSpecFilter
from backend.ticket.constants import TicketType
from backend.ticket.models import InstanceOperateRecord


@register_resource_decorator()
class MongoDBListRetrieveResource(query.ListRetrieveResource):
    """查看 mysql dbha 架构的资源"""

    cluster_types = [ClusterType.MongoReplicaSet, ClusterType.MongoShardedCluster]
    fields = [
        {"name": _("主域名"), "key": "domain"},
        {"name": _("IP"), "key": "ip"},
        {"name": _("创建人"), "key": "creator"},
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
            "cluster_type": Q(cluster_type=query_params.get("cluster_type")),
            "domains": Q(immute_domain__in=query_params.get("domains", "").split(",")),
        }
        return super()._list_clusters(
            bk_biz_id, query_params, limit, offset, filter_params_map, filter_func_map, **kwargs
        )

    @classmethod
    def _to_cluster_representation(
        cls,
        cluster: Cluster,
        db_module_names_map: Dict[int, str],
        cluster_entry_map: Dict[int, Dict[str, str]],
        cluster_operate_records_map: Dict[int, List],
        **kwargs,
    ) -> Dict[str, Any]:
        """将集群对象转为可序列化的 dict 结构"""
        mongodb_insts = [m for m in cluster.storages if m.machine.machine_type == MachineType.MONGODB]

        # 获取mongos/mongodb/mongo_config的角色信息
        mongodb = [m.simple_desc for m in mongodb_insts]
        mongo_config = [m.simple_desc for m in cluster.storages if m.machine.machine_type == MachineType.MONOG_CONFIG]
        mongos = [
            {
                **m.simple_desc,
                "bk_sub_zone_id": m.machine.bk_sub_zone_id,
                "bk_sub_zone": m.machine.bk_sub_zone,
                "bk_city": cluster.region,
            }
            for m in cluster.proxies
        ]

        # 获取mongodb的分片数和单分片实例数
        if cluster.cluster_type == ClusterType.MongoReplicaSet:
            shard_node_count, shard_num = len(mongodb), 1
        else:
            shard_num = cluster.nosqlstoragesetdtl_set.filter(
                instance__machine__machine_type=MachineType.MONGODB
            ).count()
            shard_node_count = len(mongodb) / shard_num

        # 获取mongodb总机器数量、机器组数、单机部署实例数
        machine_instance_num = mongodb_insts[0].machine.storageinstance_set.count()
        mongodb_machine_num = len(set([m.machine.bk_host_id for m in mongodb_insts]))
        mongodb_machine_pair = mongodb_machine_num // shard_node_count

        # 获取shard分片规格
        mongodb_spec = mongodb_insts[0].machine.spec_config
        mount_point__size = {disk["mount_point"]: disk["size"] for disk in mongodb_spec["storage_spec"]}
        mongodb_spec.update(
            capacity=mount_point__size.get("/data1") or mount_point__size["/data"] / 2,
            machine_pair=mongodb_machine_pair,
        )
        shard_spec = MongoDBShardSpecFilter.get_shard_spec(mongodb_spec, shard_num)

        cluster_extra_info = {
            "machine_instance_num": machine_instance_num,
            "mongodb_machine_pair": mongodb_machine_pair,
            "mongodb_machine_num": mongodb_machine_num,
            "shard_spec": shard_spec,
            "mongos": mongos,
            "mongodb": mongodb,
            "mongo_config": mongo_config,
            "shard_num": shard_num,
            "shard_node_count": shard_node_count,
            "temporary_info": cls.get_temporary_cluster_info(cluster, TicketType.MONGODB_RESTORE),
            "disaster_tolerance_level": cluster.disaster_tolerance_level,
        }
        cluster_info = super()._to_cluster_representation(
            cluster, db_module_names_map, cluster_entry_map, cluster_operate_records_map, **kwargs
        )
        cluster_info.update(cluster_extra_info)
        return cluster_info

    @classmethod
    def _list_instances(
        cls,
        bk_biz_id: int,
        query_params: Dict,
        limit: int,
        offset: int,
        filter_params_map: Dict[str, Q] = None,
        **kwargs,
    ) -> ResourceList:
        """查询实例信息"""
        filter_params_map = {
            "cluster_type": Q(cluster_type=query_params.get("cluster_type")),
            "exact_ip": Q(machine__ip=query_params.get("exact_ip")),
        }
        return super()._list_instances(bk_biz_id, query_params, limit, offset, filter_params_map, **kwargs)

    @classmethod
    def _filter_instance_qs(cls, query_filters: Q, query_params: Dict[str, str]) -> QuerySet:
        """获取过滤的queryset"""
        fields = [
            "id",
            "role",
            "port",
            "status",
            "create_at",
            "shard",
            "cluster__id",
            "cluster__major_version",
            "cluster__cluster_type",
            "cluster__db_module_id",
            "cluster__name",
            "machine__ip",
            "machine__bk_cloud_id",
            "machine__bk_host_id",
            "machine__machine_type",
            "machine__spec_config",
            "shard",
        ]
        storage_instance = (
            StorageInstance.objects.annotate(
                role=F("instance_role"),
                shard=ExpressionWrapper(
                    Concat(
                        F("as_receiver__ejector__nosqlstoragesetdtl__seg_range"),
                        F("as_ejector__ejector__nosqlstoragesetdtl__seg_range"),
                    ),
                    output_field=CharField(),
                ),
            )
            .select_related("machine")
            .prefetch_related(
                "cluster", "as_receiver__ejector__nosqlstoragesetdtl", "as_ejector__ejector__nosqlstoragesetdtl"
            )
            .filter(query_filters)
            .values(*fields)
        )
        proxy_instance = (
            ProxyInstance.objects.annotate(role=F("access_layer"), shard=Value(""))
            .select_related("machine")
            .prefetch_related("cluster")
            .filter(query_filters)
            .values(*fields)
        )
        return storage_instance.union(proxy_instance)

    @classmethod
    def _filter_instance_hook(cls, bk_biz_id, query_params, instances, **kwargs):
        instance_ids = [f"{instance['machine__bk_host_id']}:{instance['port']}" for instance in instances]
        instance_operator_record_map = InstanceOperateRecord.get_instance_records_map(instance_ids)
        return super()._filter_instance_hook(
            bk_biz_id, query_params, instances, instance_operator_record_map=instance_operator_record_map, **kwargs
        )

    @classmethod
    def _to_instance_representation(cls, instance: dict, cluster_entry_map: dict, **kwargs) -> Dict[str, Any]:
        """获取mongo实例信息"""
        bk_host_id, port = instance["machine__bk_host_id"], instance["port"]
        instance_operator_record_map = kwargs["instance_operator_record_map"]
        instance_extra_info = {
            "shard": instance["shard"],
            "operations": instance_operator_record_map.get(f"{bk_host_id}:{port}", []),
        }
        instance_info = super()._to_instance_representation(instance, cluster_entry_map, **kwargs)
        instance_info.update(instance_extra_info)
        return instance_info

    @classmethod
    def get_topo_graph(cls, bk_biz_id: int, cluster_id: int) -> dict:
        from backend.db_meta.api.cluster.mongocluster import scan_cluster as mongo_shard_scan_cluster
        from backend.db_meta.api.cluster.mongorepset import scan_cluster as mongo_replicaset_scan_cluster

        cluster = Cluster.objects.get(bk_biz_id=bk_biz_id, id=cluster_id)
        if cluster.cluster_type == ClusterType.MongoReplicaSet:
            graph = mongo_replicaset_scan_cluster(cluster).to_dict()
        else:
            graph = mongo_shard_scan_cluster(cluster).to_dict()
        return graph

    @staticmethod
    def query_storage_shard(query_conditions):
        """查询mongodb的分片信息"""
        storage_id__shard: Dict[int, str] = {}
        storage_instance = (
            StorageInstance.objects.select_related("machine")
            .prefetch_related(
                # TODO: 为啥不能这样预取：as_receiver__ejector__nosqlstoragesetdtl?
                "cluster",
                "as_receiver__ejector",
                "as_ejector__ejector",
            )
            .filter(query_conditions)
        )
        for storage in storage_instance:
            if storage.cluster.first().cluster_type == ClusterType.MongoReplicaSet:
                # 副本集没有分片信息，返回空
                storage_id__shard[storage.id] = ""
            else:
                # 找到primary节点
                ejector: StorageInstance = (storage.as_ejector.all() or storage.as_receiver.all()).first().ejector
                # 通过primary节点找到关联的NosqlStorageSetDtl表，从而获取该实例的分片
                shard = ejector.nosqlstoragesetdtl_set.first().seg_range
                storage_id__shard[storage.id] = shard
        return storage_instance, storage_id__shard
