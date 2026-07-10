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
from backend.flow.utils.mysql.dts.constants import DEFAULT_MYLOADER_PATH
from backend.flow.utils.mysql.dts.migrate_helper import apply_myloader_dirs_to_sources, build_dts_task_request
from backend.flow.utils.mysql.dts.migrate_plan import DtsTaskSpec, dts_migrate_plan_from_dict, dts_task_spec_from_dict

logger = logging.getLogger("flow")


def _apply_myloader_context_to_task_spec(task_spec: DtsTaskSpec, migrate_context) -> None:
    """将 migrate_context 中的 myloader 目录/路径回写到 task_spec（运行时）。"""
    dirs = getattr(migrate_context, "myloader_dirs", None) or {}
    if dirs:
        apply_myloader_dirs_to_sources(task_spec, dirs)
    path = getattr(migrate_context, "myloader_path", "") or DEFAULT_MYLOADER_PATH
    for src in task_spec.sources:
        if src.myloader is None:
            continue
        if not src.myloader.myloader_path:
            src.myloader.myloader_path = path


class MysqlDtsCreateTaskService(BaseService):
    """创建 DTS 迁移任务。"""

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        trans_data = data.get_one_of_inputs("trans_data")
        master_addr = kwargs.get("master_addr") or trans_data.migrate_context.master_addr
        if not master_addr:
            self.log_error(_("DTS master_addr 为空"))
            return False
        plan = dts_migrate_plan_from_dict(kwargs["migrate_plan"])
        task_spec = dts_task_spec_from_dict(kwargs["task_spec"])
        dts_user = trans_data.migrate_context.dts_user
        dts_password = trans_data.migrate_context.dts_password
        if not dts_user or not dts_password:
            self.log_error(_("DTS 迁移临时账号未创建，请先执行 prepare_user / AddUser 步骤"))
            return False
        _apply_myloader_context_to_task_spec(task_spec, trans_data.migrate_context)
        request = build_dts_task_request(
            plan,
            task_spec,
            user=dts_user,
            password=dts_password,
        )
        target_cfg = request.task.target_config
        if target_cfg and target_cfg.host:
            trans_data.migrate_context.target_host = target_cfg.host
            trans_data.migrate_context.target_port = int(target_cfg.port or 0)
            trans_data.migrate_context.target_cluster_type = target_cfg.cluster_type or ""
            self.log_info(
                _("创建 DTS 任务目标端: {}:{}, cluster_type={}").format(
                    target_cfg.host,
                    target_cfg.port,
                    target_cfg.cluster_type or "",
                )
            )
        resp = MySQLDTSApi.create_task(master_addr, request)
        task_name = task_spec.task_name
        # 契约：请求名即最终名；Master 改写会导致 start/poll/meta/ToDo 预占键全部错位
        returned_name = (resp.task or {}).get("name") if resp.task else None
        if returned_name and returned_name != task_name:
            self.log_error(_("创建 DTS 任务返回名与请求名不一致：请求={} 返回={}（拒绝静默改名）").format(task_name, returned_name))
            return False
        data.outputs.task_name = task_name
        data.outputs.check_result = resp.check_result
        data.outputs["trans_data"] = trans_data
        self.log_info(_("创建 DTS 任务成功: {}").format(task_name))
        return True


class MysqlDtsCreateTaskComponent(Component):
    name = __name__
    code = "mysql_dts_create_task"
    bound_service = MysqlDtsCreateTaskService
