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
import math
from typing import List

from django.utils.translation import ugettext as _
from pipeline.component_framework.component import Component
from pipeline.core.flow import StaticIntervalGenerator
from pipeline.core.flow.activity import Service

import backend.flow.utils.pulsar.pulsar_context_dataclass as flow_context
from backend.flow.plugins.components.collections.common.base_service import BaseService

# 默认间隔轮询时间 设置为5min
DEFAULT_SCHEDULE_INTERVAL = 60 * 5


class BlankScheduleService(BaseService):
    """
    缩容BookKeeper 空白等待节点
    """

    __need_schedule__ = True
    # 默认5分钟轮询一次
    interval = StaticIntervalGenerator(DEFAULT_SCHEDULE_INTERVAL)

    def _execute(self, data, parent_data) -> bool:
        trans_data = data.get_one_of_inputs("trans_data")
        kwargs = data.get_one_of_inputs("kwargs")

        if trans_data is None or trans_data == "${trans_data}":
            # 表示没有加载上下文内容，则在此添加
            trans_data = getattr(flow_context, kwargs["set_trans_data_dataclass"])()
        # do nothing just return true
        return True

    def _schedule(self, data, parent_data, callback_data=None) -> bool:
        # 获取节点中定义单据和单据执行中信息
        kwargs = data.get_one_of_inputs("kwargs")
        global_data = data.get_one_of_inputs("global_data")
        trans_data = data.get_one_of_inputs("trans_data")

        if trans_data is None or trans_data == "${trans_data}":
            # 表示没有加载上下文内容，则在此添加
            trans_data = getattr(flow_context, kwargs["set_trans_data_dataclass"])()

        # 简单设计成需要等待N次，等待次数 * 等待时间 为创建集群时默认的过期时间
        # wait_migration_time 总等待时间，单位：秒
        wait_migration_time = global_data["retention_time"] * 60
        # schedule_count_acquired 需要等待的次数
        schedule_count_acquired = math.ceil(wait_migration_time / DEFAULT_SCHEDULE_INTERVAL)
        # 测试等待时间
        # schedule_count_acquired = 5
        self.log_info("calculate schedule_count_acquired is {}".format(schedule_count_acquired))

        cur_schedule_count = int(getattr(trans_data, "schedule_count"))

        self.log_info(_("successfully enter blank schedule, interval times: {}".format(cur_schedule_count)))

        if cur_schedule_count >= schedule_count_acquired:
            self.finish_schedule()
        else:
            setattr(trans_data, "schedule_count", cur_schedule_count + 1)
            data.outputs["trans_data"] = trans_data
            return True
        return True

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]

    def outputs_format(self) -> List:
        return [Service.OutputItem(name="command result", key="result", type="str")]


class BlankScheduleComponent(Component):
    name = __name__
    code = "blank_schedule"
    bound_service = BlankScheduleService
