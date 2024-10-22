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
import uuid
from typing import Optional

from django.utils.translation import gettext as _

from backend.flow.consts import FAILED_STATES, SUCCEED_STATES
from backend.flow.models import FlowTree, StateType
from backend.ticket import constants
from backend.ticket.constants import TicketFlowStatus
from backend.ticket.flow_manager.base import BaseTicketFlow
from backend.ticket.models import Flow
from backend.utils.time import datetime2str


class DeliveryFlow(BaseTicketFlow):
    """交付节点，没有实际的执行动作"""

    def __init__(self, flow_obj: Flow):
        self.flow_obj_id = flow_obj.flow_obj_id
        super().__init__(flow_obj=flow_obj)

    @property
    def _start_time(self) -> str:
        return datetime2str(self.flow_obj.update_at)

    @property
    def _end_time(self) -> Optional[str]:
        return datetime2str(self.flow_obj.update_at)

    @property
    def _summary(self) -> str:
        return _("交付成功")

    @property
    def _status(self) -> str:
        # 走到交付节点，状态一定为成功
        self.flow_obj.update_status(TicketFlowStatus.SUCCEEDED)
        return constants.TicketFlowStatus.SUCCEEDED

    @property
    def _url(self) -> str:
        return ""

    def _run(self) -> str:
        describe_root_id = f"describe_{uuid.uuid1()}"
        return describe_root_id

    def run(self) -> None:
        # 跳过任务，直接进入下一流程
        super().run()

        from backend.ticket.flow_manager.manager import TicketFlowManager

        TicketFlowManager(ticket=self.ticket).run_next_flow()


class DescribeTaskFlow(DeliveryFlow):
    """
    描述节点，仅用于描述一个触发该单据的内置任务信息的节点，没有实际的执行动作
    默认触发该单据任务的root_id在当前单据的detail中
    """

    def __init__(self, flow_obj: Flow):
        super().__init__(flow_obj=flow_obj)
        self.pre_root_id = self.ticket.details["root_id"]
        self.pre_flow_tree = FlowTree.objects.get(root_id=self.pre_root_id)

    @property
    def _start_time(self) -> str:
        return datetime2str(self.pre_flow_tree.created_at)

    @property
    def _end_time(self) -> Optional[str]:
        return datetime2str(self.pre_flow_tree.updated_at)

    @property
    def _summary(self) -> dict:
        if self.pre_flow_tree.status in FAILED_STATES:
            return {"status": TicketFlowStatus.FAILED, "message": _("失败后继续提交")}
        elif self.pre_flow_tree.status in SUCCEED_STATES:
            return {"status": TicketFlowStatus.SUCCEEDED, "message": _("执行成功")}
        else:
            state = StateType.get_choice_label(self.pre_flow_tree.status)
            return {"status": TicketFlowStatus.RUNNING, "message": _("执行{}".format(state))}

    @property
    def _url(self) -> str:
        return f"/database/{self.ticket.bk_biz_id}/mission-details/{self.pre_root_id}/"

    def _run(self) -> str:
        describe_root_id = f"describe_{uuid.uuid1()}"
        return describe_root_id

    def run(self) -> None:
        # 跳过任务，直接进入下一流程
        super().run()

        from backend.ticket.flow_manager.manager import TicketFlowManager

        TicketFlowManager(ticket=self.ticket).run_next_flow()
