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

from backend.db_meta.models import MysqlDtsCluster
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_checksum_subflow import mysql_dts_checksum_subflow
from backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_cutover_subflow import mysql_dts_cutover_subflow
from backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_wait_catchup_subflow import mysql_dts_wait_catchup_subflow
from backend.flow.utils.mysql.dts.constants import get_default_deploy_path
from backend.flow.utils.mysql.dts.context import (
    MysqlDtsChecksumSubflowInput,
    MysqlDtsCutoverSubflowInput,
    MysqlDtsWaitCatchupSubflowInput,
)
from backend.flow.utils.mysql.dts.migrate_plan import DtsMigratePlan, DtsTaskSpec


def _resolve_deploy_path(migrate_plan: DtsMigratePlan) -> str:
    if migrate_plan.dts_cluster_id:
        dts_cluster = MysqlDtsCluster.objects.filter(id=migrate_plan.dts_cluster_id).first()
        if dts_cluster and dts_cluster.deploy_path:
            return dts_cluster.deploy_path
        if dts_cluster and dts_cluster.name:
            return get_default_deploy_path(dts_cluster.name)
    if migrate_plan.deploy_subflow_inp:
        if migrate_plan.deploy_subflow_inp.deploy_path:
            return migrate_plan.deploy_subflow_inp.deploy_path
        return get_default_deploy_path(migrate_plan.deploy_subflow_inp.cluster_name)
    raise ValueError(_("无法解析 DTS deploy_path"))


def mysql_dts_catchup_cutover_subflow(
    *,
    root_id: str,
    bk_biz_id: int,
    ticket_id: int,
    master_addr: str,
    task_spec: DtsTaskSpec,
    migrate_plan: DtsMigratePlan,
    dts_user: str,
    dts_password: str,
    creator: str = "",
    need_checksum: bool = True,
) -> SubBuilder:
    """组合壳：wait_catchup → checksum（可选）→ cutover。"""
    sub = SubBuilder(
        root_id=root_id,
        data={
            "bk_biz_id": bk_biz_id,
            "uid": ticket_id,
            "ticket_id": ticket_id,
            "creator": creator,
            "created_by": creator,
            "root_id": root_id,
        },
    )
    sub.add_sub_pipeline(
        sub_flow=mysql_dts_wait_catchup_subflow(
            MysqlDtsWaitCatchupSubflowInput(
                root_id=root_id,
                bk_biz_id=bk_biz_id,
                master_addr=master_addr,
                task_name=task_spec.task_name,
                source_name_list=[s.source_name for s in task_spec.sources if s.source_name] or None,
                creator=creator,
            )
        ).build_sub_process(sub_name=_("等待 DTS 追平"))
    )
    if need_checksum:
        sub.add_sub_pipeline(
            sub_flow=mysql_dts_checksum_subflow(
                inp=MysqlDtsChecksumSubflowInput(
                    root_id=root_id,
                    bk_biz_id=bk_biz_id,
                    ticket_id=ticket_id,
                    creator=creator,
                ),
                task_spec=task_spec,
            ).build_sub_process(sub_name=_("关联单据 - MySQL 数据校验"))
        )
    # checksum 子流程排在 cutover 之前：能走到此处即视为校验已通过（或单据 skip）
    sub.add_sub_pipeline(
        sub_flow=mysql_dts_cutover_subflow(
            inp=MysqlDtsCutoverSubflowInput(
                root_id=root_id,
                bk_biz_id=bk_biz_id,
                ticket_id=ticket_id,
                master_addr=master_addr,
                task_name=task_spec.task_name,
                deploy_path=_resolve_deploy_path(migrate_plan),
                dts_cluster_id=migrate_plan.dts_cluster_id or 0,
                creator=creator,
            ),
            task_spec=task_spec,
            migrate_plan=migrate_plan,
            dts_user=dts_user,
            dts_password=dts_password,
            checksum_passed=bool(need_checksum),
            skip_checksum=not need_checksum,
        ).build_sub_process(sub_name=_("人工确认并安全切换"))
    )
    return sub
