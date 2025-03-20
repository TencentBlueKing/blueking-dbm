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
from pipeline.component_framework.component import Component
from pipeline.core.flow import StaticIntervalGenerator

from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileService


class TransFileWithRetry(TransFileService):
    __need_schedule__ = True
    interval = StaticIntervalGenerator(10)

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")

        data.outputs.counter = int(kwargs["retry_seconds"] / 10) + 1  # 倒数计数器
        data.outputs.doing = False  # 单次分发job是否进行中

        return True

    def _schedule(self, data, parent_data, callback_data=None) -> bool:
        counter = data.get_one_of_outputs("counter")
        doing = data.get_one_of_outputs("doing")

        counter -= 1
        data.outputs.counter = counter

        # 倒数结束, 分发失败
        if counter < 0:
            self.finish_schedule()
            return False

        # 当前没有分发job执行, 则发起一次分发, 计数器减一
        if not doing:
            super()._execute(data=data, parent_data=parent_data)
            data.outputs.doing = True
            return True

        # 当前有分发job执行, 需要检查job执行状态
        res = super()._schedule(data=data, parent_data=parent_data)

        # res 和 is_schedule_finished 有 3 种组合
        # 1. res == True && is_schedule_finished == True: 分发成功
        # 2. res == True && is_schedule_finished == False: 分发执行中
        # 3. res == False: 分发失败

        # 1, 2 可以整合
        if res:
            return True

        # 分发失败了
        # 强制设置不终止调度
        # 设置 doing 触发下一次发起分发job
        setattr(self, self.schedule_result_attr, False)
        data.outputs.doing = False
        return True


class TransFileWithRetryComponent(Component):
    name = __name__
    code = "trans_file_with_retry"
    bound_service = TransFileWithRetry
