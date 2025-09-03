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

from django.db import connection
from django.db.models import Q, QuerySet
from django.forms import model_to_dict
from django.utils.translation import ugettext_lazy as _

from backend.configuration.constants import SystemSettingsEnum
from backend.configuration.models import SystemSettings
from backend.db_meta.api.cluster.rediscluster.handler import RedisClusterHandler
from backend.db_meta.api.cluster.redisinstance.handler import RedisInstanceHandler
from backend.db_meta.api.cluster.tendiscache.handler import TendisCacheClusterHandler
from backend.db_meta.api.cluster.tendispluscluster.handler import TendisPlusClusterHandler
from backend.db_meta.api.cluster.tendisssd.handler import TendisSSDClusterHandler
from backend.db_meta.enums import InstanceRole
from backend.db_meta.enums.cluster_type import ClusterType
from backend.db_meta.models import AppCache, Machine, NosqlStorageSetDtl, StorageInstance, StorageInstanceTuple
from backend.db_meta.models.cluster import Cluster
from backend.db_services.dbbase.resources import query
from backend.db_services.dbbase.resources.query import CommonQueryResourceMixin, ResourceList
from backend.db_services.dbbase.resources.register import register_resource_decorator
from backend.db_services.ipchooser.query.resource import ResourceQueryHelper
from backend.db_services.redis.redis_dts.util import get_redis_type_by_cluster_type
from backend.db_services.redis.redis_modules.models.redis_module_support import ClusterRedisModuleAssociate
from backend.db_services.redis.resources.constants import (
    REDIS_DELETE_RATE,
    REDIS_LIST_CLUSTER_TYPE,
    SQL_QUERY_MASTER_SLAVE_STATUS,
)
from backend.utils.basic import dictfetchall


