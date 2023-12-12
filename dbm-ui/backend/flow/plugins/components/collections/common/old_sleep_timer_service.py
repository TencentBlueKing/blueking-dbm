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

from django.utils import translation
from django.utils.translation import ugettext as _
from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import StaticIntervalGenerator
from pipeline.core.flow.io import StringItemSchema

from backend.flow.plugins.components.collections.common.base_service import BaseService


class DeprecatedSleepTimerService(BaseService):
    # todo: Deprecated, 准备移除

    __need_schedule__ = True
    interval = StaticIntervalGenerator(0)
    BK_TIMEMING_TICK_INTERVAL = int(os.getenv("BK_TIMEMING_TICK_INTERVAL", 60 * 60 * 24))

    #  匹配年月日 时分秒 正则 yyyy-MM-dd HH:mm:ss
    date_regex = re.compile(
        r"%s %s"
        % (
            r"^(((\d{3}[1-9]|\d{2}[1-9]\d{1}|\d{1}[1-9]\d{2}|[1-9]\d{3}))|"
            r"(29/02/((\d{2})(0[48]|[2468][048]|[13579][26])|((0[48]|[2468][048]|[3579][26])00))))-"
            r"((0[13578]|1[02])-((0[1-9]|[12]\d|3[01]))|"
            r"((0[469]|11)-(0[1-9]|[12]\d|30))|(02)-(0[1-9]|[1]\d|2[0-8]))",
            r"((0|[1])\d|2[0-3]):(0|[1-5])\d:(0|[1-5])\d$",
        )
    )

    seconds_regex = re.compile(r"^\d+$")

    # 匹配 +08:00, 08:00, -08:00, 00:00,
    timezone_regex = re.compile(r"[+-]?\d+:00$")

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

        if parent_data.get_one_of_inputs("language"):
            translation.activate(parent_data.get_one_of_inputs("language"))

        global_data = data.get_one_of_inputs("global_data")
        # trans_data = data.get_one_of_inputs("trans_data")
        kwargs = data.get_one_of_inputs("kwargs")

        timing = global_data["timing"]
        # cluster_timezone = trans_data.cluster_timezone
        cluster_timezone = global_data["time_zone"]
        if len(cluster_timezone) == 0:
            timezone_hour = 8  # 没有获取到时区，默认东八区
        elif self.timezone_regex.match(str(cluster_timezone)):
            timezone_hour = int(cluster_timezone.split(":")[0])
        else:
            message = _("输入参数%s不符合【时区(+08:00、-08:00)】格式") % cluster_timezone
            self.log_error(message)
            data.outputs.ext_result = message
            return False

        tz_input = datetime.timezone(datetime.timedelta(hours=timezone_hour))
        force_check = kwargs["force_check_timing"]

        # 传入的定时timing以及cluster时区信息。获取cluster时区的当前时间。
        now = datetime.datetime.now(tz_input)

        if self.date_regex.match(str(timing)):
            eta = datetime.datetime.strptime(timing, "%Y-%m-%d %H:%M:%S").replace(tzinfo=tz_input)

            if force_check and now > eta:
                message = _("定时时间需晚于当前时间")
                self.log_error(message)
                data.outputs.ext_result = message
                return False
        elif self.seconds_regex.match(str(timing)):
            #  如果写成+号 可以输入无限长，或考虑前端修改
            eta = now + datetime.timedelta(seconds=int(timing))
        else:
            message = _("输入参数%s不符合【秒(s) 或 时间(%%Y-%%m-%%d %%H:%%M:%%S)】格式") % timing
            self.log_error(message)
            data.outputs.ext_result = message
            return False

        self.log_info("planning time: {}".format(eta))
        data.outputs.timing_time = eta
        data.outputs.tz_input = tz_input
        return True

    def _schedule(self, data, parent_data, callback_data=None):
        timing_time = data.outputs.timing_time
        tz_input = data.outputs.tz_input

        now = datetime.datetime.now(tz_input)
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


class DeprecatedSleepTimerComponent(Component):
    # todo: Deprecated, 准备移除

    name = _("定时")
    code = "deprecated_sleep_timer"
    bound_service = DeprecatedSleepTimerService
