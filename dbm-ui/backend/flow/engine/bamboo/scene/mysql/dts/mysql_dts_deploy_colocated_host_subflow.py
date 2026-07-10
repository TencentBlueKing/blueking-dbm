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
    build_master_addr,
    build_master_nodes,
    build_worker_nodes,
    hosts_to_exec_targets,
    master_config_file,
    render_master_config,
    render_worker_config,
    resolve_deploy_path,
    worker_config_file,
)
from backend.flow.plugins.components.collections.mysql.dts.base_shell import MysqlDtsExecShellComponent
from backend.flow.plugins.components.collections.mysql.dts.deploy.verify_deploy import MysqlDtsDeployVerifyComponent
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.utils.mysql.dts.context import MysqlDtsDeployColocatedHostSubflowInput
from backend.flow.utils.mysql.dts.script_template import (
    render_push_config_script,
    render_start_master_script,
    render_start_worker_script,
)


def mysql_dts_deploy_colocated_host_subflow(inp: MysqlDtsDeployColocatedHostSubflowInput) -> SubBuilder:
    """同机部署 Master + Worker（介质仅下发一次）。"""
    deploy_path = resolve_deploy_path(inp.cluster_name, inp.deploy_path)
    host_list = [inp.host]
    exec_targets = hosts_to_exec_targets(host_list)
    master_nodes, peer_addrs = build_master_nodes(host_list, inp.master_ha)
    worker_nodes = build_worker_nodes(host_list)
    master_addr = build_master_addr(master_nodes)
    master_node = master_nodes[0]
    worker_node = worker_nodes[0]
    trans_kwargs, pkg_name = build_dts_trans_file_kwargs(host_list, inp.bk_cloud_id, inp.dts_pkg_id)
    master_config_name = master_config_file(master_node["name"])
    worker_config_name = worker_config_file(worker_node["name"])

    sub = SubBuilder(
        root_id=inp.root_id,
        data={
            "bk_biz_id": inp.bk_biz_id,
            "bk_cloud_id": inp.bk_cloud_id,
            "cluster_name": inp.cluster_name,
            "uid": inp.root_id,
        },
    )

    sub.add_act(
        act_name=_("下发 DTS 介质包"),
        act_component_code=TransFileComponent.code,
        kwargs=trans_kwargs,
    )

    master_config = render_master_config(
        deploy_path=deploy_path,
        node_name=master_node["name"],
        advertise_ip=inp.host.ip,
        master_ha=inp.master_ha,
        peer_addrs=peer_addrs if inp.master_ha else None,
    )
    sub.add_act(
        act_name=_("推送 Master 配置"),
        act_component_code=MysqlDtsExecShellComponent.code,
        kwargs=build_dts_exec_shell_kwargs(
            exec_targets,
            render_push_config_script(deploy_path, master_config_name, master_config),
        ),
    )
    sub.add_act(
        act_name=_("启动 Master"),
        act_component_code=MysqlDtsExecShellComponent.code,
        kwargs=build_dts_exec_shell_kwargs(
            exec_targets,
            render_start_master_script(
                deploy_path=deploy_path,
                pkg_name=pkg_name,
                config_file=master_config_name,
                dts_node_name=master_node["name"],
            ),
        ),
    )

    worker_config = render_worker_config(
        deploy_path=deploy_path,
        node_name=worker_node["name"],
        advertise_ip=inp.host.ip,
        master_addr=master_addr,
    )
    sub.add_act(
        act_name=_("推送 Worker 配置"),
        act_component_code=MysqlDtsExecShellComponent.code,
        kwargs=build_dts_exec_shell_kwargs(
            exec_targets,
            render_push_config_script(deploy_path, worker_config_name, worker_config),
        ),
    )
    sub.add_act(
        act_name=_("启动 Worker"),
        act_component_code=MysqlDtsExecShellComponent.code,
        kwargs=build_dts_exec_shell_kwargs(
            exec_targets,
            render_start_worker_script(
                deploy_path=deploy_path,
                pkg_name=pkg_name,
                config_file=worker_config_name,
                dts_node_name=worker_node["name"],
            ),
        ),
    )
    sub.add_act(
        act_name=_("验收同机部署"),
        act_component_code=MysqlDtsDeployVerifyComponent.code,
        kwargs={
            "master_addr": master_addr,
            "verify_role": "all",
            "expected_master_nodes": master_nodes,
            "expected_worker_nodes": worker_nodes,
        },
    )
    return sub
