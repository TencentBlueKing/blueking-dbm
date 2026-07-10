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
import logging

from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component

from backend.components import MySQLDTSApi
from backend.flow.plugins.components.collections.common.base_service import BaseService

logger = logging.getLogger("flow")


class MysqlDtsDeleteTaskSourceService(BaseService):
    """按本单显式名称列表删除 DTS task 与 source（串行：先 task 后 source）。

    与 DESTROY ``MysqlDtsStopTasksService`` 的差异：
      - 本组件只删除入参 ``task_names`` / ``source_names``，**禁止** ``list_tasks`` / ``list_sources`` 全量扫删
      - 用于迁移成功路径 dts-task-clean，不得挂到 DESTROY cleanup
    """

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs") or {}
        trans_data = data.get_one_of_inputs("trans_data")
        master_addr = kwargs.get("master_addr") or ""
        if not master_addr and trans_data is not None and hasattr(trans_data, "migrate_context"):
            master_addr = getattr(trans_data.migrate_context, "master_addr", "") or ""
        task_names = [n for n in (kwargs.get("task_names") or []) if n]
        source_names = [n for n in (kwargs.get("source_names") or []) if n]
        # 默认不吞错：成功路径 dts-task-clean 必须感知 delete 失败；仅显式 True 时尽力清理
        ignore_errors = bool(kwargs.get("ignore_errors", False))

        if not task_names and not source_names:
            self.log_info(_("本单 task/source 名称列表为空，跳过 delete_task/delete_source"))
            return True
        if not master_addr:
            # 有待删名称却无 Master：配置/编排错误，不可当成功跳过
            self.log_error(_("master_addr 为空，无法删除本单 task/source：tasks={} sources={}").format(task_names, source_names))
            return False

        tasks_ok = self._delete_tasks(master_addr, task_names, ignore_errors)
        sources_ok = self._delete_sources(master_addr, source_names, ignore_errors)
        if ignore_errors:
            return True
        return tasks_ok and sources_ok

    def _delete_tasks(self, master_addr: str, task_names: list[str], ignore_errors: bool) -> bool:
        ok = True
        for task_name in task_names:
            try:
                MySQLDTSApi.delete_task(master_addr, task_name, force=True)
                self.log_info(_("删除本单 DTS 任务成功: {}").format(task_name))
            except Exception as exc:  # pylint: disable=broad-except
                if ignore_errors:
                    self.log_warning(_("尽力清理：删除本单任务 {} 失败: {}").format(task_name, exc))
                    continue
                self.log_error(_("删除本单 DTS 任务 {} 失败: {}").format(task_name, exc))
                ok = False
        return ok

    def _delete_sources(self, master_addr: str, source_names: list[str], ignore_errors: bool) -> bool:
        ok = True
        for source_name in source_names:
            try:
                MySQLDTSApi.delete_source(master_addr, source_name, force=True)
                self.log_info(_("删除本单 DTS Source 成功: {}").format(source_name))
            except Exception as exc:  # pylint: disable=broad-except
                if ignore_errors:
                    self.log_warning(_("尽力清理：删除本单 Source {} 失败: {}").format(source_name, exc))
                    continue
                self.log_error(_("删除本单 DTS Source {} 失败: {}").format(source_name, exc))
                ok = False
        return ok


class MysqlDtsDeleteTaskSourceComponent(Component):
    name = __name__
    code = "mysql_dts_delete_task_source"
    bound_service = MysqlDtsDeleteTaskSourceService
