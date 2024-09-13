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

from backend.db_meta.api.cluster.rediscluster.handler import RedisClusterHandler
from backend.db_meta.api.cluster.redisinstance.handler import RedisInstanceHandler
from backend.db_meta.api.cluster.tendiscache.handler import TendisCacheClusterHandler
from backend.db_meta.api.cluster.tendispluscluster.handler import TendisPlusClusterHandler
from backend.db_meta.api.cluster.tendisssd.handler import TendisSSDClusterHandler
from backend.db_meta.enums import ClusterEntryType, InstanceRole
from backend.db_meta.enums.cluster_type import ClusterType
from backend.db_meta.enums.spec import SpecClusterType
from backend.db_meta.models import AppCache, Machine, Spec
from backend.db_meta.models.cluster import Cluster
from backend.db_services.dbbase.resources import query
from backend.db_services.dbbase.resources.query import ResourceList
from backend.db_services.dbbase.resources.register import register_resource_decorator
from backend.db_services.ipchooser.query.resource import ResourceQueryHelper
from backend.db_services.redis.resources.constants import SQL_QUERY_MASTER_SLAVE_STATUS
from backend.utils.basic import dictfetchall


@register_resource_decorator()
class RedisListRetrieveResource(query.ListRetrieveResource):
    """查看twemproxy-redis架构的资源"""

    cluster_types = [
        ClusterType.TendisPredixyRedisCluster.value,
        ClusterType.TendisPredixyTendisplusCluster.value,
        ClusterType.TendisTwemproxyRedisInstance.value,
        ClusterType.TwemproxyTendisSSDInstance.value,
        ClusterType.TendisTwemproxyTendisplusIns.value,
        ClusterType.TendisRedisInstance.value,
        ClusterType.TendisTendisplusInsance.value,
        ClusterType.TendisRedisCluster.value,
        ClusterType.TendisTendisplusCluster.value,
    ]
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
        # 预取remote的spec
        redis_spec_map = {spec.spec_id: spec for spec in Spec.objects.filter(spec_cluster_type=SpecClusterType.Redis)}
        return super()._filter_cluster_hook(
            bk_biz_id,
            cluster_queryset,
            proxy_queryset,
            storage_queryset,
            limit,
            offset,
            redis_spec_map=redis_spec_map,
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
        """集群序列化"""
        redis_master = [m.simple_desc for m in cluster.storages if m.instance_role == InstanceRole.REDIS_MASTER]
        redis_slave = [m.simple_desc for m in cluster.storages if m.instance_role == InstanceRole.REDIS_SLAVE]
        machine_list = list(set([inst["bk_host_id"] for inst in [*redis_master, *redis_slave]]))
        machine_pair_cnt = len(machine_list) / 2

        # 补充集群的规格和容量信息
        cluster_spec = cluster_capacity = ""
        redis_spec_map = kwargs["redis_spec_map"]
        if machine_list:
            spec_id = cluster.storages[0].machine.spec_id
            spec = redis_spec_map.get(spec_id)
            cluster_spec = model_to_dict(spec) if spec else {}
            cluster_capacity = spec.capacity * machine_pair_cnt if spec else 0

        # dns是否指向clb
        dns_to_clb = cluster.clusterentry_set.filter(
            cluster_entry_type=ClusterEntryType.DNS.value,
            entry=cluster.immute_domain,
            forward_to__cluster_entry_type=ClusterEntryType.CLB.value,
        ).exists()

        # 集群额外信息
        cluster_extra_info = {
            "cluster_spec": cluster_spec,
            "cluster_capacity": cluster_capacity,
            "dns_to_clb": dns_to_clb,
            "proxy": [m.simple_desc for m in cluster.proxies],
            "redis_master": redis_master,
            "redis_slave": redis_slave,
            "cluster_shard_num": len(redis_master),
            "machine_pair_cnt": machine_pair_cnt,
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
