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

from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.mysql.dts.backup_helper import (
    resolve_task_logical_backups,
    resolved_backups_to_context_payload,
)
from backend.flow.utils.mysql.dts.constants import DEFAULT_MYLOADER_PATH
from backend.flow.utils.mysql.dts.migrate_helper import apply_myloader_dirs_to_sources
from backend.flow.utils.mysql.dts.migrate_plan import dts_migrate_plan_from_dict, dts_task_spec_from_dict

logger = logging.getLogger("flow")


class MysqlDtsResolveLogicalBackupService(BaseService):
    """解析各 source 的逻辑全备，写入 migrate_context 并回写 myloader_dir。"""

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        trans_data = data.get_one_of_inputs("trans_data")
        task_spec = dts_task_spec_from_dict(kwargs["task_spec"])
        migrate_plan = dts_migrate_plan_from_dict(kwargs["migrate_plan"])
        root_id = kwargs.get("root_id") or ""
        if not root_id:
            self.log_error(_("root_id 为空，无法组装 myloader 备份目录"))
            return False

        try:
            # 优先使用编排阶段预解析结果，避免重复查备份；缺失时再现场解析
            pre_resolved = kwargs.get("resolved_backups") or []
            if pre_resolved:
                dirs = {item["source_name"]: item["myloader_dir"] for item in pre_resolved}
                backups = {item["source_name"]: item for item in pre_resolved}
                myloader_path = kwargs.get("myloader_path") or DEFAULT_MYLOADER_PATH
            else:
                resolved_list = resolve_task_logical_backups(
                    root_id=root_id,
                    migrate_plan=migrate_plan,
                    sources=task_spec.sources,
                    deadlines_days=int(kwargs.get("deadlines_days") or 7),
                )
                dirs, backups, myloader_path = resolved_backups_to_context_payload(resolved_list)

            apply_myloader_dirs_to_sources(task_spec, dirs)
            for src in task_spec.sources:
                if src.myloader and not src.myloader.myloader_path:
                    src.myloader.myloader_path = myloader_path

            if trans_data is not None and hasattr(trans_data, "migrate_context"):
                trans_data.migrate_context.myloader_dirs = dirs
                trans_data.migrate_context.myloader_backup_by_source = backups
                trans_data.migrate_context.myloader_path = myloader_path
                data.outputs["trans_data"] = trans_data

            self.log_info(_("解析逻辑全备成功: sources={}, myloader_path={}").format(list(dirs.keys()), myloader_path))
            return True
        except Exception as exc:  # pylint: disable=broad-except
            self.log_error(_("解析逻辑全备失败: {}").format(str(exc)))
            return False


class MysqlDtsResolveLogicalBackupComponent(Component):
    name = __name__
    code = "mysql_dts_resolve_logical_backup"
    bound_service = MysqlDtsResolveLogicalBackupService
