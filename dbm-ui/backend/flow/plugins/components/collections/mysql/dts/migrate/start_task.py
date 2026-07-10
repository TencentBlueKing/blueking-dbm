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
from backend.components.mysqldtsapi.types import StartTaskRequest
from backend.flow.plugins.components.collections.common.base_service import BaseService

logger = logging.getLogger("flow")


class MysqlDtsStartTaskService(BaseService):
    """启动 DTS 迁移任务。"""

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        trans_data = data.get_one_of_inputs("trans_data")
        master_addr = kwargs.get("master_addr") or trans_data.migrate_context.master_addr
        if not master_addr:
            self.log_error(_("DTS master_addr 为空"))
            return False
        task_name = kwargs["task_name"]
        # create_task 已写入 target_host/port，启动时直接透传输出，不再二次解析
        target_host = kwargs.get("target_host") or trans_data.migrate_context.target_host or ""
        target_port = kwargs.get("target_port") or trans_data.migrate_context.target_port or 0
        cluster_type = kwargs.get("target_cluster_type") or trans_data.migrate_context.target_cluster_type or ""
        if target_host:
            self.log_info(
                _("启动 DTS 任务: task={}, 目标端={}:{}, cluster_type={}, dts_master={}").format(
                    task_name,
                    target_host,
                    target_port,
                    cluster_type,
                    master_addr,
                )
            )
        else:
            self.log_info(
                _("启动 DTS 任务: task={}, dts_master={}（目标端 host/port 未由 create_task 写入）").format(
                    task_name,
                    master_addr,
                )
            )
        source_name_list = kwargs.get("source_name_list")
        request = StartTaskRequest(source_name_list=source_name_list) if source_name_list else None
        MySQLDTSApi.start_task(master_addr, task_name, request)
        self.log_info(_("启动 DTS 任务成功: {}").format(task_name))
        return True


class MysqlDtsStartTaskComponent(Component):
    name = __name__
    code = "mysql_dts_start_task"
    bound_service = MysqlDtsStartTaskService
