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
from backend.configuration.constants import PLAT_BIZ_ID, DBType
from backend.db_meta.enums import ClusterType
from backend.db_monitor.constants import GroupType


class NoticeGroup(AuditedModel):
    """告警通知组：一期粒度仅支持到业务级，可开关是否同步DBA人员数据"""

    bk_biz_id = models.IntegerField(help_text=_("业务ID, 0代表全业务"), default=PLAT_BIZ_ID)
    monitor_group_id = models.BigIntegerField(help_text=_("监控通知组ID"), default=0)
    group_type = models.CharField(
        _("告警通知组类别"), choices=GroupType.get_choices(), max_length=LEN_NORMAL, default=GroupType.PLATFORM
    )

    db_type = models.CharField(_("数据库类型"), choices=DBType.get_choices(), max_length=LEN_SHORT)
    users = models.JSONField(_("人员列表"))

    dba_sync = models.BooleanField(help_text=_("自动同步DBA人员配置"), default=True)

    class Meta:
        verbose_name = _("告警通知组")

    @classmethod
    def get_monitor_groups(cls, db_type, group_type=GroupType.PLATFORM):
        return list(
            cls.objects.filter(group_type=group_type, db_type=db_type).values_list("monitor_group_id", flat=True)
        )


class RuleTemplate(AuditedModel):
    """告警策略模板"""

    bk_biz_id = models.IntegerField(help_text=_("业务ID, 0代表全业务"), default=PLAT_BIZ_ID)
    monitor_strategy_id = models.IntegerField(help_text=_("监控策略ID"), default=0)

    name = models.CharField(verbose_name=_("策略名称"), max_length=LEN_MIDDLE, default="")
    db_type = models.CharField(
        _("DB类型"), choices=DBType.get_choices(), max_length=LEN_NORMAL, default=DBType.MySQL.value
    )

    details = models.JSONField(verbose_name=_("模板详情"), default=dict)
    is_enabled = models.BooleanField(_("是否启用"), default=True)

    class Meta:
        verbose_name = _("告警策略模板")


class AlertRule(AuditedModel):
    """告警策略实例"""

    bk_biz_id = models.IntegerField(help_text=_("业务ID, 0代表全业务"), default=PLAT_BIZ_ID)

    template_id = models.IntegerField(help_text=_("监控模板ID"), default=0)
    monitor_strategy_id = models.IntegerField(help_text=_("监控策略ID"), default=0)

    name = models.CharField(verbose_name=_("策略名称"), max_length=LEN_MIDDLE, default="")
    db_type = models.CharField(
        _("DB类型"), choices=DBType.get_choices(), max_length=LEN_NORMAL, default=DBType.MySQL.value
    )

    details = models.JSONField(verbose_name=_("实例详情"), default=dict)
    is_enabled = models.BooleanField(_("是否启用"), default=True)

    class Meta:
        verbose_name = _("告警策略实例")


class CollectTemplateBase(AuditedModel):
    """采集策略模板"""

    bk_biz_id = models.IntegerField(help_text=_("业务ID, 0代表全业务"), default=PLAT_BIZ_ID)
    plugin_id = models.CharField(verbose_name=_("插件ID"), max_length=LEN_MIDDLE, unique=True)
    db_type = models.CharField(
        _("DB类型"), choices=DBType.get_choices(), max_length=LEN_NORMAL, default=DBType.MySQL.value
    )
    details = models.JSONField(verbose_name=_("详情"), default=dict)

    class Meta:
        abstract = True
        verbose_name = _("采集策略模板")


class CollectTemplate(CollectTemplateBase):
    class Meta:
        verbose_name = _("采集策略模板")


class CollectInstance(CollectTemplateBase):
    """采集策略实例"""

    template_id = models.IntegerField(help_text=_("监控插件模板ID"), default=0)
    collect_id = models.IntegerField(help_text=_("监控采集策略ID"))

    class Meta:
        verbose_name = _("采集策略实例")


class Dashboard(AuditedModel):
    """仪表盘"""

    name = models.CharField(verbose_name=_("名称"), max_length=LEN_MIDDLE, default="")
    cluster_type = models.CharField(max_length=64, choices=ClusterType.get_choices(), default="")

    details = models.JSONField(verbose_name=_("详情"), default=dict)
    variables = models.JSONField(verbose_name=_("变量"), default=dict)

    # grafana相关
    org_id = models.BigIntegerField(verbose_name=_("grafana-org_id"))
    org_name = models.CharField(verbose_name=_("grafana-org_name"), max_length=LEN_NORMAL)
    uid = models.CharField(verbose_name=_("grafana-uid"), max_length=LEN_NORMAL)
    url = models.CharField(verbose_name=_("grafana-url"), max_length=LEN_LONG)

    class Meta:
        verbose_name = _("仪表盘")
