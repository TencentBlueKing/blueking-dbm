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

from backend.db_meta.enums import ClusterType


def is_redis_instance_type(cluster_type: str) -> bool:
    """
    是否是redis实例类型
    """
    return cluster_type in [
        ClusterType.TendisPredixyRedisCluster,
        ClusterType.RedisCluster,
        ClusterType.TendisTwemproxyRedisInstance,
        ClusterType.TendisRedisInstance,
        ClusterType.TendisRedisCluster,
    ]


def is_tendisplus_instance_type(cluster_type: str) -> bool:
    """
    是否是tendisplus实例集群类型
    """
    return cluster_type in [
        ClusterType.TendisPredixyTendisplusCluster,
        ClusterType.TendisTwemproxyTendisplusIns,
        ClusterType.TendisTendisplusInsance,
        ClusterType.TendisTendisplusCluster,
        ClusterType.TendisPredixyTendisplusInstance,
    ]


def is_tendisssd_instance_type(cluster_type: str) -> bool:
    """
    是否是tendisssd实例类型
    """
    return cluster_type in [ClusterType.TwemproxyTendisSSDInstance, ClusterType.TendisTendisSSDInstance]


def is_twemproxy_proxy_type(cluster_type: str) -> bool:
    """
    是否是twemproxy proxy类型
    """
    return cluster_type in [
        ClusterType.TendisTwemproxyRedisInstance,
        ClusterType.TendisTwemproxyTendisplusIns,
        ClusterType.TwemproxyTendisSSDInstance,
    ]


def is_predixy_proxy_type(cluster_type: str) -> bool:
    """
    是否是predixy proxy类型
    """
    return cluster_type in [
        ClusterType.TendisPredixyRedisCluster,
        ClusterType.TendisPredixyTendisplusCluster,
        ClusterType.TendisPredixyTendisplusInstance,
    ]


def is_redis_cluster_protocal(cluster_type: str) -> bool:
    """
    是否是redis_cluster协议
    """
    return cluster_type in [
        ClusterType.TendisPredixyRedisCluster,
        ClusterType.TendisPredixyTendisplusCluster,
        ClusterType.RedisCluster,
    ]


def is_predixy_standalone_type(cluster_type: str) -> bool:
    """
    是否是 predixy + 主从版(standalone) 类型
    该类型后端是主从实例,非redis cluster协议,
    predixy使用StandaloneServerPool,servers只包含master节点且带seg_range分片信息
    """
    return cluster_type in [
        ClusterType.TendisPredixyTendisplusInstance,
    ]


def is_seg_range_shard_type(cluster_type: str) -> bool:
    """
    是否是按 seg_range 分片的集群类型
    这类集群在 db_meta_nosqlstoragesetdtl 表中有分片(seg_range)记录,
    proxy 依赖 seg_range 做 key 路由, dbmon 也依赖 seg_range 上报 shard_value
    """
    return is_twemproxy_proxy_type(cluster_type) or is_predixy_standalone_type(cluster_type)


def cal_proxy_servers(cluster_type: str, cluster_name: str, redis_master_set: list, redis_slave_set: list) -> list:
    """
    计算proxy配置文件中的servers列表
    @param cluster_type: 集群类型
    @param cluster_name: 集群名,twemproxy的servers中需要
    @param redis_master_set: master实例列表,分片类集群元素格式为 "ip:port seg_range",其余为 "ip:port"
    @param redis_slave_set: slave实例列表,元素格式为 "ip:port"

    - twemproxy: "ip:port cluster_name seg_range weight"
    - predixy主从版(StandaloneServerPool): 只路由到master节点,元素格式为 "ip:port seg_range"
    - predixy redis_cluster协议(ClusterServerPool): 路由到所有节点(master+slave)
    """
    if is_twemproxy_proxy_type(cluster_type):
        servers = []
        for master in redis_master_set:
            ip_port, seg_range = str.split(master)
            servers.append("{} {} {} {}".format(ip_port, cluster_name, seg_range, 1))
        return servers
    if is_predixy_standalone_type(cluster_type):
        return list(redis_master_set)
    return list(redis_master_set) + list(redis_slave_set)


def is_have_proxy(cluster_type: str) -> bool:
    """
    是否有proxy
    """
    return is_twemproxy_proxy_type(cluster_type) or is_predixy_proxy_type(cluster_type)


def is_have_binlog(cluster_type: str) -> bool:
    """
    是否有binlog
    """
    return cluster_type in [
        ClusterType.TendisplusInstance.value,
        ClusterType.TendisSSDInstance.value,
    ]


def is_support_redis_auotfix(cluster_type: str) -> bool:
    """
    是否支持自愈
    """
    return cluster_type in [
        ClusterType.TendisTwemproxyRedisInstance.value,
        ClusterType.TwemproxyTendisSSDInstance.value,
        ClusterType.TendisPredixyTendisplusCluster.value,
        ClusterType.TendisPredixyTendisplusInstance.value,
        ClusterType.TendisPredixyRedisCluster.value,
        ClusterType.TendisRedisInstance.value,
        ClusterType.MongoShardedCluster.value,
        ClusterType.MongoReplicaSet.value,
    ]
