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
from django.utils.translation import ugettext as _
from pipeline.component_framework.component import Component

from backend.components import DRSApi
from backend.flow.plugins.components.collections.common.base_service import BaseService


class ResetSlaveViaDRSService(BaseService):
    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")

        self.log_info(_("传入参数:{}").format(kwargs))
        res = DRSApi.rpc(
            {
                "addresses": [kwargs["address"]],
                "cmds": ["reset slave"],
                "force": False,
                "bk_cloud_id": kwargs["bk_cloud_id"],
            }
        )

        if res[0]["error_msg"]:
            self.log_info("reset slave failed: {}".format(res[0]["error_msg"]))
            return False
        else:
            if res[0]["cmd_results"][0]["error_msg"]:
                self.log_info("reset slave failed: {}".format(res[0]["cmd_results"][0]["error_msg"]))
                return False

        return True


class ResetSlaveViaDRSComponent(Component):
    name = __name__
    code = "reset_slave_via_drs"
    bound_service = ResetSlaveViaDRSService
