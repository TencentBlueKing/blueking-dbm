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

logger = logging.getLogger("flow")


class MysqlDtsPrepareMigrateUserService(BaseService):
    """将编排期生成的临时账号与授权快照写入 migrate_context，供后续 AddUser / create_task 使用。"""

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        trans_data = data.get_one_of_inputs("trans_data")

        dts_user = kwargs.get("dts_user") or ""
        dts_password = kwargs.get("dts_password") or ""
        grant_hosts = list(kwargs.get("grant_hosts") or [])
        grant_targets = list(kwargs.get("grant_targets") or [])

        if not dts_user or not dts_password:
            self.log_error(_("dts_user/dts_password 为空，无法准备迁移临时账号"))
            return False
        if not grant_hosts:
            self.log_error(_("grant_hosts 为空，拒绝使用 %% 授权，请先确保 DTS Worker 可解析"))
            return False
        if not grant_targets:
            self.log_error(_("grant_targets 为空，未找到需要授权的迁移实例"))
            return False

        trans_data.migrate_context.dts_user = dts_user
        trans_data.migrate_context.dts_password = dts_password
        trans_data.migrate_context.grant_hosts = grant_hosts
        trans_data.migrate_context.grant_targets = grant_targets
        data.outputs["trans_data"] = trans_data
        self.log_info(
            _("准备 DTS 迁移临时账号: user={}, hosts={}, targets={}").format(dts_user, len(grant_hosts), len(grant_targets))
        )
        return True


class MysqlDtsPrepareMigrateUserComponent(Component):
    name = __name__
    code = "mysql_dts_prepare_migrate_user"
    bound_service = MysqlDtsPrepareMigrateUserService
