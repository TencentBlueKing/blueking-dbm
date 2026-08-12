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
from backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_deploy_colocated_host_subflow import (
    mysql_dts_deploy_colocated_host_subflow,
)
from backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_deploy_master_subflow import mysql_dts_deploy_master_subflow
from backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_deploy_worker_subflow import mysql_dts_deploy_worker_subflow
from backend.flow.engine.bamboo.scene.mysql.dts.subflow_common import (
    build_master_addr,
    build_master_nodes,
    build_worker_nodes,
    resolve_deploy_path,
)
from backend.flow.plugins.components.collections.mysql.dts.deploy.register_meta import (
    MysqlDtsRegisterClusterMetaComponent,
)
from backend.flow.plugins.components.collections.mysql.dts.deploy.verify_deploy import MysqlDtsDeployVerifyComponent
from backend.flow.utils.mysql.dts.constants import DtsRegisterMode
from backend.flow.utils.mysql.dts.context import (
    MysqlDtsDeployColocatedHostSubflowInput,
    MysqlDtsDeployMasterSubflowInput,
    MysqlDtsDeploySubflowInput,
    MysqlDtsDeployWorkerSubflowInput,
)
from backend.flow.utils.mysql.dts.deploy_helper import group_deploy_hosts


def mysql_dts_deploy_subflow(inp: MysqlDtsDeploySubflowInput) -> SubBuilder:
    """完整 DTS 集群部署。"""
    deploy_path = resolve_deploy_path(inp.cluster_name, inp.deploy_path)
    host_plans = group_deploy_hosts(inp.master_hosts, inp.worker_hosts)

    sub = SubBuilder(
        root_id=inp.root_id,
        data={
            "bk_biz_id": inp.bk_biz_id,
            "bk_cloud_id": inp.bk_cloud_id,
            "cluster_name": inp.cluster_name,
            "uid": inp.root_id,
            "creator": inp.creator,
        },
    )

    all_master_nodes = []
    all_worker_nodes = []

    for host in host_plans.colocated_hosts:
        colocated_inp = MysqlDtsDeployColocatedHostSubflowInput(
            root_id=inp.root_id,
            bk_biz_id=inp.bk_biz_id,
            bk_cloud_id=inp.bk_cloud_id,
            cluster_name=inp.cluster_name,
            host=host,
            deploy_path=deploy_path,
            master_ha=inp.master_ha,
            dts_pkg_id=inp.dts_pkg_id,
        )
        sub.add_sub_pipeline(
            mysql_dts_deploy_colocated_host_subflow(colocated_inp).build_sub_process(
                sub_name=_("同机部署 {}").format(host.ip)
            )
        )
        master_nodes, _unused = build_master_nodes([host], inp.master_ha)
        worker_nodes = build_worker_nodes([host])
        all_master_nodes.extend(master_nodes)
        all_worker_nodes.extend(worker_nodes)

    if host_plans.master_only_hosts:
        master_inp = MysqlDtsDeployMasterSubflowInput(
            root_id=inp.root_id,
            bk_biz_id=inp.bk_biz_id,
            bk_cloud_id=inp.bk_cloud_id,
            cluster_name=inp.cluster_name,
            hosts=host_plans.master_only_hosts,
            deploy_path=deploy_path,
            master_ha=inp.master_ha,
            dts_pkg_id=inp.dts_pkg_id,
        )
        sub.add_sub_pipeline(mysql_dts_deploy_master_subflow(master_inp).build_sub_process(sub_name=_("部署 Master")))
        master_nodes, _unused = build_master_nodes(host_plans.master_only_hosts, inp.master_ha)
        all_master_nodes.extend(master_nodes)

    master_addr = build_master_addr(all_master_nodes)

    if host_plans.worker_only_hosts:
        worker_inp = MysqlDtsDeployWorkerSubflowInput(
            root_id=inp.root_id,
            bk_biz_id=inp.bk_biz_id,
            bk_cloud_id=inp.bk_cloud_id,
            cluster_name=inp.cluster_name,
            hosts=host_plans.worker_only_hosts,
            master_addr=master_addr,
            deploy_path=deploy_path,
            dts_pkg_id=inp.dts_pkg_id,
        )
        sub.add_sub_pipeline(mysql_dts_deploy_worker_subflow(worker_inp).build_sub_process(sub_name=_("部署 Worker")))
        all_worker_nodes.extend(build_worker_nodes(host_plans.worker_only_hosts))

    sub.add_act(
        act_name=_("全量验收 DTS 集群"),
        act_component_code=MysqlDtsDeployVerifyComponent.code,
        kwargs={
            "master_addr": master_addr,
            "bk_cloud_id": inp.bk_cloud_id,
            "verify_role": "all",
            "expected_master_nodes": all_master_nodes,
            "expected_worker_nodes": all_worker_nodes,
        },
    )
    sub.add_act(
        act_name=_("注册 DTS 集群元数据"),
        act_component_code=MysqlDtsRegisterClusterMetaComponent.code,
        kwargs={
            "bk_biz_id": inp.bk_biz_id,
            "bk_cloud_id": inp.bk_cloud_id,
            "cluster_name": inp.cluster_name,
            "master_nodes": all_master_nodes,
            "worker_nodes": all_worker_nodes,
            "master_addr": master_addr,
            "deploy_path": deploy_path,
            "creator": inp.creator,
            "register_mode": DtsRegisterMode.CREATE.value,
        },
    )
    return sub
