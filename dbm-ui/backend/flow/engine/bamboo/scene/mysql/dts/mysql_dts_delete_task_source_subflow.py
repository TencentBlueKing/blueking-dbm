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
from backend.flow.plugins.components.collections.mysql.dts.migrate.delete_task_source import (
    MysqlDtsDeleteTaskSourceComponent,
)
from backend.flow.utils.mysql.dts.context import MysqlDtsDeleteTaskSourceSubflowInput


def mysql_dts_delete_task_source_subflow(inp: MysqlDtsDeleteTaskSourceSubflowInput) -> SubBuilder:
    """本单维度清理 DTS task/source 子流程（节点名建议「清理 dts-task」）。

    内部由组件串行执行：delete_task(force) → delete_source(force)；仅删除显式名称列表。
    挂载于成功路径 mysql_dts_task_clean_subflow 内，与 drop_user 并行；终止路径不调用。
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
    sub.add_act(
        act_name=_("删除本单 DTS task/source"),
        act_component_code=MysqlDtsDeleteTaskSourceComponent.code,
        kwargs={
            "master_addr": inp.master_addr,
            "task_names": list(inp.task_names),
            "source_names": list(inp.source_names),
            "ignore_errors": inp.ignore_errors,
        },
    )
    return sub
