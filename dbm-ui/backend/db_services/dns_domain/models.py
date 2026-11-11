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
from django.utils.translation import gettext_lazy as _

from backend.bk_web.constants import LEN_NORMAL, LEN_SHORT
from backend.bk_web.models import AuditedModel
from backend.constants import DEFAULT_BK_CLOUD_ID
from backend.db_services.dns_domain.constants import REMARK_MAX_LENGTH, AuditAction, MaintainType


class DnsDomain(AuditedModel):
    """自主维护域名。集群托管域名不落这张表，读取时从集群元数据带出。"""

    domain = models.CharField(_("完整域名"), max_length=253, primary_key=True)
    maintain_type = models.CharField(
        _("维护方式"), max_length=LEN_SHORT, choices=MaintainType.get_choices(), default=MaintainType.SELF
    )
    remark = models.CharField(_("备注"), max_length=REMARK_MAX_LENGTH, blank=True, default="")
    owners = models.JSONField(_("负责人"), default=list)
    bk_biz_id = models.IntegerField(_("业务ID"), default=0)
    bk_cloud_id = models.IntegerField(_("云区域ID"), default=DEFAULT_BK_CLOUD_ID)

    class Meta:
        db_table = "dns_domain"
        verbose_name = verbose_name_plural = _("域名(DnsDomain)")


class DnsDomainAuditLog(models.Model):
    """域名映射变更日志。本域和全局操作日志都读这张表。"""

    domain = models.CharField(_("完整域名"), max_length=253, db_index=True)
    operator = models.CharField(_("操作人"), max_length=LEN_NORMAL)
    client_ip = models.CharField(_("客户端IP"), max_length=LEN_NORMAL, blank=True, default="")
    action = models.CharField(_("操作类型"), max_length=LEN_SHORT, choices=AuditAction.get_choices())
    change_lines = models.JSONField(_("变更内容"), default=list)
    create_at = models.DateTimeField(_("时间"), auto_now_add=True, db_index=True)

    class Meta:
        db_table = "dns_domain_audit_log"
        verbose_name = verbose_name_plural = _("域名操作日志(DnsDomainAuditLog)")
        indexes = [models.Index(fields=["domain", "create_at"], name="dns_audit_domain_time_idx")]
