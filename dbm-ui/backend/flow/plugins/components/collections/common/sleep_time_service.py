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
import os
import re

from django.utils import timezone
from django.utils.translation import ugettext as _
from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import StaticIntervalGenerator
from pipeline.core.flow.io import StringItemSchema

from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.utils.time import str2datetime


class SleepTimerService(BaseService):
    __need_schedule__ = True
    interval = StaticIntervalGenerator(0)
    BK_TIMEMING_TICK_INTERVAL = int(os.getenv("BK_TIMEMING_TICK_INTERVAL", 60 * 60 * 24))
    seconds_regex = re.compile(r"^\d+$")

    def inputs_format(self):
        return [
            self.InputItem(
                name=_("定时时间"),
                key="bk_timing",
                type="string",
                schema=StringItemSchema(description=_("定时时间，格式为秒(s) 或 (%%Y-%%m-%%d %%H:%%M:%%S)")),
            ),
            self.InputItem(
                name=_("是否强制晚于当前时间"),
                key="force_check",
                type="bool",
                schema=StringItemSchema(description=_("用户输入日期格式时是否强制要求时间晚于当前时间，只对日期格式定时输入有效")),
            ),
        ]

    def outputs_format(self):
        return []

    def _execute(self, data, parent_data):

        global_data = data.get_one_of_inputs("global_data")
        kwargs = data.get_one_of_inputs("kwargs")

        timing = global_data["timing"]
        force_check = kwargs["force_check_timing"]

        now = datetime.datetime.now(timezone.utc)
        if self.seconds_regex.match(str(timing)):
            eta = now + datetime.timedelta(seconds=int(timing))
        else:
            eta = str2datetime(timing, aware_check=True)

        if force_check and now > eta:
            message = _("定时时间需晚于当前时间")
            self.log_error(message)
            data.outputs.ext_result = message
            return False

        self.log_info("planning time: {}".format(eta))
        data.outputs.timing_time = eta
        return True

    def _schedule(self, data, parent_data, callback_data=None):
        timing_time = data.outputs.timing_time
        now = datetime.datetime.now(timezone.utc)
        t_delta = timing_time - now

        if t_delta.total_seconds() < 1:
            self.finish_schedule()

        # 如果定时时间距离当前时间的时长大于唤醒消息的有效期，则设置下一次唤醒时间为消息有效期之内的时长
        # 避免唤醒消息超过消息的有效期被清除，导致定时节点永远不会被唤醒
        if t_delta.total_seconds() > self.BK_TIMEMING_TICK_INTERVAL > 60 * 5:
            self.interval.interval = self.BK_TIMEMING_TICK_INTERVAL - 60 * 5
            wake_time = now + datetime.timedelta(seconds=self.interval.interval)
            self.log_info("wake time: {}".format(wake_time))
            return True

        # 这里减去 0.5s 的目的是尽可能的减去 execute 执行带来的误差
        self.interval.interval = t_delta.total_seconds() - 0.5
        self.log_info("wake time: {}".format(timing_time))
        return True


class SleepTimerComponent(Component):
    name = _("定时")
    code = "sleep_timer"
    bound_service = SleepTimerService