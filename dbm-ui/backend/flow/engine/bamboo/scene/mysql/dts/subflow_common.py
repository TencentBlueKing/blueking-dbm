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
from dataclasses import asdict
from typing import Any

from backend import env
from backend.flow.engine.bamboo.scene.mysql.common.common_sub_flow import init_machine_sub_flow
from backend.flow.utils.mysql.dts.constants import (
    MYSQL_DTS_MASTER_PEER_PORT,
    MYSQL_DTS_MASTER_PORT,
    MYSQL_DTS_WORKER_PORT,
    get_default_deploy_path,
)
from backend.flow.utils.mysql.dts.context import DtsHostSpec
from backend.flow.utils.mysql.dts.deploy_helper import (
    DeployedNodeInfo,
    build_master_addr,
    build_master_node_name,
    build_worker_node_name,
    render_master_config,
    render_worker_config,
)
from backend.flow.utils.mysql.mysql_act_dataclass import DownloadMediaKwargs


def resolve_deploy_path(cluster_name: str, deploy_path: str = "") -> str:
    return deploy_path or get_default_deploy_path(cluster_name)


def hosts_to_exec_targets(hosts: list[DtsHostSpec]) -> list[dict]:
    return [{"ip": host.ip, "bk_cloud_id": host.bk_cloud_id} for host in hosts]


def unique_host_ips(hosts: list[DtsHostSpec]) -> list[str]:
    """Keep first-seen IP order; drop empties and duplicates."""
    return list(dict.fromkeys(host.ip for host in hosts if host.ip))


def add_dts_idle_check_subflow(sub, *, root_id: str, bk_cloud_id: int, hosts: list[DtsHostSpec]) -> None:
    """Mount MySQL idle-check subflow for new DTS hosts; skip if no IPs or SA template."""
    unique_ips = unique_host_ips(hosts)
    if not unique_ips or not env.SA_CHECK_TEMPLATE_ID:
        return
    sub.add_sub_pipeline(
        sub_flow=init_machine_sub_flow(
            uid=root_id,
            root_id=root_id,
            bk_cloud_id=bk_cloud_id,
            sys_init_ips=[],
            init_check_ips=unique_ips,
        )
    )


def build_dts_trans_file_kwargs(
    hosts: list[DtsHostSpec],
    bk_cloud_id: int,
    dts_pkg_id: int | None = None,
) -> tuple[dict[str, Any], str]:
    """组装 TransFileComponent 下发 DTS 介质的 kwargs。

    Returns:
        (kwargs, pkg_name)：pkg_name 为下发到目标机的介质文件名。
    """
    from backend.flow.utils.mysql.dts.package_resolver import build_mysql_dts_bkrepo_paths, resolve_mysql_dts_package

    pkg = resolve_mysql_dts_package(pkg_id=dts_pkg_id)
    file_list, pkg_name = build_mysql_dts_bkrepo_paths(pkg)
    kwargs = asdict(
        DownloadMediaKwargs(
            bk_cloud_id=bk_cloud_id,
            exec_ip=[host.ip for host in hosts],
            file_list=file_list,
            file_target_path="/data/install",
        )
    )
    return kwargs, pkg_name


def build_dts_exec_shell_kwargs(exec_targets: list[dict], shell_script: str) -> dict[str, Any]:
    """组装 MysqlDtsExecShellComponent 的 kwargs（脚本需在 subflow 侧预渲染）。"""
    return {
        "exec_targets": exec_targets,
        "shell_script": shell_script,
    }


def build_master_nodes(hosts: list[DtsHostSpec], master_ha: bool = False) -> list[dict]:
    nodes = []
    peer_addrs = []
    for idx, host in enumerate(hosts, start=1):
        name = host.name or build_master_node_name(idx)
        peer_addrs.append(f"{name}=http://{host.ip}:{MYSQL_DTS_MASTER_PEER_PORT}")
        nodes.append(
            DeployedNodeInfo(
                ip=host.ip,
                bk_cloud_id=host.bk_cloud_id,
                name=name,
                port=MYSQL_DTS_MASTER_PORT,
                role="master",
            ).to_dict()
        )
    return nodes, peer_addrs


def build_worker_nodes(
    hosts: list[DtsHostSpec],
    existing_workers: list[dict] | None = None,
    name_offset: int = 0,
) -> list[dict]:
    nodes = []
    for idx, host in enumerate(hosts):
        name = host.name or build_worker_node_name(existing_workers or [], index_offset=idx + name_offset)
        nodes.append(
            DeployedNodeInfo(
                ip=host.ip,
                bk_cloud_id=host.bk_cloud_id,
                name=name,
                port=MYSQL_DTS_WORKER_PORT,
                role="worker",
            ).to_dict()
        )
    return nodes


def master_config_file(node_name: str) -> str:
    return f"{node_name}.toml"


def worker_config_file(node_name: str) -> str:
    return f"{node_name}.toml"


__all__ = [
    "build_dts_exec_shell_kwargs",
    "build_dts_trans_file_kwargs",
    "build_master_addr",
    "build_master_nodes",
    "build_worker_nodes",
    "hosts_to_exec_targets",
    "master_config_file",
    "render_master_config",
    "render_worker_config",
    "resolve_deploy_path",
    "worker_config_file",
]
