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
from django.utils.translation import gettext as _

from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.engine.bamboo.scene.mysql.dts.subflow_common import (
    build_dts_exec_shell_kwargs,
    build_dts_trans_file_kwargs,
    hosts_to_exec_targets,
    worker_config_file,
)
from backend.flow.plugins.components.collections.mysql.dts.base_shell import MysqlDtsExecShellComponent
from backend.flow.plugins.components.collections.mysql.dts.deploy.verify_deploy import MysqlDtsDeployVerifyComponent
from backend.flow.plugins.components.collections.mysql.dts.reinstall.precheck import MysqlDtsReinstallPrecheckComponent
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.utils.mysql.dts.context import DtsHostSpec, MysqlDtsReinstallSubflowInput
from backend.flow.utils.mysql.dts.script_template import (
    render_reinstall_master_script,
    render_reinstall_worker_script,
    render_stop_process_script,
)


def _collect_reinstall_hosts(inp: MysqlDtsReinstallSubflowInput) -> list[DtsHostSpec]:
    """从元数据节点收集所有需要重装的主机（按 IP 去重）。"""
    seen = set()
    hosts = []
    for node in inp.master_nodes + inp.worker_nodes:
        ip = node["ip"]
        if ip in seen:
            continue
        seen.add(ip)
        hosts.append(DtsHostSpec(ip=ip, bk_cloud_id=node.get("bk_cloud_id", inp.bk_cloud_id)))
    return hosts


def mysql_dts_reinstall_subflow(inp: MysqlDtsReinstallSubflowInput) -> SubBuilder:
    """重装 DTS 集群子流程。

    顺序：
    1) precheck（检查活跃迁移，force_reinstall 可跳过）
    2) stop（停止所有 DTS 进程）
    3) transfile（下发新介质到 /data/install）
    4) reinstall（解压到隔离目录 → 更新 bin 软链 → 用原 conf 拉起）
    5) verify（OpenAPI 连通性验收：master/worker 节点匹配）

    注意：
    - 不渲染/推送配置（既有 conf 绝对不动）
    - 不 rm -rf deploy_path
    - 节点名称沿用元数据已有 name
    - 不回写 MysqlDtsCluster.version（版本写库已取消）
    """
    reinstall_hosts = _collect_reinstall_hosts(inp)
    exec_targets = hosts_to_exec_targets(reinstall_hosts)

    sub = SubBuilder(
        root_id=inp.root_id,
        data={
            "bk_biz_id": inp.bk_biz_id,
            "bk_cloud_id": inp.bk_cloud_id,
            "uid": inp.root_id,
            "creator": inp.creator,
        },
    )

    # 1. 重装前置检查
    sub.add_act(
        act_name=_("重装前置检查"),
        act_component_code=MysqlDtsReinstallPrecheckComponent.code,
        kwargs={
            "dts_cluster_id": inp.dts_cluster_id,
            "force_reinstall": inp.force_reinstall,
        },
    )

    # 2. 停止 DTS 进程
    if exec_targets:
        sub.add_act(
            act_name=_("停止 DTS 进程"),
            act_component_code=MysqlDtsExecShellComponent.code,
            kwargs=build_dts_exec_shell_kwargs(exec_targets, render_stop_process_script(inp.deploy_path)),
        )

    # 3. 下发新介质
    trans_kwargs, pkg_name = build_dts_trans_file_kwargs(reinstall_hosts, inp.bk_cloud_id, inp.dts_pkg_id)
    sub.add_act(
        act_name=_("下发 DTS 介质"),
        act_component_code=TransFileComponent.code,
        kwargs=trans_kwargs,
    )

    # 4. 重装 Master 节点（并行）
    master_acts = []
    for node in inp.master_nodes:
        node_name = node.get("name", "")
        config_file = f"{node_name}.toml"
        script = render_reinstall_master_script(
            deploy_path=inp.deploy_path,
            pkg_name=pkg_name,
            config_file=config_file,
            dts_node_name=node_name,
        )
        master_acts.append(
            {
                "act_name": _("重装 Master {}").format(node_name),
                "act_component_code": MysqlDtsExecShellComponent.code,
                "kwargs": build_dts_exec_shell_kwargs(
                    [{"ip": node["ip"], "bk_cloud_id": node.get("bk_cloud_id", inp.bk_cloud_id)}],
                    script,
                ),
            }
        )
    if master_acts:
        sub.add_parallel_acts(acts_list=master_acts)

    # 5. 重装 Worker 节点（并行）
    worker_acts = []
    for node in inp.worker_nodes:
        node_name = node.get("name", "")
        config_file = worker_config_file(node_name)
        script = render_reinstall_worker_script(
            deploy_path=inp.deploy_path,
            pkg_name=pkg_name,
            config_file=config_file,
            dts_node_name=node_name,
        )
        worker_acts.append(
            {
                "act_name": _("重装 Worker {}").format(node_name),
                "act_component_code": MysqlDtsExecShellComponent.code,
                "kwargs": build_dts_exec_shell_kwargs(
                    [{"ip": node["ip"], "bk_cloud_id": node.get("bk_cloud_id", inp.bk_cloud_id)}],
                    script,
                ),
            }
        )
    if worker_acts:
        sub.add_parallel_acts(acts_list=worker_acts)

    # 6. 连通性验收
    sub.add_act(
        act_name=_("DTS 部署验收"),
        act_component_code=MysqlDtsDeployVerifyComponent.code,
        kwargs={
            "node_name": _("重装验收"),
            "master_addr": inp.master_addr,
            "verify_role": "all",
            "expected_master_nodes": inp.master_nodes,
            "expected_worker_nodes": inp.worker_nodes,
        },
    )

    return sub
