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

from backend.bk_web.constants import LEN_SHORT
from backend.components import UserManagerApi
from backend.configuration.constants import SystemSettingsEnum
from backend.configuration.models import SystemSettings
from backend.db_services.dbpermission.constants import RuleActionType
from backend.ticket.models import Ticket


class AuthorizeRecord(models.Model):
    """
    授权记录 TODO: 请不要使用此表，以后会删除
    """

    ticket = models.ForeignKey(Ticket, help_text=_("关联工单"), related_name="authorize_records", on_delete=models.CASCADE)

    user = models.CharField(_("账号名称"), max_length=255)
    source_ips = models.TextField(_("源ip列表"), default="")
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


class DBRuleActionLog(models.Model):
    """
    权限变更记录：包括授权、修改、删除、创建
    """

    operator = models.CharField(_("操作人"), max_length=LEN_SHORT)
    record_time = models.DateTimeField(_("记录时间"), auto_now=True)
    account_id = models.IntegerField(_("账号ID"))
    rule_id = models.IntegerField(_("权限规则ID"))
    action_type = models.CharField(_("操作类型"), choices=RuleActionType.get_choices(), max_length=LEN_SHORT)

    class Meta:
        verbose_name = _("权限变更记录")
        verbose_name_plural = _("权限变更记录")
        ordering = ["-record_time"]
        indexes = [
            models.Index(fields=["rule_id"]),
            models.Index(fields=["account_id"]),
        ]

    @classmethod
    def create_log(cls, account_id, rule_id, operator, action):
        log = DBRuleActionLog.objects.create(
            rule_id=rule_id, account_id=account_id, operator=operator, action_type=action
        )
        return log

    @classmethod
    def get_notifiers(cls, rule_id):
        """获取通知人列表，目前只过滤有授权记录的人"""
        users = cls.objects.filter(rule_id=rule_id, action_type=RuleActionType.AUTH).values_list("operator", flat=True)
        if not users:
            return []
        # 过滤离职的和虚拟账户
        virtual_users = SystemSettings.get_setting_value(key=SystemSettingsEnum.VIRTUAL_USERS, default=[])
        real_users = UserManagerApi.list_users(
            {"fields": "username", "exact_lookups": ",".join(users), "no_page": True}
        )
        real_users = [user["username"] for user in real_users]
        return list(set(real_users) - set(virtual_users))
