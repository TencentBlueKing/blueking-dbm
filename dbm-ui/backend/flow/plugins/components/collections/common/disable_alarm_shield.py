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
from django.conf import settings
from pipeline.component_framework.component import Component

from backend import env
from backend.components import BKMonitorV3Api
from backend.flow.plugins.components.collections.common.sleep_time_service import SleepTimerService

# logger = logging.getLogger("flow")


class DisableAlarmShieldService(SleepTimerService):
    def _execute(self, data, parent_data):
        kwargs = data.get_one_of_inputs("kwargs")

        kwargs["timing"] = settings.DISABLE_ALARM_SHIELD_DELAY
        kwargs["force_check_timing"] = True

        data.outputs.kwargs = kwargs

        return super()._execute(data=data, parent_data=parent_data)

    def _schedule(self, data, parent_data, callback_data=None):
        res = super()._schedule(data=data, parent_data=parent_data, callback_data=callback_data)
        if res and self.is_schedule_finished():
            trans_data = data.get_one_of_inputs("trans_data")
            shield_id = trans_data.alarm_shield_id
            self.log_info(f"to delete alarm shield {shield_id}")
            BKMonitorV3Api.disable_shield({"bk_biz_id": env.DBA_APP_BK_BIZ_ID, "id": shield_id})

        return True


class DisableAlarmShieldComponent(Component):
    name = __name__
    code = "disable_alarm_shield"
    bound_service = DisableAlarmShieldService
