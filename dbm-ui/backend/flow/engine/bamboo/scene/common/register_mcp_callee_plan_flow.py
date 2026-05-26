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
from typing import Dict, Optional

from django.utils.translation import gettext as _

from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.plugins.components.collections.common.register_mcp_callee_plan import RegisterMcpCalleePlanComponent


class RegisterMcpCalleePlanFlow(object):
    def __init__(self, root_id: str, data: Optional[Dict]):
        self.root_id = root_id
        self.data = data

    def register_plan_flow(self):
        """
        self.data = {
            "uid": "1234567890",
            "bk_biz_id": 123456,
            "plan_id": 123456,
            "mcp_id": "demo",
            "params": {},
            "time_window_start": "2025-09-01 00:00:00",
            "time_window_end": "2025-09-01 00:00:00",
            "max_call_count": 100,
        }
        """
        pipe = Builder(root_id=self.root_id, data=self.data)
        pipe.add_act(
            act_name=_("注册MCP被调计划"),
            act_component_code=RegisterMcpCalleePlanComponent.code,
            kwargs={},
        )
        pipe.run_pipeline()
