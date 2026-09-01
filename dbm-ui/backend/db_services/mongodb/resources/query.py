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
import logging
import re
from typing import Any, Callable, Dict, List, Tuple

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import (
    Case,
    CharField,
    ExpressionWrapper,
    F,
    IntegerField,
    Min,
    Prefetch,
    Q,
    QuerySet,
    Value,
    When,
)
from django.db.models.functions import Coalesce, Concat
from django.utils.translation import gettext_lazy as _

from backend.db_meta.enums import ClusterEntryType, ClusterType, InstanceRole, MachineType, MachineTypeInstanceRoleMap
from backend.db_meta.models import (
    AppCache,
    ClusterEntry,
    Machine,
    MongoDBStorageInstanceExt,
    NosqlStorageSetDtl,
    StorageInstanceTuple,
)
from backend.db_meta.models.cluster import Cluster
from backend.db_meta.models.instance import ProxyInstance, StorageInstance
from backend.db_services.dbbase.resources import query
from backend.db_services.dbbase.resources.query import (
    CommonExportQueryResourceMixin,
    CommonQueryResourceMixin,
    ResourceList,
)
from backend.db_services.dbbase.resources.query_base import build_empty_and_in_q, build_q_for_domain_by_mongo_instance
from backend.db_services.dbbase.resources.register import register_resource_decorator
from backend.db_services.dbresource.handlers import MongoDBShardSpecFilter
from backend.db_services.ipchooser.handlers.host_handler import HostHandler
from backend.flow.utils.mongodb.version_utils import get_cluster_live_instance_version
from backend.ticket.constants import TicketType
from backend.ticket.models import InstanceOperateRecord
from backend.utils.time import datetime2str

logger = logging.getLogger("root")

# 集群列表/详情节点展示顺序：m1 → m2…m10 → backup（与 MachineTypeInstanceRoleMap 一致）
_MONGO_DISPLAY_ROLE_ORDER = [role.value for role in MachineTypeInstanceRoleMap[MachineType.MONGODB]]
_MONGO_DISPLAY_ROLE_INDEX = {role: idx for idx, role in enumerate(_MONGO_DISPLAY_ROLE_ORDER)}

# 实例/主机列表机型顺序：mongos → config → mongodb
_MONGO_MACHINE_TYPE_ORDER = [
    MachineType.MONGOS.value,
    MachineType.MONOG_CONFIG.value,
    MachineType.MONGODB.value,
]
# 默认排序字段（未传 ordering 时）：集群 → 机型 → 分片 → 角色 → IP → 端口
_MONGO_INSTANCE_DEFAULT_ORDER = (
    "cluster__id",
    "_machine_type_order",
    "shard",
    "_role_order",
    "machine__ip",
    "port",
)
_MONGO_MACHINE_DEFAULT_ORDER = ("_machine_type_order", "_role_order", "ip", "bk_host_id")


def mongo_shard_name_sort_key(shard_name: str):
    """分片名按尾号自然序（s1 < s2 < s10），避免字典序 s1、s10、s11…"""
    match = re.search(r"(\d+)$", shard_name or "")
    if match:
        return (0, int(match.group(1)), shard_name or "")
    return (1, 0, shard_name or "")


def _mongo_machine_type_order_case(field_name: str = "machine_type") -> Case:
    return Case(
        *[When(**{field_name: mt}, then=Value(idx)) for idx, mt in enumerate(_MONGO_MACHINE_TYPE_ORDER)],
        default=Value(9),
        output_field=IntegerField(),
    )


def _mongo_role_order_case(field_name: str = "instance_role") -> Case:
    return Case(
        *[When(**{field_name: role}, then=Value(idx)) for idx, role in enumerate(_MONGO_DISPLAY_ROLE_ORDER)],
        default=Value(999),
        output_field=IntegerField(),
    )


