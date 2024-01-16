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


def is_have_binlog(cluster_type: str) -> bool:
    """
    是否有binlog
    """
    return cluster_type in [
        ClusterType.TendisplusInstance.value,
        ClusterType.TendisSSDInstance.value,
    ]
