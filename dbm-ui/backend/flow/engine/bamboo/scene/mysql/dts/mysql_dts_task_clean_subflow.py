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
from backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_delete_task_source_subflow import (
    mysql_dts_delete_task_source_subflow,
)
from backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_drop_user_subflow import mysql_dts_drop_user_subflow
from backend.flow.utils.mysql.dts.context import (
    MysqlDtsDeleteTaskSourceSubflowInput,
    MysqlDtsDropUserSubflowInput,
    MysqlDtsTaskCleanSubflowInput,
)


def mysql_dts_task_clean_subflow(inp: MysqlDtsTaskCleanSubflowInput) -> SubBuilder:
    """迁移成功路径可扩展清理子流程（流程树节点名建议 dts-task-clean）。

    挂载约定：
      - 仅挂在总流程 run_flow：mysql_dts_migrate_subflow 之后、run_pipeline 之前
      - 终止路径（REVOKED）禁止调用本子流程；终止仅同步 DROP 临时账号

    本期范围（并行）：
      1. 删除迁移临时账号（mysql_dts_drop_user_subflow，沿用 inp.ignore_errors 尽力清理）
      2. 清理本单 dts-task：delete_task → delete_source（仅显式名称列表；默认不吞错）
    """
    sub = SubBuilder(
        root_id=inp.root_id,
        data={
            "bk_biz_id": inp.bk_biz_id,
            "uid": inp.root_id,
            "creator": inp.creator,
            "created_by": inp.creator,
            "root_id": inp.root_id,
        },
    )
    drop_inp = MysqlDtsDropUserSubflowInput(
        root_id=inp.root_id,
        bk_biz_id=inp.bk_biz_id,
        dts_user=inp.dts_user,
        grant_hosts=list(inp.grant_hosts),
        grant_targets=list(inp.grant_targets),
        ignore_errors=inp.ignore_errors,
        creator=inp.creator,
    )
    delete_inp = MysqlDtsDeleteTaskSourceSubflowInput(
        root_id=inp.root_id,
        bk_biz_id=inp.bk_biz_id,
        master_addr=inp.master_addr or "",
        task_names=list(inp.task_names or []),
        source_names=list(inp.source_names or []),
        # 与 drop_user 解耦：task/source 残留会挡住后续迁移，成功路径必须失败可见
        ignore_errors=False,
        creator=inp.creator,
    )
    drop_built = mysql_dts_drop_user_subflow(drop_inp).build_sub_process(
        sub_name=_("删除 DTS 临时账号 {}").format(inp.dts_user)
    )
    delete_built = mysql_dts_delete_task_source_subflow(delete_inp).build_sub_process(sub_name=_("清理 dts-task"))
    sub.add_parallel_sub_pipeline(sub_flow_list=[drop_built, delete_built])
    return sub
