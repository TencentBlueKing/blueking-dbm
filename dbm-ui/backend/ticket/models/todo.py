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
from backend.components import CmsiApi
from backend.configuration.constants import SystemSettingsEnum
from backend.configuration.models import SystemSettings
from backend.exceptions import ApiError
from backend.ticket.constants import TicketFlowStatus, TodoStatus, TodoType

logger = logging.getLogger("root")


class TodoManager(models.Manager):
    def exist_unfinished(self):
        return self.filter(status__in=[TodoStatus.TODO, TodoStatus.RUNNING]).exists()

    def create(self, **kwargs):
        todo = super().create(**kwargs)
        msg_types = CmsiApi.get_msg_type()
        ticket = todo.ticket
        ticket_type = ticket.get_ticket_type_display()
        for msg_type in msg_types:
            if msg_type["type"] not in SystemSettings.get_setting_value(
                key=SystemSettingsEnum.SYSTEM_MSG_TYPE.value, default=["weixin", "mail"]
            ):
                continue
            try:
                CmsiApi.send_msg(
                    {
                        "msg_type": msg_type["type"],
                        "receiver__username": ",".join(todo.operators),
                        "title": _("DBM数据库管理 待办通知").format(ticket_type=ticket_type),
                        "content": _("有一条[{ticket_type}]待办需要您处理\n" "待办详情：{todo_url}\n").format(
                            ticket_type=ticket_type,
                            todo_url=todo.url,
                        ),
                    }
                )
            except ApiError as err:
                logger.error(f"send message error, ticket_id:{ticket.id}, todo_id:{todo.id}, err:{err}")

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

    @property
    def url(self):
        return f"{env.BK_SAAS_HOST}/{self.ticket.bk_biz_id}/my-todos?id={self.id}"

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
        self.ticket.set_terminated()
        self.flow.update_status(TicketFlowStatus.TERMINATED)
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
