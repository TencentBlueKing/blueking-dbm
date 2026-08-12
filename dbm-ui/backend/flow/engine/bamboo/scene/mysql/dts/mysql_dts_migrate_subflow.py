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
from backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_ensure_cluster_subflow import (
    mysql_dts_ensure_cluster_subflow,
)
from backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_migrate_task_subflow import mysql_dts_migrate_task_subflow
from backend.flow.plugins.components.collections.mysql.dts.migrate.prepare_user import (
    MysqlDtsPrepareMigrateUserComponent,
)
from backend.flow.utils.mysql.dts.constants import MigrateTopology
from backend.flow.utils.mysql.dts.context import MysqlDtsMigrateSubflowInput
from backend.flow.utils.mysql.dts.cutover_helper import resolve_master_addr_from_plan
from backend.flow.utils.mysql.dts.migrate_credentials import (
    DtsGrantTarget,
    build_dts_add_user_parallel_acts,
    grant_targets_to_dicts,
    resolve_migrate_temp_account_for_pipeline,
)


def _ensure_cluster_sub_name(plan) -> str:
    """外层 ensure_cluster 子流程显示名：已有集群 / 部署。"""
    if plan.dts_cluster_id:
        return _("加载已有 DTS 集群")
    return _("部署 DTS 集群")


def _resolve_temp_account(inp: MysqlDtsMigrateSubflowInput):
    """优先使用外层传入的同源凭证；否则建流期内解析并生成。"""
    if inp.dts_user and inp.dts_password and inp.grant_hosts is not None and inp.grant_targets is not None:
        grant_targets = []
        for item in inp.grant_targets:
            if isinstance(item, DtsGrantTarget):
                grant_targets.append(item)
            else:
                grant_targets.append(
                    DtsGrantTarget(
                        bk_cloud_id=int(item["bk_cloud_id"]),
                        address=item["address"],
                        cluster_id=int(item.get("cluster_id") or 0),
                        major_version=item.get("major_version") or "",
                    )
                )
        return inp.dts_user, inp.dts_password, list(inp.grant_hosts), grant_targets
    if inp.dts_user or inp.dts_password or inp.grant_hosts is not None or inp.grant_targets is not None:
        # 部分传入易导致 migrate / clean 凭证不一致，拒绝静默混用
        raise ValueError(_("DTS 临时账号凭证须完整传入（dts_user/dts_password/grant_hosts/grant_targets）"))
    return resolve_migrate_temp_account_for_pipeline(inp.migrate_plan)


def mysql_dts_migrate_subflow(inp: MysqlDtsMigrateSubflowInput) -> SubBuilder:
    """迁移总入口：加载/部署 DTS 集群 → 创建临时账号 → 执行 N 个 Task。

    临时账号生命周期（本子流程不挂 drop）：
      - 成功路径：总流程末尾 mysql_dts_task_clean_subflow（节点 dts-task-clean）编排 DROP
      - 终止路径：Signal REVOKED（终止任务）由 mysql_dts_migrate_handler 仅尽力 DROP 临时账号
        （不编排完整 dts-task-clean，不做 stop_task / 注销 source）
    不要在本子流程 task 汇合后硬挂单点 drop_user 作为唯一成功路径。
    """
    plan = inp.migrate_plan
    sub = SubBuilder(
        root_id=inp.root_id,
        data={
            "bk_biz_id": inp.bk_biz_id,
            "ticket_id": inp.ticket_id,
            # Builder.add_parallel_acts / FlowNode 需要 uid；与 migrate_task_subflow 等一致取 ticket_id
            "uid": inp.ticket_id,
            "creator": inp.creator,
            # AddUserComponent 等通用组件读取 created_by；SubBuilder 的 data 即 global_data
            "created_by": inp.creator,
            "root_id": inp.root_id,
        },
    )
    sub.add_sub_pipeline(
        mysql_dts_ensure_cluster_subflow(inp).build_sub_process(sub_name=_ensure_cluster_sub_name(plan))
    )

    dts_user, dts_password, grant_hosts, grant_targets = _resolve_temp_account(inp)
    sub.add_act(
        act_name=_("准备 DTS 迁移临时账号"),
        act_component_code=MysqlDtsPrepareMigrateUserComponent.code,
        kwargs={
            "dts_user": dts_user,
            "dts_password": dts_password,
            "grant_hosts": grant_hosts,
            "grant_targets": grant_targets_to_dicts(grant_targets),
        },
    )
    sub.add_parallel_acts(
        acts_list=build_dts_add_user_parallel_acts(
            dts_user=dts_user,
            dts_password=dts_password,
            grant_hosts=grant_hosts,
            grant_targets=grant_targets,
        )
    )

    master_addr = resolve_master_addr_from_plan(plan)
    task_subflows = []
    for task_spec in plan.task_specs:
        task_sub = mysql_dts_migrate_task_subflow(
            root_id=inp.root_id,
            bk_biz_id=inp.bk_biz_id,
            ticket_id=inp.ticket_id,
            master_addr=master_addr,
            task_spec=task_spec,
            migrate_plan=plan,
            creator=inp.creator,
            dts_user=dts_user,
            dts_password=dts_password,
        )
        task_subflows.append(task_sub.build_sub_process(sub_name=_("迁移任务 {}").format(task_spec.task_name)))

    if plan.topology == MigrateTopology.ONE_TO_MANY.value and len(task_subflows) > 1:
        sub.add_parallel_sub_pipeline(task_subflows)
    else:
        for task_subflow in task_subflows:
            sub.add_sub_pipeline(task_subflow)
    return sub
