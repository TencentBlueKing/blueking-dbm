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
from backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_cc_standardize_subflow import (
    mysql_dts_cc_standardize_subflow,
)
from backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_deploy_worker_subflow import mysql_dts_deploy_worker_subflow
from backend.flow.engine.bamboo.scene.mysql.dts.subflow_common import add_dts_idle_check_subflow, build_worker_nodes
from backend.flow.plugins.components.collections.mysql.dts.deploy.register_meta import (
    MysqlDtsRegisterClusterMetaComponent,
)
from backend.flow.utils.mysql.dts.constants import DtsRegisterMode
from backend.flow.utils.mysql.dts.context import MysqlDtsAppendWorkerSubflowInput, MysqlDtsDeployWorkerSubflowInput


def mysql_dts_append_worker_subflow(inp: MysqlDtsAppendWorkerSubflowInput) -> SubBuilder:
    """向已有 DTS 集群追加 Worker。"""
    worker_inp = MysqlDtsDeployWorkerSubflowInput(
        root_id=inp.root_id,
        bk_biz_id=inp.bk_biz_id,
        bk_cloud_id=inp.bk_cloud_id,
        cluster_name="",
        hosts=inp.new_worker_hosts,
        master_addr=inp.master_addr,
        deploy_path=inp.deploy_path,
        dts_pkg_id=inp.dts_pkg_id,
        register_mode=DtsRegisterMode.APPEND_WORKER.value,
    )
    new_worker_nodes = build_worker_nodes(inp.new_worker_hosts, inp.existing_worker_nodes)

    sub = SubBuilder(
        root_id=inp.root_id,
        data={
            "bk_biz_id": inp.bk_biz_id,
            "bk_cloud_id": inp.bk_cloud_id,
            "uid": inp.root_id,
            "creator": inp.creator,
        },
    )
    add_dts_idle_check_subflow(
        sub,
        root_id=inp.root_id,
        bk_cloud_id=inp.bk_cloud_id,
        hosts=inp.new_worker_hosts,
    )
    sub.add_sub_pipeline(mysql_dts_deploy_worker_subflow(worker_inp).build_sub_process(sub_name=_("部署新增 Worker")))
    sub.add_act(
        act_name=_("追加 Worker 元数据"),
        act_component_code=MysqlDtsRegisterClusterMetaComponent.code,
        kwargs={
            "dts_cluster_id": inp.dts_cluster_id,
            "new_worker_nodes": new_worker_nodes,
            "creator": inp.creator,
            "register_mode": DtsRegisterMode.APPEND_WORKER.value,
        },
    )
    # 监控 act 在构建期冻结节点列表：必须传入 existing+new，不能只靠当时库快照。
    # 保留 dts_cluster_id，供 _resolve_monitor_context 在未传 master 时补齐。
    all_worker_nodes = list(inp.existing_worker_nodes or []) + new_worker_nodes
    sub.add_sub_pipeline(
        mysql_dts_cc_standardize_subflow(
            root_id=inp.root_id,
            bk_biz_id=inp.bk_biz_id,
            bk_cloud_id=inp.bk_cloud_id,
            dts_cluster_id=inp.dts_cluster_id,
            worker_nodes=all_worker_nodes,
            creator=inp.creator,
            dts_master_addr=inp.master_addr,
        ).build_sub_process(sub_name=_("DTS 标准化"))
    )
    return sub
