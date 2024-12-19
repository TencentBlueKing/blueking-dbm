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

from pipeline.component_framework.component import Component

from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptService

logger = logging.getLogger("flow")


class ExecSwitchActForSourceService(ExecuteDBActuatorScriptService):
    """
    处理执行切换的活动节点，并判断切换结果返回不同的状态码，作为下一个条件的判断流向
    目前状态码分为以下情况：
    0: 代表切换正常
    1: 代表切换异常
    """

    def _schedule(self, data, parent_data, callback_data=None):
        code = super()._schedule(data, parent_data, callback_data)
        if code:
            # 代表执行切换正常
            data.outputs.switch_code = 0
            return True
        else:
            # 代表执行切换异常
            data.outputs.switch_code = 1
            return False


class ExecSwitchActForSourceComponent(Component):
    name = __name__
    code = "exec_switch_act_for_source"
    bound_service = ExecSwitchActForSourceService
