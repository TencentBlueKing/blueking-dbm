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
from dataclasses import dataclass

from backend.flow.utils.mysql.dts.constants import (
    MYSQL_DTS_MASTER_PEER_PORT,
    MYSQL_DTS_MASTER_PORT,
    MYSQL_DTS_WORKER_PORT,
)
from backend.flow.utils.mysql.dts.context import DtsHostSpec, HostDeployPlan


def group_deploy_hosts(master_hosts: list[DtsHostSpec], worker_hosts: list[DtsHostSpec]) -> HostDeployPlan:
    master_ip_set = {h.ip for h in master_hosts}
    worker_ip_set = {h.ip for h in worker_hosts}
    colocated_ips = master_ip_set & worker_ip_set
    colocated_hosts = [h for h in master_hosts if h.ip in colocated_ips]
    master_only_hosts = [h for h in master_hosts if h.ip not in colocated_ips]
    worker_only_hosts = [h for h in worker_hosts if h.ip not in colocated_ips]
    return HostDeployPlan(
        colocated_hosts=colocated_hosts,
        master_only_hosts=master_only_hosts,
        worker_only_hosts=worker_only_hosts,
    )


def build_master_node_name(index: int) -> str:
    return f"dm-master-{index}"


def build_worker_node_name(existing_workers: list[dict], index_offset: int = 0) -> str:
    max_idx = 0
    for worker in existing_workers:
        name = worker.get("name", "")
        if name.startswith("dm-worker-"):
            try:
                max_idx = max(max_idx, int(name.split("-")[-1]))
            except ValueError:
                pass
    return f"dm-worker-{max_idx + index_offset + 1}"


def render_master_config(
    *,
    deploy_path: str,
    node_name: str,
    advertise_ip: str,
    master_ha: bool = False,
    peer_addrs: list[str] | None = None,
) -> str:
    """渲染 dm-master.toml，字段对齐官方 mysql-dts 介质包样例。"""
    data_dir = f"{deploy_path}/{node_name}-data"
    log_file = f"{deploy_path}/{node_name}.log"
    peer_url = f"http://{advertise_ip}:{MYSQL_DTS_MASTER_PEER_PORT}"
    if peer_addrs:
        # peer_addrs 形如 ["dm-master-1=http://ip:18401", ...]
        initial_cluster = ",".join(peer_addrs)
    else:
        initial_cluster = f"{node_name}={peer_url}"
    return f"""# dm-master.toml
name = "{node_name}"
master-addr = "{advertise_ip}:{MYSQL_DTS_MASTER_PORT}"
peer-urls = "{peer_url}"
initial-cluster = "{initial_cluster}"
data-dir = "{data_dir}"
log-file = "{log_file}"
log-level = "info"
log-rotate = "1d"
openapi = true
"""


def render_worker_config(
    *,
    deploy_path: str,
    node_name: str,
    advertise_ip: str,
    master_addr: str,
    join_addrs: list[str] | None = None,
) -> str:
    """渲染 dm-worker.toml，字段对齐官方 mysql-dts 介质包样例。"""
    relay_dir = f"{deploy_path}/{node_name}-data"
    log_file = f"{deploy_path}/{node_name}.log"
    # 样例为字符串 join = "ip:18301"；多 Master 时用逗号拼接
    join_addrs = join_addrs or [master_addr]
    join_value = ",".join(join_addrs)
    return f"""# dm-worker.toml
name = "{node_name}"
worker-addr = "{advertise_ip}:{MYSQL_DTS_WORKER_PORT}"
join = "{join_value}"
relay-dir = "{relay_dir}"
log-file = "{log_file}"
log-level = "info"
log-rotate = "1d"
"""


@dataclass
class DeployedNodeInfo:
    ip: str
    bk_cloud_id: int
    name: str
    port: int
    role: str

    def to_dict(self) -> dict:
        return {
            "ip": self.ip,
            "bk_cloud_id": self.bk_cloud_id,
            "name": self.name,
            "port": self.port,
            "role": self.role,
        }


def build_master_addr(master_nodes: list[dict]) -> str:
    if not master_nodes:
        return ""
    first = master_nodes[0]
    return f"{first['ip']}:{first.get('port', MYSQL_DTS_MASTER_PORT)}"