class MongoDBExportQueryResourceMixin(CommonExportQueryResourceMixin):
    """补充MongoDB集群列表导出所需的header及数据"""

    @staticmethod
    def fill_instances_to_cluster_info(cluster_info: Dict, instance_queryset: QuerySet, role_header_ids):
        """
        将实例信息填充到集群信息中
        """

        instances = instance_queryset.all()
        if not instances.exists():
            return

        for ins in instances:
            if ins.machine.machine_type in [MachineType.MONOG_CONFIG, MachineType.MONGOS, MachineType.MONGODB]:
                role = ins.machine.machine_type
            else:
                role = ins.instance_role

            # 添加实例信息
            if role in cluster_info:
                cluster_info[role] += f"\n{ins.machine.ip}:{ins.port}"
            else:
                role_header_ids.add(role)
                cluster_info[role] = f"{ins.machine.ip}:{ins.port}"

    @classmethod
    def update_headers(cls, headers, **kwargs):
        extra_headers = [
            {"id": "clb", "name": _("clb")},
            {"id": "mongo_config", "name": _("ConfigSvr")},
            {"id": "mongos", "name": _("Mongos")},
            {"id": "mongodb", "name": _("ShardSvr")},
        ]

        # 去除从域名/模块字段
        for header in headers:
            if header["id"] in ["slave_domain", "db_module_name"]:
                headers.remove(header)

        return headers, extra_headers

    @classmethod
    def update_cluster_info(cls, cluster, cluster_info, **kwargs):
        """
        补充额外的集群列表数据
        """

        # 补充clb
        clb_entry, _ = CommonQueryResourceMixin.get_cluster_clb_polaris_entries(cluster)
        cluster_info.update(
            {
                "clb": clb_entry,
            }
        )

        # 删除cluster_info中的从域名/模块字段值
        del cluster_info["slave_domain"], cluster_info["db_module_name"]

        return cluster_info

    @classmethod
    def update_instance_ext_info(cls, resource_list):
        """
        补充副本集状态数据
        """
        instance_ids = [item["id"] for item in resource_list.data]

        if not instance_ids:
            return resource_list

        ext_instances = MongoDBStorageInstanceExt.objects.filter(instance_id__in=instance_ids).values(
            "instance_id", "state"
        )

        ext_dict = {ext["instance_id"]: ext["state"] for ext in ext_instances}

        for item in resource_list.data:
            item["mongodb_state"] = ext_dict.get(item["id"], None)

        return resource_list


