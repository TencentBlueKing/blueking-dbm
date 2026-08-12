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
    build_worker_nodes,
    render_worker_config,
    resolve_deploy_path,
    worker_config_file,
)
from backend.flow.plugins.components.collections.mysql.dts.base_shell import MysqlDtsExecShellComponent
from backend.flow.plugins.components.collections.mysql.dts.deploy.verify_deploy import MysqlDtsDeployVerifyComponent
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.utils.mysql.dts.context import MysqlDtsDeployWorkerSubflowInput
from backend.flow.utils.mysql.dts.script_template import render_push_config_script, render_start_worker_script


def mysql_dts_deploy_worker_subflow(inp: MysqlDtsDeployWorkerSubflowInput) -> SubBuilder:
    """仅部署 dm-worker 节点（新建集群场景）。"""
    deploy_path = resolve_deploy_path(inp.cluster_name, inp.deploy_path)
    worker_nodes = build_worker_nodes(inp.hosts)
    trans_kwargs, pkg_name = build_dts_trans_file_kwargs(inp.hosts, inp.bk_cloud_id, inp.dts_pkg_id)

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

    for idx, host in enumerate(inp.hosts):
        node = worker_nodes[idx]
        config_file = worker_config_file(node["name"])
        exec_targets = [{"ip": host.ip, "bk_cloud_id": host.bk_cloud_id}]
        config_content = render_worker_config(
            deploy_path=deploy_path,
            node_name=node["name"],
            advertise_ip=host.ip,
            master_addr=inp.master_addr,
        )
        sub.add_act(
            act_name=_("推送 Worker 配置 {}").format(node["name"]),
            act_component_code=MysqlDtsExecShellComponent.code,
            kwargs=build_dts_exec_shell_kwargs(
                exec_targets,
                render_push_config_script(deploy_path, config_file, config_content),
            ),
        )
        sub.add_act(
            act_name=_("启动 Worker {}").format(node["name"]),
            act_component_code=MysqlDtsExecShellComponent.code,
            kwargs=build_dts_exec_shell_kwargs(
                exec_targets,
                render_start_worker_script(
                    deploy_path=deploy_path,
                    pkg_name=pkg_name,
                    config_file=config_file,
                    dts_node_name=node["name"],
                ),
            ),
        )

    sub.add_act(
        act_name=_("验收 Worker 部署"),
        act_component_code=MysqlDtsDeployVerifyComponent.code,
        kwargs={
            "master_addr": inp.master_addr,
            "bk_cloud_id": inp.bk_cloud_id,
            "verify_role": "worker",
            "expected_worker_nodes": worker_nodes,
        },
    )
    return sub
