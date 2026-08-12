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
from pipeline.component_framework.component import Component

from backend.db_meta.models import MysqlDtsCluster
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_append_worker_subflow import mysql_dts_append_worker_subflow
from backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_deploy_subflow import mysql_dts_deploy_subflow
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.mysql.dts.constants import DtsLifecycleMode
from backend.flow.utils.mysql.dts.context import MysqlDtsAppendWorkerSubflowInput, MysqlDtsMigrateSubflowInput


class MysqlDtsResolveClusterService(BaseService):
    """加载已有 DTS 集群上下文。"""

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        trans_data = data.get_one_of_inputs("trans_data")
        dts_cluster = MysqlDtsCluster.objects.get(id=kwargs["dts_cluster_id"])
        trans_data.migrate_context.dts_cluster_id = dts_cluster.id
        trans_data.migrate_context.master_addr = dts_cluster.master_addr
        trans_data.migrate_context.bk_cloud_id = dts_cluster.bk_cloud_id
        trans_data.deploy_context.master_addr = dts_cluster.master_addr
        trans_data.deploy_context.deployed_master_nodes = list(dts_cluster.master_nodes)
        trans_data.deploy_context.deployed_worker_nodes = list(dts_cluster.worker_nodes)
        self.log_info(_("加载 DTS 集群: id={}, addr={}").format(dts_cluster.id, dts_cluster.master_addr))
        return True


class MysqlDtsResolveClusterComponent(Component):
    name = __name__
    code = "mysql_dts_resolve_cluster"
    bound_service = MysqlDtsResolveClusterService


def mysql_dts_ensure_cluster_subflow(inp: MysqlDtsMigrateSubflowInput) -> SubBuilder:
    """确保迁移所需的 DTS 集群可用。"""
    plan = inp.migrate_plan
    sub = SubBuilder(
        root_id=inp.root_id,
        data={
            "bk_biz_id": inp.bk_biz_id,
            "ticket_id": inp.ticket_id,
            "uid": inp.ticket_id,
            "creator": inp.creator,
            "created_by": inp.creator,
            "root_id": inp.root_id,
        },
    )

    if plan.dts_cluster_id:
        sub.add_act(
            act_name=_("加载已有 DTS 集群"),
            act_component_code=MysqlDtsResolveClusterComponent.code,
            kwargs={"dts_cluster_id": plan.dts_cluster_id},
        )
        dts_cluster = MysqlDtsCluster.objects.get(id=plan.dts_cluster_id)
        current_workers = len(dts_cluster.worker_nodes)
        if current_workers < plan.worker_count_required:
            if not plan.deploy_subflow_inp:
                raise ValueError(
                    _("DTS 集群ID {} 当前 Worker 数 {} 少于所需 {}，且未提供 deploy_subflow 扩容参数").format(
                        dts_cluster.id, current_workers, plan.worker_count_required
                    )
                )
            append_inp = MysqlDtsAppendWorkerSubflowInput(
                root_id=inp.root_id,
                dts_cluster_id=dts_cluster.id,
                bk_biz_id=plan.bk_biz_id or inp.bk_biz_id,
                bk_cloud_id=plan.bk_cloud_id or dts_cluster.bk_cloud_id,
                master_addr=dts_cluster.master_addr,
                deploy_path=dts_cluster.deploy_path,
                existing_worker_nodes=dts_cluster.worker_nodes,
                new_worker_hosts=plan.deploy_subflow_inp.worker_hosts,
                dts_pkg_id=plan.deploy_subflow_inp.dts_pkg_id,
                creator=inp.creator,
            )
            sub.add_sub_pipeline(
                mysql_dts_append_worker_subflow(append_inp).build_sub_process(sub_name=_("追加 DTS Worker"))
            )
    elif plan.auto_deploy_dts and plan.deploy_subflow_inp:
        deploy_inp = plan.deploy_subflow_inp
        deploy_inp.root_id = inp.root_id
        deploy_inp.creator = inp.creator
        sub.add_sub_pipeline(mysql_dts_deploy_subflow(deploy_inp).build_sub_process(sub_name=_("自动部署 DTS 集群")))
    elif (
        plan.dts_lifecycle
        in (
            DtsLifecycleMode.DEPLOY_EPHEMERAL.value,
            DtsLifecycleMode.DEPLOY_PERSISTENT.value,
        )
        and plan.deploy_subflow_inp
    ):
        deploy_inp = plan.deploy_subflow_inp
        deploy_inp.root_id = inp.root_id
        deploy_inp.creator = inp.creator
        sub.add_sub_pipeline(mysql_dts_deploy_subflow(deploy_inp).build_sub_process(sub_name=_("部署 DTS 集群")))
    else:
        raise ValueError(_("未配置可用的 DTS 集群，且未开启自动部署"))

    return sub
