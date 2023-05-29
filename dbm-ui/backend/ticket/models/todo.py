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
from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _

from backend.bk_web.constants import LEN_MIDDLE, LEN_SHORT
from backend.bk_web.models import AuditedModel
from backend.ticket.constants import TicketFlowStatus, TodoStatus, TodoType


class TodoManager(models.Manager):
    def exist_unfinished(self):
        return self.filter(status__in=[TodoStatus.TODO, TodoStatus.RUNNING]).exists()


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

    def set_status(self, username, status):
        self.status = status

        if status in [TodoStatus.DONE_SUCCESS, TodoStatus.DONE_FAILED]:
            self.done_by = username
            self.done_at = timezone.now()

        self.save()

    def set_success(self, username, action):
        self.set_status(username, TodoStatus.DONE_SUCCESS)
        TodoHistory.objects.create(creator=username, todo=self, action=action)

    def set_failed(self, username, action):
        self.set_status(username, TodoStatus.DONE_FAILED)
        self.ticket.set_failed()
        self.flow.update_status(TicketFlowStatus.FAILED)
        TodoHistory.objects.create(creator=username, todo=self, action=action)

    class Meta:
        verbose_name = _("待办")
        verbose_name_plural = _("待办")


class TodoHistory(AuditedModel):
    """
    待办操作记录
    """

    todo = models.ForeignKey("Todo", help_text=_("关联待办"), related_name="history_of_todo", on_delete=models.CASCADE)
    action = models.CharField(_("操作"), max_length=LEN_MIDDLE, default="")

    class Meta:
        verbose_name = _("待办操作记录")
        verbose_name_plural = _("待办操作记录")