@register_resource_decorator()
class MongoDBListRetrieveResource(query.ListRetrieveResource, MongoDBExportQueryResourceMixin):
    """查看 mysql dbha 架构的资源"""

    cluster_types = [ClusterType.MongoReplicaSet, ClusterType.MongoShardedCluster]
    storage_spec_role = InstanceRole.MONGO_M1
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
            "domains": Q(immute_domain__in=query_params.get("domains", "").split(",")),
        }
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
        """
        为查询的集群填充额外信息
        @param bk_biz_id: 业务ID
        @param cluster_queryset: 过滤集群查询集
        @param proxy_queryset: 过滤的proxy查询集
        @param storage_queryset: 过滤的storage查询集
        @param limit: 分页限制
        @param offset: 分页起始
        """
        # 预取运行时状态，供列表/详情节点字段 mongodb_state 使用
        storage_queryset = storage_queryset.select_related("mongodbstorageinstanceext")
        storage_instance_queryset = StorageInstance.objects.prefetch_related(
            Prefetch(
                "as_ejector",
                queryset=StorageInstanceTuple.objects.select_related("receiver", "receiver__machine").filter(
                    ejector__in=storage_queryset.values_list("id", flat=True)
                ),
                to_attr="instance_tuples",
            )
        )
        cluster_queryset = cluster_queryset.prefetch_related(
            Prefetch(
                "storageinstance_set",
                queryset=storage_instance_queryset.select_related("machine", "mongodbstorageinstanceext"),
                to_attr="storage_instances",
            ),
            Prefetch(
                "nosqlstoragesetdtl_set",
                queryset=NosqlStorageSetDtl.objects.select_related("instance", "instance__machine"),
                to_attr="storage_set_dtl",
            ),
        )

        return super()._filter_cluster_hook(
            bk_biz_id,
            cluster_queryset,
            proxy_queryset,
            storage_queryset,
            limit,
            offset,
            **kwargs,
        )

    @staticmethod
    def _get_storage_mongodb_state(storage: StorageInstance):
        """读取巡检写入的运行时状态；无扩展记录时返回 None"""
        try:
            return storage.mongodbstorageinstanceext.state
        except ObjectDoesNotExist:
            return None

    @classmethod
    def _to_mongo_storage_node_desc(cls, storage: StorageInstance, seg_range: str = "", with_seg_range: bool = False):
        """storage 节点描述：simple_desc + 元数据角色 + 运行时状态（可选分片名）"""
        desc = {
            **storage.simple_desc,
            "instance_role": storage.instance_role,
            "mongodb_state": cls._get_storage_mongodb_state(storage),
        }
        if with_seg_range and seg_range:
            desc["seg_range"] = seg_range
        return desc

    @classmethod
    def _sort_mongo_storages(cls, storages: List[StorageInstance], ip_port_to_seg: Dict[str, str]):
        """按分片名（自然序）→ 角色(m1…backup) → ip → port 排序"""

        def sort_key(storage: StorageInstance):
            ip_port = f"{storage.machine.ip}:{storage.port}"
            seg = ip_port_to_seg.get(ip_port, "")
            role_idx = _MONGO_DISPLAY_ROLE_INDEX.get(storage.instance_role, 999)
            return (mongo_shard_name_sort_key(seg), role_idx, storage.machine.ip, storage.port)

        return sorted(storages, key=sort_key)

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
        cluster_zone_map: Dict[str, str],
        dns_to_clb: bool = False,
        **kwargs,
    ) -> Dict[str, Any]:
        """将集群对象转为可序列化的 dict 结构"""
        mongodb_insts = [m for m in cluster.storages if m.machine.machine_type == MachineType.MONGODB]
        mongo_config_insts = [m for m in cluster.storages if m.machine.machine_type == MachineType.MONOG_CONFIG]

        machine_list = [
            (storage_set_dtl.seg_range, f"{storage_set_dtl.instance.machine.ip}:{storage_set_dtl.instance.port}")
            for storage_set_dtl in cluster.storage_set_dtl
        ]

        machine_map = {}
        for group_name, machine_ip_port in machine_list:
            if not machine_map.get(group_name):
                machine_map[group_name] = [machine_ip_port]
            else:
                machine_map[group_name].append(machine_ip_port)

        master_slave_map = {}
        for instance in cluster.storage_instances:
            for instance_tuple in instance.instance_tuples:
                key = f"{instance.machine.ip}:{instance.port}"
                item = f"{instance_tuple.receiver.machine.ip}:{instance_tuple.receiver.port}"
                if not master_slave_map.get(key):
                    master_slave_map[key] = [item]
                else:
                    master_slave_map[key].append(item)

        for k, v in master_slave_map.items():
            for group_name, ip_port_list in machine_map.items():
                if k in ip_port_list:
                    machine_map[group_name].extend(v)

        # ip:port → seg_range，用于 ShardSvr 排序与字段
        ip_port_to_seg: Dict[str, str] = {}
        for group_name, ip_port_list in machine_map.items():
            for ip_port in ip_port_list:
                ip_port_to_seg[ip_port] = group_name

        is_sharded = cluster.cluster_type == ClusterType.MongoShardedCluster
        mongodb_insts = cls._sort_mongo_storages(mongodb_insts, ip_port_to_seg)
        mongo_config_insts = cls._sort_mongo_storages(mongo_config_insts, {})

        mongodb = [
            cls._to_mongo_storage_node_desc(
                m,
                seg_range=ip_port_to_seg.get(f"{m.machine.ip}:{m.port}", ""),
                with_seg_range=is_sharded,
            )
            for m in mongodb_insts
        ]
        mongo_config = [cls._to_mongo_storage_node_desc(m) for m in mongo_config_insts]
        mongos = sorted(
            [
                {
                    **m.simple_desc,
                    "bk_sub_zone_id": m.machine.bk_sub_zone_id,
                    "bk_sub_zone": m.machine.bk_sub_zone,
                    "bk_city": cluster.region,
                }
                for m in cluster.proxies
            ],
            key=lambda node: (node["ip"], node["port"]),
        )

        # 获取mongodb的分片数和单分片实例数
        if cluster.cluster_type == ClusterType.MongoReplicaSet:
            shard_node_count, shard_num = len(mongodb), 1
        else:
            shard_num = cluster.nosqlstoragesetdtl_set.filter(
                instance__machine__machine_type=MachineType.MONGODB
            ).count()
            shard_node_count = len(mongodb) / shard_num

        # 获取单机部署实例数、mongodb总机器数量、机器组数
        machine_instance_num = mongodb_insts[0].machine.storageinstance_set.count()
        mongodb_machine_num = len(set([m.machine.bk_host_id for m in mongodb_insts]))
        mongodb_machine_pair = mongodb_machine_num // shard_node_count

        # 获取单机分片数
        single_host_shard_num = shard_num / mongodb_machine_pair

        # 获取shard分片规格（历史机器可能缺 storage_spec，兜底为空列表）
        mongodb_spec = dict(mongodb_insts[0].machine.spec_config or {})
        mount_point__size = {
            disk["mount_point"]: disk["min"] if "min" in disk else disk.get("size")
            for disk in (mongodb_spec.get("storage_spec") or [])
            if disk.get("mount_point")
        }
        data_size = mount_point__size.get("/data1") or (mount_point__size.get("/data") or 0) / 2
        mongodb_spec.update(
            capacity=data_size,
            machine_pair=mongodb_machine_pair,
        )
        shard_spec = MongoDBShardSpecFilter.get_shard_spec(mongodb_spec, shard_num)

        cluster_extra_info = {
            "machine_instance_num": machine_instance_num,
            "mongodb_machine_pair": mongodb_machine_pair,
            "mongodb_machine_num": mongodb_machine_num,
            "shard_spec": shard_spec,
            "seg_range": machine_map,
            "mongos": mongos,
            "mongodb": mongodb,
            "mongo_config": mongo_config,
            "shard_num": shard_num,  # 集群分片数
            "shard_node_count": shard_node_count,  # 每分片节点数
            "single_host_shard_num": single_host_shard_num,  # 获取单机分片数
            "temporary_info": cls.get_temporary_cluster_info(cluster, [TicketType.MONGODB_PITR_RESTORE]),
            "disaster_tolerance_level": cluster.disaster_tolerance_level,
            "instance_version": get_cluster_live_instance_version(cluster) or cluster.major_version,
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
            cluster_zone_map,
            dns_to_clb,
            **kwargs,
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
        resource_list = super()._list_instances(bk_biz_id, query_params, limit, offset, filter_params_map, **kwargs)
        return super().update_instance_ext_info(resource_list)

    @classmethod
    def _mongo_instance_order_by(cls, query_params: Dict[str, str]) -> Tuple[str, ...]:
        """实例列表排序：显式 ordering 优先，否则按机型/分片/角色稳定排序"""
        ordering = (query_params.get("ordering") or "").strip()
        if ordering:
            return tuple(part.strip() for part in ordering.split(",") if part.strip())
        return _MONGO_INSTANCE_DEFAULT_ORDER

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
            "bk_biz_id",
            "cluster__id",
            "version",
            "cluster__cluster_type",
            "cluster__db_module_id",
            "cluster__name",
            "machine__ip",
            "machine__bk_cloud_id",
            "machine__bk_host_id",
            "machine__machine_type",
            "machine__spec_config",
            "machine__bk_sub_zone",
            "machine__bk_sub_zone_id",
            "machine__bk_os_name",
            "machine__bk_rack_id",
            "machine__bk_svr_device_cls_name",
            "shard",
            "bind_entry__entry",
            "_machine_type_order",
            "_role_order",
        ]
        order_by = cls._mongo_instance_order_by(query_params)

        # 过滤实例域名
        if "domain" in query_params:
            query_filters &= build_q_for_domain_by_mongo_instance(query_params)

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
                _machine_type_order=_mongo_machine_type_order_case("machine__machine_type"),
                _role_order=_mongo_role_order_case("instance_role"),
            )
            .select_related("machine")
            .prefetch_related(
                "cluster", "as_receiver__ejector__nosqlstoragesetdtl", "as_ejector__ejector__nosqlstoragesetdtl"
            )
            .filter(query_filters)
        )
        if query_params.get("shard"):
            return (
                storage_instance.filter(shard__in=query_params["shard"].split(","))
                .distinct()
                .values(*fields)
                .order_by(*order_by)
            )

        mongodb_state = query_params.get("mongodb_state", "")
        if mongodb_state:
            # 根据副本集状态字段过滤（需在 values 前过滤）
            mongo_state_filters = (build_empty_and_in_q("mongodbstorageinstanceext__state", mongodb_state),)
            return storage_instance.filter(*mongo_state_filters).distinct().values(*fields).order_by(*order_by)

        storage_instance = storage_instance.values(*fields)
        proxy_instance = (
            ProxyInstance.objects.annotate(
                role=F("access_layer"),
                shard=Value(""),
                _machine_type_order=_mongo_machine_type_order_case("machine__machine_type"),
                _role_order=Value(0, output_field=IntegerField()),
            )
            .select_related("machine")
            .prefetch_related("cluster")
            .filter(query_filters & Q(bind_entry__cluster_entry_type=ClusterEntryType.DNS.value))  # 过滤实例域名
            .values(*fields)
        )

        return storage_instance.union(proxy_instance).order_by(*order_by)

    @classmethod
    def _filter_machine_hook(
        cls,
        bk_biz_id,
        machine_queryset: QuerySet,
        limit: int,
        offset: int,
        **kwargs,
    ) -> ResourceList:
        """主机列表按机型 → 角色(m1…backup) → IP 排序（替代默认 -create_at）"""
        machine_queryset = machine_queryset.annotate(
            _machine_type_order=_mongo_machine_type_order_case("machine_type"),
            _role_order=Coalesce(
                Min(_mongo_role_order_case("storageinstance__instance_role")),
                Case(
                    When(machine_type=MachineType.MONGOS.value, then=Value(0)),
                    default=Value(999),
                    output_field=IntegerField(),
                ),
            ),
        ).order_by(*_MONGO_MACHINE_DEFAULT_ORDER)

        count = machine_queryset.count()
        limit = count if limit == -1 else limit
        if count == 0:
            return ResourceList(count=0, data=[])

        machine_queryset = machine_queryset[offset : limit + offset].prefetch_related(
            "storageinstance_set__cluster", "proxyinstance_set__cluster"
        )

        bk_host_ids = list(machine_queryset.values_list("bk_host_id", flat=True))
        host_id_info_map = {host["host_id"]: host for host in HostHandler.check([], [], [], bk_host_ids)}

        machine_infos: List[Dict[str, Any]] = []
        for machine in machine_queryset:
            machine_infos.append(cls._to_machine_representation(machine, host_id_info_map, **kwargs))

        return ResourceList(count=count, data=machine_infos)

    @classmethod
    def _get_machine_extra_info(cls, machine: Machine) -> dict:
        """关联实例按角色排序，instance_role 取排序后首个"""
        storages = list(machine.storageinstance_set.all())
        proxies = list(machine.proxyinstance_set.all())

        if storages:
            sorted_storages = cls._sort_mongo_storages(storages, {})
            instances = [inst.simple_desc for inst in sorted_storages]
            instance_role = sorted_storages[0].instance_role
        elif proxies:
            sorted_proxies = sorted(proxies, key=lambda inst: (inst.machine.ip, inst.port))
            instances = [inst.simple_desc for inst in sorted_proxies]
            instance_role = sorted_proxies[0].access_layer
        else:
            instances, instance_role = [], ""

        related_clusters_map: Dict[int, List[Dict]] = {}
        for inst in [*storages, *proxies]:
            cluster = inst.cluster.first()
            if cluster:
                related_clusters_map[cluster.id] = cluster.to_dict()

        return {
            "instance_role": instance_role,
            "related_instances": instances,
            "related_clusters": related_clusters_map.values(),
        }

    @classmethod
    def _filter_instance_hook(cls, bk_biz_id, query_params, instances, **kwargs):
        instance_ids = [f"{instance['machine__bk_host_id']}:{instance['port']}" for instance in instances]
        instance_operator_record_map = InstanceOperateRecord.get_instance_records_map(instance_ids)
        return super()._filter_instance_hook(
            bk_biz_id, query_params, instances, instance_operator_record_map=instance_operator_record_map, **kwargs
        )

    @classmethod
    def _to_instance_representation(
        cls, instance: dict, cluster_entry_map: dict, db_module_names_map: dict, **kwargs
    ) -> Dict[str, Any]:
        """获取mongo实例信息"""
        bk_host_id, port = instance["machine__bk_host_id"], instance["port"]
        instance_operator_record_map = kwargs["instance_operator_record_map"]
        instance_extra_info = {
            "shard": instance["shard"],
            "operations": instance_operator_record_map.get(f"{bk_host_id}:{port}", []),
            "instance_domain": instance["bind_entry__entry"] if instance["bind_entry__entry"] else "",
        }
        instance_info = super()._to_instance_representation(instance, cluster_entry_map, db_module_names_map, **kwargs)
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
                try:
                    # 找到primary节点
                    ejector: StorageInstance = (storage.as_ejector.all() or storage.as_receiver.all()).first().ejector
                    # 通过primary节点找到关联的NosqlStorageSetDtl表，从而获取该实例的分片
                    shard = ejector.nosqlstoragesetdtl_set.first().seg_range
                    storage_id__shard[storage.id] = shard
                except Exception as e:  # pylint: disable=broad-except
                    logger.error("query mongo storage shard error: %s", e)
                    storage_id__shard[storage.id] = ""

        return storage_instance, storage_id__shard

    @staticmethod
    def common_query_instance(bk_biz_id: int, cluster_types: list, bk_host_ids: list) -> Tuple[List[Dict], List[Dict]]:

        query_condition = Q(bk_biz_id=bk_biz_id, cluster_type__in=cluster_types)
        if bk_host_ids:
            query_condition = query_condition & Q(machine__bk_host_id__in=bk_host_ids)
        fields = [
            "id",
            "role",
            "port",
            "status",
            "create_at",
            "shard",
            "cluster__id",
            "version",
            "cluster__name",
            "machine__ip",
            "machine__bk_sub_zone",
            "machine__bk_os_name",
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
            .filter(query_condition)
            .values(*fields)
        )
        proxy_instance = (
            ProxyInstance.objects.annotate(role=F("access_layer"), shard=Value(""))
            .select_related("machine")
            .prefetch_related("cluster")
            .filter(query_condition & Q(bind_entry__cluster_entry_type=ClusterEntryType.DNS.value))  # 过滤实例域名
            .values(*fields)
        )
        instances = storage_instance.union(proxy_instance)

        headers = [
            {"id": "ip_port", "name": _("实例")},
            {"id": "instance_id", "name": _("ID")},
            {"id": "cluster_name", "name": _("所属集群")},
            {"id": "shard", "name": _("分片名")},
            {"id": "status", "name": _("状态")},
            {"id": "instance_role", "name": _("部署角色")},
            {"id": "version", "name": _("版本")},
            {"id": "master_domain", "name": _("域名")},
            {"id": "ip", "name": _("IP")},
            {"id": "bk_sub_zone", "name": _("园区")},
            {"id": "bk_os_name", "name": _("操作系统")},
            {"id": "create_at", "name": _("部署时间")},
        ]
        # 插入数据
        data_list = []

        cluster_ids = [instance["cluster__id"] for instance in instances]
        # 查询访问入口
        cluster_entry_map = ClusterEntry.get_cluster_entry_map(cluster_ids)

        for ins in instances:
            data_list.append(
                {
                    "ip_port": f"{ins['machine__ip']}:{ins['port']}",
                    "instance_id": ins["id"],
                    "cluster_name": ins["cluster__name"],
                    "shard": ins["shard"],
                    "status": ins["status"],
                    "instance_role": ins["role"],
                    "version": ins["version"],
                    "master_domain": cluster_entry_map.get(ins["cluster__id"], {}).get("master_domain", ""),
                    "ip": ins["machine__ip"],
                    "bk_sub_zone": ins["machine__bk_sub_zone"],
                    "bk_os_name": ins["machine__bk_os_name"],
                    "create_at": datetime2str(ins["create_at"]),
                }
            )

        return headers, data_list
