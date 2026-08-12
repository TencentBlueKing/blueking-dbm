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


class MysqlDtsStopTasksService(BaseService):
    """停止并删除 DTS Master 上的 Task / Source。"""

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        master_addr = kwargs.get("master_addr")
        bk_cloud_id = kwargs.get("bk_cloud_id")
        force_destroy = kwargs.get("force_destroy", False)
        if not master_addr:
            self.log_warning(_("master_addr 为空，跳过 stop_task/delete_source"))
            return True
        if bk_cloud_id is None:
            self.log_error(_("bk_cloud_id 为空，无法 stop_task/delete_source"))
            return False
        bk_cloud_id = int(bk_cloud_id)

        try:
            tasks_resp = MySQLDTSApi.list_tasks(master_addr, with_status=False, bk_cloud_id=bk_cloud_id)
            task_names = [item.name for item in (tasks_resp.data or []) if getattr(item, "name", None)]
        except Exception as exc:  # pylint: disable=broad-except
            if force_destroy:
                self.log_warning(_("强制清理：list_tasks 失败，继续: {}").format(exc))
                task_names = []
            else:
                self.log_error(_("list_tasks 失败: {}").format(exc))
                return False

        for task_name in task_names:
            try:
                MySQLDTSApi.stop_task(master_addr, task_name, bk_cloud_id=bk_cloud_id)
                self.log_info(_("停止 DTS 任务成功: {}").format(task_name))
            except Exception as exc:  # pylint: disable=broad-except
                if force_destroy:
                    self.log_warning(_("强制清理：停止任务 {} 失败: {}").format(task_name, exc))
                else:
                    self.log_error(_("停止 DTS 任务 {} 失败: {}").format(task_name, exc))
                    return False
            try:
                MySQLDTSApi.delete_task(master_addr, task_name, force=True, bk_cloud_id=bk_cloud_id)
                self.log_info(_("删除 DTS 任务成功: {}").format(task_name))
            except Exception as exc:  # pylint: disable=broad-except
                if force_destroy:
                    self.log_warning(_("强制清理：删除任务 {} 失败: {}").format(task_name, exc))
                else:
                    self.log_error(_("删除 DTS 任务 {} 失败: {}").format(task_name, exc))
                    return False

        try:
            sources_resp = MySQLDTSApi.list_sources(master_addr, bk_cloud_id=bk_cloud_id)
            source_names = [item.source_name for item in (sources_resp.data or []) if item.source_name]
        except Exception as exc:  # pylint: disable=broad-except
            if force_destroy:
                self.log_warning(_("强制清理：list_sources 失败，继续: {}").format(exc))
                source_names = []
            else:
                self.log_error(_("list_sources 失败: {}").format(exc))
                return False

        for source_name in source_names:
            try:
                MySQLDTSApi.delete_source(master_addr, source_name, force=True, bk_cloud_id=bk_cloud_id)
                self.log_info(_("删除 DTS Source 成功: {}").format(source_name))
            except Exception as exc:  # pylint: disable=broad-except
                if force_destroy:
                    self.log_warning(_("强制清理：删除 Source {} 失败: {}").format(source_name, exc))
                else:
                    self.log_error(_("删除 DTS Source {} 失败: {}").format(source_name, exc))
                    return False
        return True


class MysqlDtsStopTasksComponent(Component):
    name = __name__
    code = "mysql_dts_stop_tasks"
    bound_service = MysqlDtsStopTasksService
