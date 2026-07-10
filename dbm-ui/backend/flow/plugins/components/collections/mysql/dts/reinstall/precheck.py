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

from backend.db_meta.models.mysql_dts import MysqlDtsInfo, MysqlDtsStatus
from backend.flow.plugins.components.collections.common.base_service import BaseService

logger = logging.getLogger("flow")

_ACTIVE_MIGRATE_STATUSES = [
    MysqlDtsStatus.ToDo.value,
    MysqlDtsStatus.FullOnline.value,
]


class MysqlDtsReinstallPrecheckService(BaseService):
    """重装前检查：默认拒绝仍有运行中迁移任务的集群。"""

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        dts_cluster_id = kwargs["dts_cluster_id"]
        force_reinstall = kwargs.get("force_reinstall", False)

        active_qs = MysqlDtsInfo.objects.filter(
            dts_cluster_id=dts_cluster_id,
            status__in=_ACTIVE_MIGRATE_STATUSES,
        )
        active_count = active_qs.count()
        if active_count and not force_reinstall:
            self.log_error(
                _("DTS 集群ID {} 仍有 {} 条运行中迁移记录，拒绝重装；如需强制请传 force_reinstall=true").format(dts_cluster_id, active_count)
            )
            return False
        if active_count and force_reinstall:
            self.log_warning(_("强制重装：忽略 {} 条运行中迁移记录").format(active_count))
        else:
            self.log_info(_("重装前置检查通过: dts_cluster_id={}").format(dts_cluster_id))
        return True


class MysqlDtsReinstallPrecheckComponent(Component):
    name = __name__
    code = "mysql_dts_reinstall_precheck"
    bound_service = MysqlDtsReinstallPrecheckService
