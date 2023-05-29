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
from django.utils.translation import ugettext_lazy as _

from backend.bk_web.constants import LEN_NORMAL, LEN_SHORT
from backend.db_services.mysql.permission.constants import CloneType
from backend.ticket.models import Ticket


class MySQLPermissionCloneRecord(models.Model):
    """
    权限克隆记录模型基类
    """

    ticket = models.ForeignKey(Ticket, help_text=_("关联工单"), related_name="clone_records", on_delete=models.CASCADE)

    clone_type = models.CharField(_("权限克隆类型"), choices=CloneType.get_choices(), max_length=LEN_SHORT)
    bk_cloud_id = models.IntegerField(_("云区域ID"))
    source = models.CharField(_("旧实例/旧客户端IP"), max_length=LEN_NORMAL)
    target = models.TextField(_("新实例/新客户端IP列表"))

    status = models.BooleanField(_("是否克隆成功"), default=True)
    error = models.TextField(_("错误信息"), default="")
    record_time = models.DateTimeField(_("记录时间"), auto_now=True)

    class Meta:
        ordering = ["-record_time"]
        verbose_name = _("权限克隆记录")
        verbose_name_plural = _("权限克隆记录")

    @classmethod
    def get_clone_records_by_ticket(cls, ticket_id: int, clone_type):
        return cls.objects.filter(ticket__pk=ticket_id, clone_type=clone_type).values(
            "source", "target", "bk_cloud_id", "error"
        )
