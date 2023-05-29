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
from datetime import datetime
from typing import Any, Union

from django.utils.translation import gettext as _

from backend.components import ItsmApi
from backend.components.itsm.constants import ItsmTicketStatus
from backend.ticket.constants import TicketFlowStatus, TicketStatus
from backend.ticket.flow_manager.base import BaseTicketFlow
from backend.ticket.models import Flow
from backend.utils.time import datetime2str


class ItsmFlow(BaseTicketFlow):
    def __init__(self, flow_obj: Flow):
        super().__init__(flow_obj=flow_obj)

    @property
    def ticket_approval_result(self):
        # 优先读取缓存，避免同一个对象内多次请求 ITSM
        # TODO: ITSM接口请求比较缓慢
        if getattr(self, "_ticket_approval_result", None):
            return self._ticket_approval_result

        # 调用ITSM接口查询审批状态
        data = ItsmApi.ticket_approval_result({"sn": [self.flow_obj.flow_obj_id]}, use_admin=True)
        try:
            itsm_ticket_result = data[0]
        except IndexError:
            itsm_ticket_result = None

        setattr(self, "_ticket_approval_result", itsm_ticket_result)
        return itsm_ticket_result

    @property
    def _start_time(self) -> str:
        return datetime2str(self.flow_obj.create_at)

    @property
    def _end_time(self) -> Union[datetime, Any]:
        if self.ticket_approval_result:
            return self.ticket_approval_result["update_at"]

        return self.flow_obj.update_at

    @property
    def _summary(self) -> str:
        logs = ItsmApi.get_ticket_logs({"sn": [self.flow_obj.flow_obj_id]})
        # 目前审批流程是固定的，取流程中第三个节点的日志作为概览即可
        try:
            return logs["logs"][2]["message"]
        except (IndexError, KeyError):
            # 异常时根据状态取默认的概览
            status_summary_map = {
                TicketStatus.RUNNING.value: _("审批中"),
                TicketStatus.REVOKED.value: _("已撤销"),
                TicketStatus.SUCCEEDED.value: _("已通过"),
                TicketStatus.FAILED.value: _("被拒绝"),
            }
            return status_summary_map.get(self._status, "")

    @property
    def _status(self) -> str:
        # 把 ITSM 单据状态映射为本系统内的单据状态
        current_status = self.ticket_approval_result["current_status"]
        approve_result = self.ticket_approval_result["approve_result"]

        if current_status == ItsmTicketStatus.RUNNING:
            self.flow_obj.update_status(TicketFlowStatus.RUNNING)
            return TicketStatus.RUNNING

        if current_status == ItsmTicketStatus.REVOKED:
            self.flow_obj.update_status(TicketFlowStatus.REVOKED)
            return TicketStatus.REVOKED
        elif current_status == ItsmTicketStatus.FINISHED and approve_result:
            self.flow_obj.update_status(TicketFlowStatus.SUCCEEDED)
            return TicketStatus.SUCCEEDED
        else:
            self.flow_obj.update_status(TicketFlowStatus.FAILED)
            return TicketStatus.FAILED

    @property
    def _url(self) -> str:
        if self.ticket_approval_result:
            return self.ticket_approval_result["ticket_url"]

        return ""

    def _run(self) -> str:
        data = ItsmApi.create_ticket(self.flow_obj.details)
        return data["sn"]
