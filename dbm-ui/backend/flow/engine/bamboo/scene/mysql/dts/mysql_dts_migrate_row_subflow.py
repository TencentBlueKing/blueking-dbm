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
from backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_migrate_subflow import mysql_dts_migrate_subflow
from backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_task_clean_subflow import mysql_dts_task_clean_subflow
from backend.flow.utils.mysql.dts.constants import FullLoadEngine
from backend.flow.utils.mysql.dts.context import MysqlDtsMigrateSubflowInput, MysqlDtsTaskCleanSubflowInput
from backend.flow.utils.mysql.dts.cutover_helper import resolve_master_addr_from_plan
from backend.flow.utils.mysql.dts.migrate_credentials import (
    grant_targets_to_dicts,
    resolve_migrate_temp_account_for_pipeline,
)
from backend.flow.utils.mysql.dts.migrate_helper import build_ticket_dts_clean_names, plan_deploy_cluster_name
from backend.flow.utils.mysql.dts.migrate_plan import DtsMigratePlan


def build_migrate_row_sub_name(plan) -> str:
    """画布行节点名：{src_id} 迁移-> {dst_id}。"""
    src_ids: list[int] = []
    dst_ids: list[int] = []
    seen_src: set[int] = set()
    seen_dst: set[int] = set()
    for spec in getattr(plan, "task_specs", None) or []:
        for source in getattr(spec, "sources", None) or []:
            cid = getattr(source, "cluster_id", None)
            if cid and cid not in seen_src:
                seen_src.add(cid)
                src_ids.append(int(cid))
        dst = getattr(spec, "target_cluster_id", None)
        if dst and dst not in seen_dst:
            seen_dst.add(dst)
            dst_ids.append(int(dst))
    src_label = ",".join(str(i) for i in src_ids) or "-"
    dst_label = ",".join(str(i) for i in dst_ids) or "-"
    return _("{} 迁移-> {}").format(src_label, dst_label)


def build_migrate_row_subflow(
    *,
    root_id: str,
    bk_biz_id: int,
    ticket_id: int,
    migrate_plan: DtsMigratePlan,
    creator: str,
    sub_name: str,
    row_key: str = "",
):
    """一行独立子流程：migrate + 该行 dts-task-clean。

    每行自建临时账号，串行挂在本行 SubBuilder 内，避免并行行共用 migrate_context。
    """
    dts_user, dts_password, grant_hosts, grant_targets = resolve_migrate_temp_account_for_pipeline(migrate_plan)
    grant_target_dicts = grant_targets_to_dicts(grant_targets)
    row = SubBuilder(
        root_id=root_id,
        data={
            "bk_biz_id": bk_biz_id,
            "ticket_id": ticket_id,
            "uid": ticket_id or root_id,
            "creator": creator,
            "created_by": creator,
            "root_id": root_id,
            "row_key": row_key,
            "dts_task_ids": [s.task_name for s in migrate_plan.task_specs if getattr(s, "task_name", None)],
        },
    )
    migrate_inp = MysqlDtsMigrateSubflowInput(
        root_id=root_id,
        bk_biz_id=bk_biz_id,
        ticket_id=ticket_id,
        migrate_plan=migrate_plan,
        creator=creator,
        dts_user=dts_user,
        dts_password=dts_password,
        grant_hosts=grant_hosts,
        grant_targets=grant_targets,
    )
    row.add_sub_pipeline(mysql_dts_migrate_subflow(migrate_inp).build_sub_process(sub_name=_("数据迁移")))

    task_names, source_names = build_ticket_dts_clean_names(migrate_plan)
    task_cfg = getattr(migrate_plan, "dts_task_config", None)
    task_mode = (getattr(task_cfg, "task_mode", None) or "all") if task_cfg is not None else "all"
    full_load_engine = (
        (getattr(task_cfg, "full_load_engine", None) or FullLoadEngine.BUILTIN.value)
        if task_cfg is not None
        else FullLoadEngine.BUILTIN.value
    )
    clean_inp = MysqlDtsTaskCleanSubflowInput(
        root_id=root_id,
        bk_biz_id=bk_biz_id,
        dts_user=dts_user,
        grant_hosts=grant_hosts,
        grant_targets=grant_target_dicts,
        ignore_errors=True,
        creator=creator,
        master_addr=resolve_master_addr_from_plan(migrate_plan),
        bk_cloud_id=int(migrate_plan.bk_cloud_id or 0),
        task_names=task_names,
        source_names=source_names,
        dts_cluster_id=getattr(migrate_plan, "dts_cluster_id", None) or None,
        cluster_name=plan_deploy_cluster_name(migrate_plan),
        task_mode=task_mode,
        full_load_engine=full_load_engine,
    )
    row.add_sub_pipeline(mysql_dts_task_clean_subflow(clean_inp).build_sub_process(sub_name=_("dts-task-clean")))
    return row.build_sub_process(sub_name=sub_name)


def build_parallel_migrate_row_pipelines(
    *,
    pipeline,
    root_id: str,
    data: dict,
    migrate_plans: list,
    migrate_type: str | None = None,
):
    """按 plan 列表并行挂行子流程。

    migrate_type 传入则覆盖各 plan；否则保留 plan.migrate_type（rename 混行）。
    """
    creator = data.get("created_by", "")
    bk_biz_id = int(data["bk_biz_id"])
    ticket_id = int(data.get("ticket_id", 0) or 0)
    row_subs = []
    for idx, plan in enumerate(migrate_plans):
        if migrate_type:
            plan.migrate_type = migrate_type
        row_subs.append(
            build_migrate_row_subflow(
                root_id=root_id,
                bk_biz_id=bk_biz_id,
                ticket_id=ticket_id,
                migrate_plan=plan,
                creator=creator,
                sub_name=build_migrate_row_sub_name(plan),
                row_key=f"row-{idx}",
            )
        )
    pipeline.add_parallel_sub_pipeline(sub_flow_list=row_subs)
