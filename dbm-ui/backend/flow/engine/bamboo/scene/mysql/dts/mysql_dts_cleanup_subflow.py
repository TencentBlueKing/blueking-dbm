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
    hosts_to_exec_targets,
)
from backend.flow.plugins.components.collections.mysql.dts.base_shell import MysqlDtsExecShellComponent
from backend.flow.plugins.components.collections.mysql.dts.cleanup.offline_nodes import MysqlDtsOfflineNodesComponent
from backend.flow.plugins.components.collections.mysql.dts.cleanup.precheck import MysqlDtsCleanupPrecheckComponent
from backend.flow.plugins.components.collections.mysql.dts.cleanup.stop_tasks import MysqlDtsStopTasksComponent
from backend.flow.plugins.components.collections.mysql.dts.cleanup.unregister_meta import (
    MysqlDtsUnregisterClusterMetaComponent,
)
from backend.flow.utils.mysql.dts.context import DtsHostSpec, MysqlDtsCleanupSubflowInput
from backend.flow.utils.mysql.dts.script_template import render_clean_data_dir_script, render_stop_process_script


def _collect_cleanup_targets(inp: MysqlDtsCleanupSubflowInput) -> list[DtsHostSpec]:
    if inp.target_hosts:
        return inp.target_hosts
    seen = set()
    hosts = []
    for node in inp.master_nodes + inp.worker_nodes:
        ip = node["ip"]
        if ip in seen:
            continue
        seen.add(ip)
        hosts.append(DtsHostSpec(ip=ip, bk_cloud_id=node.get("bk_cloud_id", inp.bk_cloud_id)))
    return hosts


def mysql_dts_cleanup_subflow(inp: MysqlDtsCleanupSubflowInput) -> SubBuilder:
    """清理/销毁 DTS 集群。

    顺序约束（与 DTS Master API 一致）：
    1) 停任务/Source（需 Master 在线）
    2) 停本机 dm-worker / dm-master 进程（Worker 必须先离线，否则 offline_worker 报 46005）
    3) 调用 OpenAPI 注销节点注册（Master 可能已停，失败按可忽略处理）
    4) 清理目录与元数据

    迁移临时账号（dts_m_*）不在本子流程回收：账号挂在业务源/目标 MySQL 上，
    与 DESTROY 生命周期解耦；成功路径见 mysql_dts_task_clean_subflow，终止见 signal handler。
    """
    cleanup_hosts = _collect_cleanup_targets(inp)
    exec_targets = hosts_to_exec_targets(cleanup_hosts)

    sub = SubBuilder(
        root_id=inp.root_id,
        data={
            "bk_biz_id": inp.bk_biz_id,
            "bk_cloud_id": inp.bk_cloud_id,
            "uid": inp.root_id,
            "creator": inp.creator,
        },
    )

    sub.add_act(
        act_name=_("清理前置检查"),
        act_component_code=MysqlDtsCleanupPrecheckComponent.code,
        kwargs={
            "dts_cluster_id": inp.dts_cluster_id,
            "force_destroy": inp.force_destroy,
        },
    )
    sub.add_act(
        act_name=_("停止并删除 DTS 任务/Source"),
        act_component_code=MysqlDtsStopTasksComponent.code,
        kwargs={
            "master_addr": inp.master_addr,
            "bk_cloud_id": inp.bk_cloud_id,
            "force_destroy": inp.force_destroy,
        },
    )

    # 必须先停进程：Master API offline_worker 要求 Worker 已不在线（否则 46005）
    if exec_targets:
        sub.add_act(
            act_name=_("停止 DTS 进程"),
            act_component_code=MysqlDtsExecShellComponent.code,
            kwargs=build_dts_exec_shell_kwargs(exec_targets, render_stop_process_script(inp.deploy_path)),
        )

    sub.add_act(
        act_name=_("下线 DTS 节点注册信息"),
        act_component_code=MysqlDtsOfflineNodesComponent.code,
        kwargs={
            "master_addr": inp.master_addr,
            "bk_cloud_id": inp.bk_cloud_id,
            "worker_nodes": inp.worker_nodes,
            "master_nodes": inp.master_nodes,
            "force_destroy": inp.force_destroy,
            # 进程已停后 Master 可能不可达，offline API 失败可忽略
            "ignore_unreachable": True,
        },
    )

    if exec_targets and inp.clean_data_dir:
        sub.add_act(
            act_name=_("清理 DTS 部署目录"),
            act_component_code=MysqlDtsExecShellComponent.code,
            kwargs=build_dts_exec_shell_kwargs(exec_targets, render_clean_data_dir_script(inp.deploy_path)),
        )

    sub.add_act(
        act_name=_("下线 DTS 集群元数据"),
        act_component_code=MysqlDtsUnregisterClusterMetaComponent.code,
        kwargs={
            "dts_cluster_id": inp.dts_cluster_id,
            "recycle_hosts": inp.recycle_hosts,
            "target_hosts": [{"ip": h.ip, "bk_cloud_id": h.bk_cloud_id} for h in cleanup_hosts]
            if inp.target_hosts
            else None,
            "creator": inp.creator,
        },
    )
    return sub