@register_resource_decorator()
class RedisListRetrieveResource(query.ListRetrieveResource):
    """查看twemproxy-redis架构的资源"""

    cluster_types = REDIS_LIST_CLUSTER_TYPE

    handler_map = {
        ClusterType.TwemproxyTendisSSDInstance: TendisSSDClusterHandler,
        ClusterType.TendisTwemproxyRedisInstance: TendisCacheClusterHandler,
        ClusterType.TendisPredixyTendisplusCluster: TendisPlusClusterHandler,
        ClusterType.TendisPredixyRedisCluster: RedisClusterHandler,
        ClusterType.RedisInstance: RedisInstanceHandler,
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

    redis_cluster_module_map = {}

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
        return ResourceQueryHelper.search_cc_hosts(role_host_ids, keyword)

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

        seg_range_map, instance_tuple = seg_instance_info(bk_biz_id, storage_queryset)

        # 获取redis集群DB模块的映射信息
        cls.redis_cluster_module_map = {
            module["cluster_id"]: module["module_names"]
            for module in ClusterRedisModuleAssociate.objects.filter(cluster_id__in=cluster_queryset)
            .distinct()
            .values("cluster_id", "module_names")
        }
        # 获取redis集群删除率的配置
        delete_rate_configs = SystemSettings.get_setting_value(
            key=SystemSettingsEnum.REDIS_DELETE_RATE.value,
            default=REDIS_DELETE_RATE,
        )

        return super()._filter_cluster_hook(
            bk_biz_id,
            cluster_queryset,
            proxy_queryset,
            storage_queryset,
            limit,
            offset,
            seg_range_map=seg_range_map,
            instance_tuple=list(instance_tuple),
            delete_rate_configs=delete_rate_configs,
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
        dns_to_clb: bool = False,
        delete_rate_configs: dict = None,
        **kwargs,
    ) -> Dict[str, Any]:
        """集群序列化"""
        seg_range_map = kwargs["seg_range_map"]
        instance_tuple = kwargs["instance_tuple"]
        delete_rate_configs = delete_rate_configs or REDIS_DELETE_RATE
        # 填充分片信息
        machine_list, remote_infos = remote_tuple_info(
            seg_range_map, instance_tuple, cluster.cluster_type, cluster.storages
        )

        machine_list = list(set(machine_list))
        machine_pair_cnt = len(machine_list) / 2

        # 补充集群的规格和容量信息
        cluster_spec = cluster_capacity = ""
        remote_spec_map = kwargs["remote_spec_map"]
        if machine_list:
            spec_id = cluster.storages[0].machine.spec_id
            spec = remote_spec_map.get(spec_id)
            cluster_spec = model_to_dict(spec) if spec else {}
            cluster_capacity = spec.capacity * machine_pair_cnt if spec else 0

        # 集群额外信息
        cluster_extra_info = {
            "cluster_spec": cluster_spec,
            "cluster_capacity": cluster_capacity,
            "proxy": [m.simple_desc for m in cluster.proxies],
            "redis_master": remote_infos[InstanceRole.REDIS_MASTER.value],
            "redis_slave": remote_infos[InstanceRole.REDIS_SLAVE.value],
            "cluster_shard_num": len(remote_infos[InstanceRole.REDIS_MASTER.value]),
            "machine_pair_cnt": machine_pair_cnt,
            "module_names": cls.redis_cluster_module_map.get(cluster.id, []),
            "delete_rate": delete_rate_configs[get_redis_type_by_cluster_type(cluster.cluster_type)],
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
            dns_to_clb,
        )
        cluster_info.update(cluster_extra_info)
        return cluster_info

    @classmethod
    def query_master_slave_map(cls, master_ips):
        """根据master的ip查询主从状态对"""

        # 取消查询，否则sql报错
        if not master_ips:
            return {}

        where_sql = "where mim.ip in ({})".format(",".join(["%s"] * len(master_ips)))
        with connection.cursor() as cursor:
            cursor.execute(SQL_QUERY_MASTER_SLAVE_STATUS.format(where=where_sql), master_ips)
            master_slave_map = {ms["ip"]: ms for ms in dictfetchall(cursor)}

        return master_slave_map

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
        # 获取机器的基础信息
        data = super()._list_machines(bk_biz_id, query_params, limit, offset, filter_params_map, **kwargs)
        count, machines = data.count, data.data

        # redis额外补充主从状态
        if query_params.get("add_role_count"):
            master_ips = [m["ip"] for m in machines if m["instance_role"] == InstanceRole.REDIS_MASTER]
            master_slave_map = cls.query_master_slave_map(master_ips)
            for item in machines:
                item.update(master_slave_map.get(item["ip"], {}))

        return ResourceList(count=count, data=machines)

    @classmethod
    def fill_instances_to_cluster_info(cls, cluster_info: Dict, instance_queryset: QuerySet, role_header_ids: set):
        """
        将实例信息填充到集群信息中
        """

        instances = instance_queryset.all()
        if not instances.exists():
            return

        # 获取第一个实例的集群类型即可
        cluster_type = instances[0].cluster_type
        for ins in instances:
            role = ins.instance_role

            # 添加实例信息
            if role in cluster_info:
                cluster_info[role] += f"\n{ins.machine.ip}:{ins.port}"
            else:
                role_header_ids.add(role)
                cluster_info[role] = f"{ins.machine.ip}:{ins.port}"

        # 补充集群的分片信息
        if isinstance(instances[0], StorageInstance):
            seg_range_map, instance_tuple = seg_instance_info(instances[0].bk_biz_id, instance_queryset)
            _, remote_infos = remote_tuple_info(seg_range_map, instance_tuple, cluster_type, instances)
            for role in (InstanceRole.REDIS_MASTER.value, InstanceRole.REDIS_SLAVE.value):
                cluster_info[role] = ""
                for ins in remote_infos[role]:
                    if ins.get("seg_range", ""):
                        cluster_info[role] += f"\n{ins['instance']}({ins['seg_range']})"
                    else:
                        cluster_info[role] += f"\n{ins['instance']}"

    @classmethod
    def update_headers(cls, headers, **kwargs):
        # redis主从无clb/北极星
        if kwargs["cluster_type"] == ClusterType.TendisRedisInstance.value:
            return headers, []
        extra_headers = [
            {"id": "clb", "name": _("clb")},
            {"id": "polaris", "name": _("北极星")},
        ]

        # 替换原headers的db_module_name为modules
        item = next((item for item in headers if item["id"] == "db_module_name"), None)
        if item:
            item.update({"id": "db_module_name", "name": _("modules")})

        # redis集群架构不需要从域名
        filtered_headers = list(filter(lambda header: header["id"] != "slave_domain", headers))

        return filtered_headers, extra_headers

    @classmethod
    def update_cluster_info(cls, cluster, cluster_info, **kwargs):
        """
        补充额外的集群列表数据
        """
        # 替换原headers的cluster_info字段db_module_name为modules
        cluster_info["db_module_name"] = cls.redis_cluster_module_map.get(cluster.id, "")

        # redis主从无clb/北极星
        if cluster.cluster_type == ClusterType.TendisRedisInstance.value:
            return cluster_info

        # 补充clb/北极星
        clb_entry, polaris_entry = CommonQueryResourceMixin.get_cluster_clb_polaris_entries(cluster)
        cluster_info.update(
            {
                "clb": clb_entry,
                "polaris": polaris_entry,
            }
        )
        # 删除cluster_info中的从域名
        del cluster_info["slave_domain"]
        return cluster_info


def seg_instance_info(bk_biz_id, storage_queryset):
    """
    获取实例的主从对应关系及分片信息

    """
    # 这里不要用prefetch，在实例数过多的时候内存处理反而比sql查询更慢，这里提前做map缓存
    storage_ids = list(storage_queryset.values_list("id", flat=True))
    # 获得tuple对应的id映射
    seg_ranges = NosqlStorageSetDtl.objects.filter(bk_biz_id=bk_biz_id, instance__in=storage_ids).values_list(
        "instance", "seg_range"
    )
    seg_range_map = {t[0]: t[1] for t in seg_ranges}
    # 获取实例的主从对应关系元组列表
    instance_tuple = (
        StorageInstanceTuple.objects.filter(ejector__in=storage_ids)
        .order_by("-create_at")
        .values_list("ejector", "receiver")
    )
    # 获取实例id对应的分片信息
    for t in instance_tuple:
        if t[0] in seg_range_map:
            seg_range_map[t[1]] = seg_range_map[t[0]]

    return seg_range_map, instance_tuple


def remote_tuple_info(seg_range_map, instance_tuple, cluster_type, instances):
    """
    补充实例分片信息 按分片信息排序
    param: seg_range_map  实例分片信息的映射
    param: instance_tuple  实例的主从映射
    param: cluster_type 集群类型
    param: instances 实例的queryset集
    """
    remote_infos = {InstanceRole.REDIS_MASTER.value: [], InstanceRole.REDIS_SLAVE.value: []}
    for inst in instances:
        seg_range = seg_range_map.get(inst.id, "")
        remote_infos[inst.instance_role].append({**inst.simple_desc, "seg_range": seg_range, "id": inst.id})

    # 对 master 和 slave 的 seg_range 进行排序
    machine_list = []
    for role in [InstanceRole.REDIS_MASTER.value, InstanceRole.REDIS_SLAVE.value]:
        remote_infos[role].sort(key=lambda x: int(x["seg_range"].split("-")[0]) if x["seg_range"] else -1)
        machine_list.extend([inst["bk_host_id"] for inst in remote_infos[role]])

    # 集群类型Tendisplus、RedisCluster无分片信息 需特殊处理主从对应关系
    if cluster_type in [ClusterType.TendisPredixyRedisCluster, ClusterType.TendisPredixyTendisplusCluster]:
        result = {InstanceRole.REDIS_MASTER.value: [], InstanceRole.REDIS_SLAVE.value: []}
        master_index = {master["id"]: master for master in remote_infos[InstanceRole.REDIS_MASTER.value]}
        slave_index = {slave["id"]: slave for slave in remote_infos[InstanceRole.REDIS_SLAVE.value]}

        for master_id, slave_id in instance_tuple:
            if master_id in master_index:
                result[InstanceRole.REDIS_MASTER.value].append(master_index[master_id])
            if slave_id in slave_index:
                result[InstanceRole.REDIS_SLAVE.value].append(slave_index[slave_id])
        remote_infos = result

    return machine_list, remote_infos
