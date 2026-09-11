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
import logging
from typing import List

from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import Service

from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.mongodb.deferred_deinstall_ticket import deferred_deinstall_ticket

logger = logging.getLogger("json")


class ExecDeferredDeInstallTicketOperation(BaseService):
    """父流程创建 MongoDB 延迟下架单据。"""

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        try:
            deferred_deinstall_ticket(
                infos=kwargs["infos"],
                creator=kwargs["creator"],
                bk_biz_id=kwargs["bk_biz_id"],
                parent_ticket=kwargs.get("parent_ticket_id") or kwargs.get("uid"),
                poll_interval_sec=kwargs.get("poll_interval_sec", 300),
                max_wait_hours=kwargs.get("max_wait_hours", 168),
            )
        except Exception as e:  # noqa: BLE001
            self.log_error("create deferred deinstall ticket fail, error:{}".format(e))
            return False
        self.log_info("create deferred deinstall ticket successfully")
        return True

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]


class ExecDeferredDeInstallTicketOperationComponent(Component):
    name = __name__
    code = "deferred_deinstall_ticket"
    bound_service = ExecDeferredDeInstallTicketOperation
