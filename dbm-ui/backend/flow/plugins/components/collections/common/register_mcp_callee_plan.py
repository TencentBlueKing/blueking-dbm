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
from django.utils.translation import gettext_lazy as _
from pipeline.component_framework.component import Component

from backend import env
from backend.flow.plugins.components.collections.common.base_service import BaseService


class RegisterMcpCalleePlanService(BaseService):
    def _execute(self, data, parent_data):
        if not env.ENABLE_DBM_AI:
            return True

        from backend.dbm_aiagent.models.mcp_callee_plan import McpCalleePlan, McpCalleePlanStatus

        global_data = data.get_one_of_inputs("global_data")

        plan_id = global_data.get("plan_id")
        self.log_info("register_mcp_callee_plan plan_id: {}".format(plan_id))

        plan_obj = McpCalleePlan.objects.get(id=plan_id)
        plan_obj.status = McpCalleePlanStatus.APPROVED
        plan_obj.save()

        return True


class RegisterMcpCalleePlanComponent(Component):
    name = _("注册mcp callee plan")
    code = "register_mcp_callee_plan"
    bound_service = RegisterMcpCalleePlanService
