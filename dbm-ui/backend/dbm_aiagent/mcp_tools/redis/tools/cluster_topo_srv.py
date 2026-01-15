"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from typing import Dict

from django.utils.translation import gettext_lazy as _

from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster

from .comm_tools import sort_by_ip_port
from .redis_info_srv import RedisInfoService


class RedisClusterTopologyService:
    """Redis集群拓扑查询服务"""

    def __init__(self, immute_domain: str):
        """
        初始化Redis连接
        """
        self.cluster_obj = Cluster.objects.get(immute_domain=immute_domain)

        self.cluster_nodes = [
            {"host": s.machine.ip, "port": s.port, "role": s.instance_role}
            for s in self.cluster_obj.storageinstance_set.all()
        ]
        self.node_clients = {}

    def get_node_info(self, host: str, port: int) -> Dict:
        """
        获取单个节点的信息
        """
        key = f"{host}:{port}"
        client = RedisInfoService(addr=key, immute_domain=self.cluster_obj.immute_domain)

        if not client:
            return {
                "ip": host,
                "port": port,
                "keys": 0,
                "memory_human": "0B",
                "qps": 0,
                "status": "ERROR",
                "error": "Connection failed",
            }

        try:
            # 获取键空间信息
            keyspace_info = client.get_keyspace_info()
            total_keys = 0
            for db_info in keyspace_info:
                total_keys += int(db_info["keys"])

            # 获取内存信息
            memory_info = client.get_memory_info()
            memory_human = memory_info.get("used_memory_human", "0B")

            if self.cluster_obj.cluster_type in [
                ClusterType.TendisPredixyTendisplusCluster.value,
                ClusterType.TendisTendisSSDInstance.value,
            ]:
                memory_human = memory_info.get("disk_size_human", "0B")

            stats = client.get_stats_info()
            # 获取QPS（通过两次采样计算）
            qps = stats.get("instantaneous_ops_per_sec", -1)

            # 获取同步状态
            status = "OK"
            repl_status = client.get_replication_info()
            if repl_status.get("role", "x") == "master" and int(repl_status.get("connected_slaves", 0)) == 0:
                status = "NO-SLAVE"

            if repl_status.get("role", "x") == "slave" and repl_status.get("master_link_status", "down") == "down":
                status = "LINK-DOWN"
            elif (
                repl_status.get("role", "x") == "slave"
                and int(repl_status.get("master_last_io_seconds_ago", "-1")) > 10
            ):
                status = repl_status.get("master_last_io_seconds_ago", "-1")

            return {
                "ip": host,
                "port": port,
                "keys": total_keys,
                "memory_human": memory_human,
                "qps": qps,
                "status": status,
            }
        except Exception as e:
            return {
                "ip": host,
                "port": port,
                "keys": -1,
                "memory_human": "0B",
                "qps": -1,
                "status": "ERROR",
                "error": str(e),
            }

    def get_master_slaves_info(self, master_host: str, master_port: int) -> Dict:
        """
        获取主节点及其从节点信息
        """
        key = f"{master_host}:{master_port}"
        client = RedisInfoService(key, self.cluster_obj.immute_domain)

        # 获取主节点信息
        master_info = self.get_node_info(master_host, master_port)

        # 获取复制信息
        slaves_info = []
        connected_slaves = 0
        total_slaves = 0

        if client:
            try:
                repl_info = client.get_replication_info()
                connected_slaves = repl_info.get("connected_slaves", 0)
                total_slaves = connected_slaves

                # 解析从节点信息
                for slave_data in repl_info.get("slaves", []):

                    # 获取从节点详细信息
                    slave_detail = self.get_node_info(slave_data["ip"], slave_data["port"])

                    # 添加复制延迟
                    slave_detail["replication_lag"] = slave_data.get("lag", 0)

                    slaves_info.append(slave_detail)
            except Exception as e:
                print(_("获取主节点 {} 的从节点信息失败: {}".format(key, e)))

        return {
            **master_info,
            "connected_slaves": connected_slaves,
            "total_slaves": total_slaves,
            "slaves": slaves_info,
        }

    def get_cluster_topology(self) -> Dict:
        """
        获取完整的集群拓扑信息

        Returns:
            集群拓扑字典
        """

        # 获取所有主节点
        master_nodes = [node for node in self.cluster_nodes if node.get("role") == "redis_master"]

        masters_info = []
        total_keys = 0
        total_qps = 0
        total_slaves = 0

        for master in master_nodes:
            master_data = self.get_master_slaves_info(master["host"], master["port"])
            masters_info.append(master_data)

            total_keys += master_data["keys"]
            total_qps += master_data["qps"]
            total_slaves += len(master_data["slaves"])

            # 累加从节点的QPS
            for slave in master_data["slaves"]:
                total_qps += slave["qps"]

        return {
            "total_masters": len(master_nodes),
            "total_slaves": total_slaves,
            "total_keys": total_keys,
            "total_qps": total_qps,
            "masters": masters_info,
        }

    def format_topology_text(self, topology: Dict) -> str:
        """
        将拓扑信息格式化为文本
        """
        lines = []

        for master in sort_by_ip_port(topology["masters"]):
            # 主节点信息
            master_line = (
                f"{master['ip']}:{master['port']} "
                f"({master['keys']} keys {master['memory_human']}) "
                f"{master['qps']}/s {master['status']}"
            )

            # 从节点信息
            if master["slaves"]:
                slave_parts = []
                for slave in master["slaves"]:
                    slave_part = (
                        f"{slave['ip']}:{slave['port']} "
                        f"({slave['keys']} keys {slave['memory_human']}) "
                        f"{slave['qps']}/s {slave['status']}"
                    )
                    slave_parts.append(slave_part)

                # 组合主从信息
                full_line = (
                    f"{master_line} => "
                    f"({master['connected_slaves']}/{master['total_slaves']} slaves) "
                    f"{' | '.join(slave_parts)}"
                )
            else:
                full_line = f"{master_line} => (0/0 slaves)"

            lines.append(full_line)

        return "\n".join(lines)
