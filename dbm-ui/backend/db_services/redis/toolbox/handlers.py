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
import itertools
import json
from collections import defaultdict

from django.db import connection
from django.db.models import Count, F, Q
from django.forms import model_to_dict

from backend import env
from backend.db_meta.enums import ClusterType, InstanceRole
from backend.db_meta.enums.comm import RedisVerUpdateNodeType
from backend.db_meta.models import Cluster, ProxyInstance, StorageInstance, StorageInstanceTuple
from backend.db_services.ipchooser.handlers.host_handler import HostHandler
from backend.db_services.ipchooser.query.resource import ResourceQueryHelper
from backend.db_services.redis.resources.constants import (
    SQL_QUERY_COUNT_INSTANCES,
    SQL_QUERY_INSTANCES,
    SQL_QUERY_MASTER_SLAVE_STATUS,
)
from backend.flow.utils.redis.redis_proxy_util import (
    get_cluster_proxy_version,
    get_cluster_proxy_version_for_upgrade,
    get_cluster_redis_version,
    get_cluster_storage_versions_for_upgrade,
)
from backend.ticket.constants import InstanceType
from backend.ticket.models import ClusterOperateRecord
from backend.utils.basic import dictfetchall


class ToolboxHandler:
    """redis工具箱查询接口封装"""

    def __init__(self, bk_biz_id: int):
        self.bk_biz_id = bk_biz_id

    def query_by_ip(self, ips) -> list:
        """根据ip查询实例、集群和规格相关信息"""

        ips = list(
            itertools.chain(
                StorageInstance.filter_by_ips(self.bk_biz_id, ips),
                ProxyInstance.filter_by_ips(self.bk_biz_id, ips),
            )
        )

        # 查询主从状态对
        master_slave_map = self.query_master_slave_map(
            [i["ip"] for i in ips if i["role"] == InstanceRole.REDIS_MASTER]
        )

        # 主从关系补充
        for item in ips:
            item.update(master_slave_map.get(item["ip"], {}))

        return ips

    def query_master_slave_by_ip(self, master_ips) -> list:
        """根据master主机查询集群、实例和对应的slave主机"""

        results = []
        for master_ip in master_ips:
            masters = StorageInstance.objects.filter(
                bk_biz_id=self.bk_biz_id, machine__ip=master_ip, instance_role=InstanceRole.REDIS_MASTER
            )
            if not masters.exists():
                continue

            ms_pairs = StorageInstanceTuple.objects.filter(ejector__machine__ip=master_ip)
            results.append(
                {
                    "cluster": masters.last().cluster.first().simple_desc,
                    "master_ip": master_ip,
                    "slave_ip": ms_pairs.last().receiver.machine.ip,
                    "slave_host_info": ms_pairs.last().receiver.machine.simple_desc,
                    "instances": map(lambda x: x.simple_desc, masters),
                }
            )

        return results

    def query_instance_by_cluster(self, keywords) -> list:
        """根据角色和关键字查询集群规格、方案和角色信息 - deprecated"""

        fields = ["id", "machine__ip", "port", "name", "status", "version", "machine__spec_config"]
        number_keywords = filter(lambda x: x.isnumeric(), keywords)
        clusters = Cluster.objects.filter(
            Q(id__in=number_keywords) | Q(name__in=keywords) | Q(immute_domain__in=keywords), bk_biz_id=self.bk_biz_id
        )

        results = []
        for cluster in clusters:
            results.append(
                {
                    "cluster": cluster.extra_desc,
                    InstanceType.PROXY.value: cluster.proxyinstance_set.all().values(*fields),
                    InstanceType.STORAGE.value: cluster.storageinstance_set.all().values(*fields, "instance_role"),
                }
            )

        return results

    def query_master_slave_pairs(self, cluster_id: int) -> list:
        """查询主从架构集群的关系对"""

        try:
            cluster = Cluster.objects.get(pk=cluster_id, bk_biz_id=self.bk_biz_id)
        except Cluster.DoesNotExist:
            return []

        pairs = StorageInstanceTuple.objects.filter(receiver__cluster=cluster, ejector__cluster=cluster).values(
            master_id=F("ejector__id"),
            master_ip=F("ejector__machine__ip"),
            master_port=F("ejector__port"),
            slave_id=F("receiver__id"),
            slave_ip=F("receiver__machine__ip"),
            slave_port=F("receiver__port"),
        )

        # 按照ip合并
        grouped = defaultdict(list)
        for pair in pairs:
            grouped[(pair["master_ip"], pair["slave_ip"])].append(pair["master_port"])

        result = []
        for mkey, ports in grouped.items():
            result.append(
                {
                    "master_ip": mkey[0],
                    "slave_ip": mkey[1],
                    "ports": ports,
                }
            )

        return result

    def query_cluster_list(self):
        """ "TODO: 切换为集群列表接口，deprecated"""

        clusters = Cluster.objects.filter(
            bk_biz_id=self.bk_biz_id,
            cluster_type__in=[
                ClusterType.TendisPredixyRedisCluster,
                ClusterType.TendisPredixyTendisplusCluster,
                ClusterType.TendisTwemproxyRedisInstance,
                ClusterType.TwemproxyTendisSSDInstance,
                ClusterType.TendisTwemproxyTendisplusIns,
                ClusterType.TendisRedisInstance,
                ClusterType.TendisTendisSSDInstance,
                ClusterType.TendisTendisplusInsance,
                ClusterType.TendisRedisCluster,
                ClusterType.TendisTendisplusCluster,
            ],
        ).order_by("-create_at", "name")

        cloud_info = ResourceQueryHelper.search_cc_cloud(get_cache=True, fields=["bk_cloud_id", "bk_cloud_name"])

        results = []
        for cluster in clusters:
            result = {
                **model_to_dict(cluster),
                "operations": ClusterOperateRecord.objects.get_cluster_operations(cluster.id),
                "cloud_info": cloud_info[str(cluster.bk_cloud_id)],
                "proxy_count": cluster.proxyinstance_set.count(),
                "storage_count": len(set(cluster.storageinstance_set.all().values_list("machine__ip"))),
            }
            for storage in (
                cluster.storageinstance_set.values("instance_role")
                .annotate(cnt=Count("machine__ip", distinct=True))
                .order_by()
            ):
                result["{}_count".format(storage["instance_role"])] = storage["cnt"]

            results.append(result)

        return results

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

    def query_cluster_ips(self, limit=None, offset=None, cluster_id=None, ip=None, role=None, status=None):
        """聚合查询集群下的主机"""

        limit_sql = ""
        if limit:
            # 强制格式化为int，避免sql注入
            limit_sql = " LIMIT {}".format(int(limit))

        offset_sql = ""
        if offset:
            offset_sql = " OFFSET {}".format(int(offset))

        where_sql = "WHERE i.bk_biz_id = %s "
        where_values = [self.bk_biz_id]

        if cluster_id:
            placeholder = ",".join(["%s"] * len(cluster_id))
            where_sql += f"AND c.cluster_id IN ({placeholder})"
            where_values.extend(cluster_id)

        if ip:
            ip_conditions = " OR ".join(["m.ip LIKE %s" for _ in ip])
            where_sql += f" AND ({ip_conditions})"
            where_ip_values = [f"%{single_ip}%" for single_ip in ip]
            where_values.extend(where_ip_values)

        if status:
            where_sql += "AND i.status = %s "
            where_values.append(status)
            # placeholders = ",".join(["%s"] * len(status))
            # where_sql += "AND i.status IN (" + placeholders + ") "
            # where_values.extend(status)

        if role:
            placeholder = ", ".join(["%s"] * len(role))
            having_sql = f"HAVING role IN ({placeholder}) "
            where_values.extend(role)

        else:
            having_sql = ""

        # union查询需要两份参数
        where_values = where_values * 2
        sql_count = SQL_QUERY_COUNT_INSTANCES.format(where=where_sql, having=having_sql)
        sql = SQL_QUERY_INSTANCES.format(where=where_sql, having=having_sql, limit=limit_sql, offset=offset_sql)

        with connection.cursor() as cursor:
            cursor.execute(sql_count, where_values)
            total_count = cursor.fetchone()[0]
            cursor.execute(sql, where_values)

        ips = dictfetchall(cursor)
        bk_host_ids = [ip["bk_host_id"] for ip in ips]

        # 查询主机信息
        host_id_info_map = {
            host_info["host_id"]: host_info
            for host_info in HostHandler.check(
                [{"bk_biz_id": env.DBA_APP_BK_BIZ_ID, "scope_type": "biz"}], [], [], bk_host_ids
            )
        }

        # 查询主从状态对
        master_slave_map = self.query_master_slave_map(
            [i["ip"] for i in ips if i["role"] == InstanceRole.REDIS_MASTER]
        )
        cloud_info = ResourceQueryHelper.search_cc_cloud(get_cache=True)
        # 补充主机、规格和主从关系信息、补充云区域信息
        for item in ips:
            item["host_info"] = host_id_info_map.get(item["bk_host_id"])
            item["spec_config"] = json.loads(item["spec_config"])
            item["bk_cloud_name"] = cloud_info[str(item["bk_cloud_id"])]["bk_cloud_name"]
            item.update(master_slave_map.get(item["ip"], {}))

        response = {"count": total_count, "results": ips}
        return response

    @classmethod
    def get_online_cluster_versions(cls, cluster_id: int, node_type: str):
        """根据cluster id获取集群现存版本"""
        if node_type == RedisVerUpdateNodeType.Backend.value:
            return [get_cluster_redis_version(cluster_id)]
        else:
            return get_cluster_proxy_version(cluster_id)

    @classmethod
    def get_update_cluster_versions(cls, cluster_id: int, node_type: str):
        """根据cluster类型获取版本信息"""
        if node_type == RedisVerUpdateNodeType.Backend.value:
            return get_cluster_storage_versions_for_upgrade(cluster_id)
        else:
            return get_cluster_proxy_version_for_upgrade(cluster_id)
