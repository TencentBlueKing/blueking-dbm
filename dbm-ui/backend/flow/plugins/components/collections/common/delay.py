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

from django.utils import timezone
from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import StaticIntervalGenerator
from pipeline.core.flow.io import StringItemSchema

from backend.flow.plugins.components.collections.common.base_service import BaseService


class DelayService(BaseService):
    """
    延迟节点，延迟指定秒数后自动继续执行
    """

    __need_schedule__ = True
    interval = StaticIntervalGenerator(1)

    def _execute(self, data, parent_data):
        self.log_info(_("execute DelayService"))
        kwargs = data.get_one_of_inputs("kwargs")
        global_data = data.get_one_of_inputs("global_data")

        # 获取延迟秒数，优先从 kwargs 获取，其次从 global_data 获取
        if "delay_seconds" in kwargs:
            delay_seconds = kwargs["delay_seconds"]
        elif "delay_seconds" in global_data:
            delay_seconds = global_data["delay_seconds"]
        else:
            error_msg = _("未找到延迟秒数参数 delay_seconds")
            self.log_error(error_msg)
            return False

        # 验证延迟秒数
        try:
            delay_seconds = int(delay_seconds)
            if delay_seconds < 0:
                error_msg = _("延迟秒数不能为负数")
                self.log_error(error_msg)
                return False
        except (ValueError, TypeError):
            error_msg = _("延迟秒数必须是整数: {}").format(delay_seconds)
            self.log_error(error_msg)
            return False

        # 记录开始时间和目标时间
        start_time = datetime.datetime.now(timezone.utc)
        target_time = start_time + datetime.timedelta(seconds=delay_seconds)

        self.log_info(_("延迟节点开始，延迟 {} 秒，预计完成时间: {}").format(delay_seconds, target_time))
        data.outputs.start_time = start_time
        data.outputs.target_time = target_time
        data.outputs.delay_seconds = delay_seconds

        return True

    def _schedule(self, data, parent_data, callback_data=None):
        target_time = data.outputs.target_time
        now = datetime.datetime.now(timezone.utc)
        remaining_seconds = (target_time - now).total_seconds()

        # 如果已经过了目标时间，完成调度
        if remaining_seconds <= 0:
            elapsed_seconds = (now - data.outputs.start_time).total_seconds()
            self.log_info(_("延迟节点完成，实际延迟 {} 秒").format(int(elapsed_seconds)))
            self.finish_schedule()
            return True

        # 如果剩余时间大于当前调度间隔，设置下一次调度间隔
        # 避免过于频繁的调度检查
        if remaining_seconds > self.interval.interval:
            # 设置调度间隔为剩余时间的一半，但不超过60秒
            next_interval = min(remaining_seconds / 2, 60)
            self.interval.interval = max(int(next_interval), 1)
        else:
            # 剩余时间小于等于当前间隔，设置为剩余时间
            self.interval.interval = max(int(remaining_seconds), 1)

        self.log_info(_("延迟节点等待中，剩余 {} 秒").format(int(remaining_seconds)))
        return True

    def inputs_format(self):
        return [
            self.InputItem(
                name=_("延迟秒数"),
                key="delay_seconds",
                type="string",
                schema=StringItemSchema(description=_("延迟的秒数，必须为非负整数")),
            )
        ]

    def outputs_format(self):
        return [
            self.OutputItem(
                name=_("开始时间"),
                key="start_time",
                type="string",
                schema=StringItemSchema(description=_("延迟节点开始执行的时间")),
            ),
            self.OutputItem(
                name=_("目标时间"),
                key="target_time",
                type="string",
                schema=StringItemSchema(description=_("延迟节点预计完成的时间")),
            ),
            self.OutputItem(
                name=_("延迟秒数"),
                key="delay_seconds",
                type="string",
                schema=StringItemSchema(description=_("配置的延迟秒数")),
            ),
        ]


class DelayComponent(Component):
    name = _("延迟")
    code = "delay"
    bound_service = DelayService
