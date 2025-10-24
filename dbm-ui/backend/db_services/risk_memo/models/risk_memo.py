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

from backend.bk_web.models import AuditedModel
from backend.configuration.constants import DBType
from backend.db_services.risk_memo.constants import RiskOpType, RiskPriority, Status
from backend.db_services.risk_memo.models.managers import RiskMemoFollowUpManager, RiskMemoManager


class RiskMemo(AuditedModel):
    """
    风险备忘录数据表
    """

    name = models.CharField(max_length=64, default="", help_text=_("风险名称"))
    bk_biz_id = models.IntegerField(default=0)
    level = models.CharField(
        max_length=64, choices=RiskPriority.get_choices(), default=RiskPriority.MIDDLE.value, help_text=_("风险等级")
    )
    status = models.CharField(
        max_length=32, choices=Status.get_choices(), default=Status.DOING.value, help_text=_("风险状态")
    )
    db_type = models.CharField(max_length=64, choices=DBType.get_choices(), default="", help_text=_("影响DB"))
    description = models.TextField(default="", help_text=_("风险描述"))
    biz_inpact = models.CharField(max_length=255, default="", help_text=_("业务影响"))
    inpact_cluster = models.CharField(max_length=255, default="", help_text=_("影响集群"))
    is_special = models.BooleanField(default=False, help_text=_("是否特殊"))
    duration_time = models.IntegerField(default=0)
    # 结项字段
    finalist = models.CharField(max_length=64, default="", help_text=_("结项人"))
    final_time = models.DateTimeField(blank=True, null=True, help_text=_("结项时间"))
    final_content = models.TextField(null=True, blank=True, help_text=_("结项内容"))

    objects = RiskMemoManager()

    class Meta:
        db_table = "tb_risk_memo"
        verbose_name = verbose_name_plural = _("风险备忘录数据表")


class RiskMemoFollowUp(AuditedModel):
    """
    风险备忘录跟进表
    """

    risk = models.ForeignKey("RiskMemo", help_text=_("关联风险备忘录"), on_delete=models.CASCADE)
    content = models.TextField(null=True, blank=True, help_text=_("跟进内容"))

    objects = RiskMemoFollowUpManager()

    class Meta:
        db_table = "tb_risk_memo_follow_up"
        verbose_name = verbose_name_plural = _("风险备忘录跟进表")


class RiskOperateRecord(AuditedModel):
    """
    风险操作记录表
    """

    risk = models.ForeignKey("RiskMemo", help_text=_("关联风险备忘录"), on_delete=models.CASCADE)
    oper_type = models.CharField(max_length=64, choices=RiskOpType.get_choices(), default="")

    class Meta:
        db_table = "tb_risk_oper_record"
        verbose_name = verbose_name_plural = _("风险操作记录表")
