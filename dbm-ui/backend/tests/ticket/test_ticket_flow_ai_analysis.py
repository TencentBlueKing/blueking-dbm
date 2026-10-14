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
import ast
from pathlib import Path
from unittest.mock import MagicMock, patch

from backend import env
from backend.ticket.flow_manager.base import BaseTicketFlow

_TASKS_MODULE = "backend.dbm_aiagent.agent.services.log_analysis.tasks"


class _DummyFlow(BaseTicketFlow):
    @property
    def _status(self) -> str:
        return ""

    @property
    def _end_time(self):
        return None

    @property
    def _url(self) -> str:
        return ""

    @property
    def _summary(self) -> str:
        return ""

    @staticmethod
    def _run():
        return ""

    @property
    def _start_time(self) -> str:
        return ""


def _flow(flow_obj_id: str):
    flow_obj = MagicMock()
    flow_obj.id = 3034504
    flow_obj.flow_obj_id = flow_obj_id
    flow_obj.retry_type = ""
    return _DummyFlow(flow_obj)


@patch(f"{_TASKS_MODULE}.ticket_flow_log_ai_analysis")
@patch.object(env, "ENABLE_DBM_AI", True)
def test_run_error_dispatches_ai_analysis_with_flow_obj_id(mocked_task):
    _flow("root-abc").run_error_status_handler(RuntimeError("boom"))
    mocked_task.apply_async.assert_called_once_with(args=("root-abc",))


@patch(f"{_TASKS_MODULE}.ticket_flow_log_ai_analysis")
@patch.object(env, "ENABLE_DBM_AI", True)
def test_run_error_skips_ai_analysis_without_flow_obj_id(mocked_task):
    _flow("").run_error_status_handler(RuntimeError("boom"))
    mocked_task.apply_async.assert_not_called()


def test_worker_imports_ai_log_tasks_at_module_level():
    """任务模块必须在 worker 启动导入本文件时被加载，不能只留在函数体内。"""
    path = Path(__file__).resolve().parents[2] / "db_periodic_task/local_tasks/ai_tasks/log_analysis.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    imported = []
    for node in tree.body:
        if not isinstance(node, ast.If):
            continue
        for stmt in node.body:
            if isinstance(stmt, ast.Import):
                imported.extend(alias.name for alias in stmt.names)
    assert _TASKS_MODULE in imported
