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

from backend.flow.plugins.components.collections.sqlserver.exec_actuator_script import SqlserverActuatorScriptService

logger = logging.getLogger("json")


class CheckSQLServerServiceService(SqlserverActuatorScriptService):
    def _schedule(self, data, parent_data, callback_data=None) -> bool:
        result = super()._schedule(data, parent_data)
        if not result:
            return False
        # 处理判断变量
        trans_data = data.get_one_of_inputs("trans_data")
        write_payload_var = data.get_one_of_inputs("write_payload_var")
        data.outputs.is_registered = int(getattr(trans_data, write_payload_var)["is_registered"])
        return True


class CheckSQLServerServiceComponent(Component):
    name = __name__
    code = "check_sqlserver_service"
    bound_service = CheckSQLServerServiceService
