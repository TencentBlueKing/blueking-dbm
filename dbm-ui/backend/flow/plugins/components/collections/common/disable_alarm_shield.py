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
import datetime

from django.utils.translation import gettext_lazy as _
from pipeline.component_framework.component import Component

from backend import env
from backend.components import BKMonitorV3Api
from backend.db_monitor.constants import MonitorShieldType
from backend.flow.plugins.components.collections.common.base_service import BaseService


# logger = logging.getLogger("flow")
class DisableAlarmShieldService(BaseService):
    def _execute(self, data, parent_data):
        trans_data = data.get_one_of_inputs("trans_data")
        shield_id = trans_data.alarm_shield_id

        detail = BKMonitorV3Api.get_shield({"bk_biz_id": env.DBA_APP_BK_BIZ_ID, "id": shield_id})

        edit_param = {
            "bk_biz_id": env.DBA_APP_BK_BIZ_ID,
            "description": detail["description"],
            "begin_time": detail["begin_time"],
            "end_time": (datetime.datetime.now() + datetime.timedelta(minutes=15)).strftime("%Y-%m-%d %H:%M:%S"),
            "cycle_config": detail["cycle_config"],
            "shield_notice": detail["shield_notice"],
            "notice_config": detail["notice_config"],
            "id": shield_id,
        }
        # 支持策略维度的调整
        if detail["category"] == MonitorShieldType.STRATEGY.value:
            edit_param["level"] = detail["dimension_config"]["level"]

        BKMonitorV3Api.edit_shield(edit_param)

        return True


class DisableAlarmShieldComponent(Component):
    name = __name__
    code = "disable_alarm_shield"
    bound_service = DisableAlarmShieldService
    node_name = str(_("15 分钟后解除告警屏蔽"))
