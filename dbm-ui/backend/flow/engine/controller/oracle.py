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
from backend.flow.engine.bamboo.scene.oracle.oracle_exec_script import OracleExecuteScriptFlow
from backend.flow.engine.controller.base import BaseController


class OracleController(BaseController):
    """
    oracle相关控制器
    """

    def multi_oracle_execute_script(self):
        """
        执行脚本
        """

        flow = OracleExecuteScriptFlow(root_id=self.root_id, data=self.ticket_data)
        flow.multi_oracle_execute_script_flow()
