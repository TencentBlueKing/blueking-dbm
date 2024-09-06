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

from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from backend import env
from backend.bk_web.constants import LEN_MIDDLE, LEN_SHORT
from backend.bk_web.models import AuditedModel
from backend.configuration.constants import BizSettingsEnum
from backend.configuration.models import BizSettings
from backend.ticket.constants import (
    TODO_RUNNING_STATUS,
    FlowMsgStatus,
    FlowMsgType,
    TicketFlowStatus,
    TodoStatus,
    TodoType,
)
from backend.ticket.tasks.ticket_tasks import send_msg_for_flow

logger = logging.getLogger("root")


class TodoManager(models.Manager):
    def exist_unfinished(self):
        return self.filter(status__in=TODO_RUNNING_STATUS).exists()

    def create(self, **kwargs):
        bk_biz_id = kwargs["ticket"].bk_biz_id
        assistance_flag = BizSettings.get_setting_value(bk_biz_id, key=BizSettingsEnum.BIZ_ASSISTANCE_SWITCH) or False
        if assistance_flag:
            # 获取业务协助人列表
            biz_helpers = BizSettings.get_setting_value(bk_biz_id, key=BizSettingsEnum.BIZ_ASSISTANCE_VARS, default=[])
            # 合并单据处理人 + 业务协助人
            kwargs["operators"] = kwargs.get("operators", []) + biz_helpers
        # 对操作者去重
        kwargs["operators"] = list(set(kwargs["operators"]))
        todo = super().create(**kwargs)
        send_msg_for_flow.apply_async(
            kwargs={
                "flow_id": todo.flow.id,
                "flow_msg_type": FlowMsgType.TODO.value,
                "flow_status": FlowMsgStatus.UNCONFIRMED.value,
                "processor": ",".join(todo.operators),
                "receiver": todo.creator,
            }
        )

        return todo


class Todo(AuditedModel):
    """
    Flow相关的待办
    """

    name = models.CharField(_("待办标题"), max_length=LEN_MIDDLE, default="")
    flow = models.ForeignKey("Flow", help_text=_("关联流程任务"), related_name="todo_of_flow", on_delete=models.CASCADE)
    ticket = models.ForeignKey("Ticket", help_text=_("关联工单"), related_name="todo_of_ticket", on_delete=models.CASCADE)
    operators = models.JSONField(_("待办人"), default=list)
    type = models.CharField(
        _("待办类型"),
        choices=TodoType.get_choices(),
        max_length=LEN_SHORT,
        default=TodoType.APPROVE,
    )
    context = models.JSONField(_("上下文"), default=dict)
    status = models.CharField(
        _("待办状态"),
        choices=TodoStatus.get_choices(),
        max_length=LEN_SHORT,
        default=TodoStatus.TODO,
    )
    done_by = models.CharField(_("待办完成人"), max_length=LEN_SHORT, default="")
    done_at = models.DateTimeField(_("待办完成时间"), null=True)

    objects = TodoManager()

    class Meta:
        verbose_name_plural = verbose_name = _("待办(Todo)")

    @property
    def url(self):
        return f"{env.BK_SAAS_HOST}/my-todos?id={self.ticket.id}"

    def set_status(self, username, status):
        self.status = status

        if status in [TodoStatus.DONE_SUCCESS, TodoStatus.DONE_FAILED]:
            self.done_by = username
            self.done_at = timezone.now()

        self.save()

    def set_success(self, username, action):
        self.set_status(username, TodoStatus.DONE_SUCCESS)
        TodoHistory.objects.create(creator=username, todo=self, action=action)

    def set_terminated(self, username, action):
        self.set_status(username, TodoStatus.DONE_FAILED)
        self.flow.update_status(TicketFlowStatus.TERMINATED)
        TodoHistory.objects.create(creator=username, todo=self, action=action)


class TodoHistory(AuditedModel):
    """
    待办操作记录
    """

    todo = models.ForeignKey("Todo", help_text=_("关联待办"), related_name="history_of_todo", on_delete=models.CASCADE)
    action = models.CharField(_("操作"), max_length=LEN_MIDDLE, default="")

    class Meta:
        verbose_name = _("待办操作记录")
        verbose_name_plural = _("待办操作记录")
