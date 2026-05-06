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

from backend.db_meta.enums import MachineType
from backend.db_meta.models import Cluster


class MongoDBInfoService:
    """MongoDB 信息查询服务（拓扑基于元数据，serverStatus 需对接 DRSApi.mongodb_rpc）"""

    def __init__(self, addr: str, immute_domain: str):
        self.addr = addr
        self.immute_domain = immute_domain
        self.cluster_obj = Cluster.objects.get(immute_domain=immute_domain)

    def get_server_status(self) -> Dict:
        """
        获取 MongoDB serverStatus 信息。
        当前返回基于元数据的占位结构，实际可对接 DRSApi.mongodb_rpc 执行 serverStatus 命令。
        """
        if not self.addr:
            return {
                "host": "",
                "version": self.cluster_obj.major_version or "",
                "uptime": 0,
                "connections": {"current": 0, "available": 0},
                "opcounters": {"insert": 0, "query": 0, "update": 0, "delete": 0},
                "mem": {"resident": 0, "virtual": 0},
            }
        host, port = self.addr.split(":") if ":" in self.addr else (self.addr, "27017")
        return {
            "host": self.addr,
            "version": self.cluster_obj.major_version or "",
            "uptime": 0,
            "connections": {"current": 0, "available": 0},
            "opcounters": {"insert": 0, "query": 0, "update": 0, "delete": 0},
            "mem": {"resident": 0, "virtual": 0},
        }

    def get_cluster_topology_text(self) -> Dict:
        """从元数据生成集群拓扑文本"""
        cluster = self.cluster_obj
        lines: List[str] = []
        # Mongos
        mongos_list = cluster.proxyinstance_set.filter(machine_type=MachineType.MONGOS)
        if mongos_list.exists():
            addrs = [f"{s.machine.ip}:{s.port}" for s in mongos_list]
            lines.append("mongos: " + " | ".join(addrs))
        # Shard / 副本集节点
        storages = cluster.storageinstance_set.filter(machine_type=MachineType.MONGODB).select_related("machine")
        if storages.exists():
            by_shard: Dict[str, List[str]] = {}
            instance_to_seg = {}
            for dtl in cluster.nosqlstoragesetdtl_set.all().select_related("instance"):
                instance_to_seg[dtl.instance_id] = dtl.seg_range
            for s in storages:
                addr = f"{s.machine.ip}:{s.port}"
                key = instance_to_seg.get(s.id, cluster.immute_domain)
                if key not in by_shard:
                    by_shard[key] = []
                by_shard[key].append(addr)
            for name, addrs in sorted(by_shard.items()):
                lines.append(f"{name}: " + " | ".join(addrs))
        topology_text = "\n".join(lines) if lines else "(no instances)"
        return {
            "cluster_id": cluster.id,
            "cluster_name": cluster.immute_domain,
            "topology_text": topology_text,
            "summary": {
                "mongos_count": mongos_list.count() if mongos_list else 0,
                "storage_count": storages.count(),
            },
        }
