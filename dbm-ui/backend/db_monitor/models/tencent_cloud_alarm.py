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

from backend.bk_web.constants import LEN_LONG, LEN_MIDDLE, LEN_NORMAL, LEN_SHORT
from backend.bk_web.models import AuditedModel

__all__ = ["TencentCloudAlarmRecord"]


class TencentCloudAlarmRecord(AuditedModel):
    """腾讯云告警同步记录。负载均衡对上平台 CLB 才上报事件，Redis 目前只落库。"""

    alarm_id = models.CharField(_("告警ID"), max_length=LEN_MIDDLE, unique=True)
    product = models.CharField(_("产品"), max_length=LEN_SHORT, default="clb")
    occurred_at = models.DateTimeField(_("告警时间"))
    alarm_type = models.CharField(_("告警类型"), max_length=LEN_SHORT, default="", blank=True)
    alarm_status = models.CharField(_("告警状态"), max_length=LEN_SHORT, default="", blank=True)
    alarm_level = models.CharField(_("告警级别"), max_length=LEN_SHORT, default="", blank=True)
    region = models.CharField(_("地域"), max_length=LEN_NORMAL, default="", blank=True)
    policy_name = models.CharField(_("策略"), max_length=LEN_LONG, default="", blank=True)
    instance_id = models.CharField(_("实例ID"), max_length=LEN_MIDDLE, default="", blank=True)
    instance_name = models.CharField(_("实例名称"), max_length=LEN_LONG, default="", blank=True)
    address = models.CharField(_("实例地址"), max_length=LEN_MIDDLE, default="", blank=True)
    content = models.TextField(_("告警内容"), default="", blank=True)
    alarm_object = models.TextField(_("告警对象"), default="", blank=True)
    tags = models.JSONField(_("标签"), default=list, blank=True)
    bk_biz_id = models.IntegerField(_("业务ID"), default=0)
    app = models.CharField(_("业务英文名"), max_length=LEN_MIDDLE, default="", blank=True)
    cluster_id = models.IntegerField(_("集群ID"), default=0)
    cluster_domain = models.CharField(_("集群域名"), max_length=LEN_LONG, default="", blank=True)
    cluster_type = models.CharField(_("集群类型"), max_length=LEN_NORMAL, default="", blank=True)
    event_sent = models.BooleanField(_("是否已上报事件"), default=False)

    class Meta:
        verbose_name = verbose_name_plural = _("腾讯云告警(TencentCloudAlarmRecord)")
        ordering = ["-occurred_at", "-id"]
        indexes = [
            models.Index(fields=["event_sent", "cluster_id"], name="db_monitor_tc_alarm_evt_idx"),
        ]

    def __str__(self):
        return self.alarm_id
