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
from typing import Union

from django.utils.translation import gettext as _

from backend.ticket.constants import TodoType
from backend.ticket.flow_manager.pause import PauseFlow
from backend.ticket.models import Todo
from backend.ticket.todos.confirm_modify_todo import ConfirmModifyTodoContext


class ConfirmModifyFlow(PauseFlow):
    """
    确认修改流程，用于审批人代为修改后，由提单人确认改单内容
    - 与 PauseFlow 同构，区别在于待办类型为 CONFIRM_MODIFY，处理人为提单人
    """

    def _run(self) -> Union[int, str]:
        confirm_uid = f"confirm_modify_{uuid.uuid1().hex}"

        # 创建待确认修改待办，处理人为提单人(由 TodoManager.get_operators 按类型推导)
        Todo.objects.create(
            name=_("【{}】单据内容已由审批人修改，请确认").format(self.ticket.get_ticket_type_display()),
            flow=self.flow_obj,
            ticket=self.ticket,
            type=TodoType.CONFIRM_MODIFY,
            operators=self.flow_obj.details.get("operators", []),
            context=ConfirmModifyTodoContext(self.flow_obj.id, self.ticket.id).to_dict(),
        )

        return confirm_uid
