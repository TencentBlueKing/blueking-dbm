"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from typing import Dict, List

from backend.dbm_aiagent.mcp_tools.redis.tools.cluster_topo_srv import RedisClusterTopologyService
from backend.dbm_aiagent.mcp_tools.redis.tools.redis_client_srv import RedisClientListService
from backend.dbm_aiagent.mcp_tools.redis.tools.redis_info_srv import RedisInfoService


def get_redis_server_info(redis_addr: str, immute_domain: str) -> Dict:
    """获取Redis服务器基本信息"""
    service = RedisInfoService(addr=redis_addr, immute_domain=immute_domain)
    return service.get_server_info()


def get_redis_clients_info(redis_addr: str, immute_domain: str) -> Dict:
    """获取Redis客户端连接信息"""
    service = RedisInfoService(addr=redis_addr, immute_domain=immute_domain)
    return service.get_clients_info()


def get_redis_memory_info(redis_addr: str, immute_domain: str) -> Dict:
    """获取Redis内存使用信息"""
    service = RedisInfoService(addr=redis_addr, immute_domain=immute_domain)
    return service.get_memory_info()


def get_redis_persistence_info(redis_addr: str, immute_domain: str) -> Dict:
    """获取Redis持久化信息"""
    service = RedisInfoService(addr=redis_addr, immute_domain=immute_domain)
    return service.get_persistence_info()


def get_redis_stats_info(redis_addr: str, immute_domain: str) -> Dict:
    """获取Redis统计信息"""
    service = RedisInfoService(addr=redis_addr, immute_domain=immute_domain)
    return service.get_stats_info()


def get_redis_replication_info(redis_addr: str, immute_domain: str) -> Dict:
    """获取Redis复制信息"""
    service = RedisInfoService(addr=redis_addr, immute_domain=immute_domain)
    return service.get_replication_info()


def get_redis_cpu_info(redis_addr: str, immute_domain: str) -> Dict:
    """获取Redis CPU使用信息"""
    service = RedisInfoService(addr=redis_addr, immute_domain=immute_domain)
    return service.get_cpu_info()


def get_redis_keyspace_info(redis_addr: str, immute_domain: str) -> List[Dict]:
    """获取Redis键空间信息"""
    service = RedisInfoService(addr=redis_addr, immute_domain=immute_domain)
    return service.get_keyspace_info()


def get_redis_client_list(redis_addr: str, immute_domain: str) -> Dict:
    """
    获取Redis客户端列表
    Returns:
        包含客户端总数和客户端列表的字典
    """
    service = RedisClientListService(addr=redis_addr, immute_domain=immute_domain)
    return service.get_client_list()


def get_redis_command_stats_delta(redis_addr: str, immute_domain: str, interval: float = 1.0) -> Dict:
    """
    获取Redis命令统计增量信息（间隔采样）

    Returns:
        包含命令统计增量的字典
    """
    service = RedisInfoService(addr=redis_addr, immute_domain=immute_domain)
    return service.get_command_stats_delta(interval=interval)


def get_redis_cluster_topology_text(immute_domain: str) -> Dict:
    """
    获取Redis集群拓扑信息（文本格式）
    """
    service = RedisClusterTopologyService(immute_domain=immute_domain)
    topology = service.get_cluster_topology()
    topology_text = service.format_topology_text(topology)

    return {
        "cluster_name": immute_domain,
        "topology_text": topology_text,
        "summary": {
            "total_masters": topology["total_masters"],
            "total_slaves": topology["total_slaves"],
            "total_keys": topology["total_keys"],
            "total_qps": topology["total_qps"],
        },
    }
