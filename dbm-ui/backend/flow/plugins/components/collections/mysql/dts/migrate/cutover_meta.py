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

from backend.db_meta.models import MysqlDtsInfo
from backend.db_meta.models.mysql_dts import MysqlDtsStatus
from backend.flow.plugins.components.collections.common.base_service import BaseService

logger = logging.getLogger("flow")


class MysqlDtsCutoverMetaService(BaseService):
    """cutover 成功后：写终态 Disconnected + 位点快照。"""

    def _resolve_position_snapshot(self, data, kwargs: dict) -> dict:
        """优先 kwargs.position_snapshot；否则读 trans_data.cutover_position（actuator OutputCtx）。"""
        from backend.flow.utils.mysql.dts.context import MysqlDtsTransData

        explicit = kwargs.get("position_snapshot")
        if isinstance(explicit, dict) and explicit:
            return explicit
        trans_data = data.get_one_of_inputs("trans_data")
        if trans_data is None:
            return {}
        var_name = MysqlDtsTransData.get_cutover_position_var_name()
        snap = getattr(trans_data, var_name, None)
        return dict(snap) if isinstance(snap, dict) else {}

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs") or {}
        global_data = data.get_one_of_inputs("global_data") or {}
        ticket_id = kwargs.get("ticket_id") or global_data.get("ticket_id") or global_data.get("uid")
        task_name = kwargs.get("task_name")
        position_snapshot = self._resolve_position_snapshot(data, kwargs)

        qs = MysqlDtsInfo.objects.filter(ticket_id=ticket_id)
        if task_name:
            qs = qs.filter(dts_task_id=task_name)
        infos = list(qs)
        if not infos:
            self.log_error(_("未找到待更新的 MysqlDtsInfo：ticket_id={} task_name={}").format(ticket_id, task_name))
            return False

        if not position_snapshot:
            self.log_warning(_("cutover 位点快照为空（actuator OutputCtx 未写入或解析失败）ticket_id={}").format(ticket_id))

        for info in infos:
            info.status = MysqlDtsStatus.Disconnected.value
            # 位点落在任务配置快照旁路字段：不改 schema，写入 dts_task_config_snapshot 扩展键
            snap = dict(info.dts_task_config_snapshot or {})
            snap["cutover_position"] = position_snapshot
            info.dts_task_config_snapshot = snap
            info.save(update_fields=["status", "dts_task_config_snapshot", "update_at"])
            self.log_info(_("DTS 切换完成，已写终态 Disconnected：id={} task={}").format(info.id, info.dts_task_id))
        return True


class MysqlDtsCutoverMetaComponent(Component):
    name = __name__
    code = "mysql_dts_cutover_meta"
    bound_service = MysqlDtsCutoverMetaService
