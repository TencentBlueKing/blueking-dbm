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

from backend.db_services.mysql.permission.constants import AuthorizeExcelHeader
from backend.ticket.models import Ticket


class MySQLAuthorizeRecord(models.Model):
    """
    授权记录
    """

    ticket = models.ForeignKey(Ticket, help_text=_("关联工单"), related_name="authorize_records", on_delete=models.CASCADE)

    user = models.CharField(_("账号名称"), max_length=255)
    source_ips = models.TextField(_("源ip列表"))
    target_instances = models.TextField(_("目标集群"))
    access_dbs = models.TextField(_("访问DB名列表"))

    status = models.BooleanField(_("是否授权成功"), default=True)
    error = models.TextField(_("错误信息/提示信息"), default="")
    record_time = models.DateTimeField(_("记录时间"), auto_now=True)

    class Meta:
        verbose_name = _("授权记录")
        verbose_name_plural = _("授权记录")
        ordering = ["-record_time"]

    @classmethod
    def get_authorize_records_by_ticket(cls, ticket_id: int):
        return cls.objects.filter(ticket__pk=ticket_id)

    def serialize_excel_data(self):
        return {
            AuthorizeExcelHeader.USER: self.user,
            AuthorizeExcelHeader.SOURCE_IPS: self.source_ips,
            AuthorizeExcelHeader.TARGET_INSTANCES: self.target_instances,
            AuthorizeExcelHeader.ACCESS_DBS: self.access_dbs,
            AuthorizeExcelHeader.ERROR: self.error,
        }
