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
from backend.db_monitor.constants import GroupType, PolicyStatus, TargetLevel, TargetPriority

__all__ = ["NoticeGroup", "AlertRule", "RuleTemplate", "DispatchGroup", "MonitorPolicy"]


class NoticeGroup(AuditedModel):
    """告警通知组：一期粒度仅支持到业务级，可开关是否同步DBA人员数据"""

    bk_biz_id = models.IntegerField(help_text=_("业务ID, 0代表全业务"), default=PLAT_BIZ_ID)
    monitor_group_id = models.BigIntegerField(help_text=_("监控通知组ID"), default=0)
    group_type = models.CharField(
        _("告警通知组类别"), choices=GroupType.get_choices(), max_length=LEN_NORMAL, default=GroupType.PLATFORM
    )

    db_type = models.CharField(_("数据库类型"), choices=DBType.get_choices(), max_length=LEN_SHORT)

    receivers = models.JSONField(_("告警接收人员/组列表"), default=dict)
    details = models.JSONField(verbose_name=_("通知方式详情"), default=dict)

    is_synced = models.BooleanField(verbose_name=_("是否已同步到监控"), default=False)
    sync_at = models.DateTimeField(_("最近一次的同步时间"), null=True)
    dba_sync = models.BooleanField(help_text=_("自动同步DBA人员配置"), default=True)

    class Meta:
        verbose_name = _("告警通知组")

    @classmethod
    def get_monitor_groups(cls, db_type, group_type=GroupType.PLATFORM):
        return list(
            cls.objects.filter(group_type=group_type, db_type=db_type).values_list("monitor_group_id", flat=True)
        )


class RuleTemplate(AuditedModel):
    """TODO: 告警策略模板：deprecated"""

    bk_biz_id = models.IntegerField(help_text=_("业务ID, 0代表全业务"), default=PLAT_BIZ_ID)
    monitor_strategy_id = models.IntegerField(help_text=_("监控策略ID"), default=0)

    name = models.CharField(verbose_name=_("策略名称监控侧要求唯一"), max_length=LEN_MIDDLE, unique=True)
    db_type = models.CharField(
        _("DB类型"), choices=DBType.get_choices(), max_length=LEN_NORMAL, default=DBType.MySQL.value
    )

    details = models.JSONField(verbose_name=_("模板详情"), default=dict)
    is_enabled = models.BooleanField(_("是否启用"), default=True)

    class Meta:
        verbose_name = _("告警策略模板")


class AlertRule(AuditedModel):
    """TODO: 告警策略实例：deprecated"""

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


class DispatchGroup(AuditedModel):
    """分派策略组"""

    monitor_dispatch_id = models.IntegerField(verbose_name=_("蓝鲸监控分派策略组ID"), default=0)
    name = models.CharField(verbose_name=_("策略名称，全局唯一"), max_length=LEN_MIDDLE)
    priority = models.PositiveIntegerField(verbose_name=_("监控策略优先级，跟随targets调整"))
    details = models.JSONField(verbose_name=_("策略模板详情，可用于还原"), default=dict)
    is_synced = models.BooleanField(verbose_name=_("是否已同步到监控"), default=False)
    sync_at = models.DateTimeField(_("最近一次的同步时间"), null=True)

    class Meta:
        verbose_name = _("分派策略组")


class MonitorPolicy(AuditedModel):
    """监控策略"""

    parent_id = models.IntegerField(verbose_name=_("父级策略ID，0代表父级"), default=0)
    name = models.CharField(verbose_name=_("策略名称，全局唯一"), max_length=LEN_MIDDLE, unique=True)
    bk_biz_id = models.IntegerField(verbose_name=_("业务ID, 0代表全业务"), default=PLAT_BIZ_ID)

    db_type = models.CharField(
        _("DB类型"), choices=DBType.get_choices(), max_length=LEN_NORMAL, default=DBType.MySQL.value
    )

    details = models.JSONField(verbose_name=_("策略模板详情，可用于还原"), default=dict)

    # 拆解部分details中的字段到外层
    targets = models.JSONField(verbose_name=_("监控目标"), default=dict)
    target_level = models.CharField(
        verbose_name=_("监控目标级别，跟随targets调整"),
        choices=TargetLevel.get_choices(),
        max_length=LEN_NORMAL,
        default=TargetLevel.APP.value,
    )
    target_priority = models.PositiveIntegerField(verbose_name=_("监控策略优先级，跟随targets调整"))

    # [{}, {}]
    test_rules = models.JSONField(verbose_name=_("检测规则"), default=dict)
    # [1,2,3]
    notify_rules = models.JSONField(verbose_name=_("通知规则"), default=dict)
    # [1,2,3]
    notify_groups = models.JSONField(verbose_name=_("通知组"), default=dict)

    is_enabled = models.BooleanField(verbose_name=_("是否已启用"), default=True)
    is_synced = models.BooleanField(verbose_name=_("是否已同步到监控"), default=False)

    # 当 is_synced=True时，才有效
    sync_at = models.DateTimeField(_("最近一次的同步时间"), null=True)
    event_count = models.IntegerField(verbose_name=_("告警事件数量，初始值设置为-1"), default=-1)

    # 意义不大
    policy_status = models.CharField(
        verbose_name=_("策略状态"),
        choices=PolicyStatus.get_choices(),
        max_length=LEN_NORMAL,
        default=PolicyStatus.VALID.value,
    )

    # 分派策略组ID，目前专供内置策略
    dispatch_group_id = models.BigIntegerField(verbose_name=_("分派策略组ID，0代表没有对应的策略"), default=0)
    monitor_policy_id = models.BigIntegerField(verbose_name=_("蓝鲸监控策略ID"), default=0)

    def calculate_targets(self):
        """TODO: 根据目标计算优先级（样例）"""
        self.target_level = TargetLevel.APP
        self.target_priority = TargetPriority.APP
        self.save()

    class Meta:
        verbose_name = _("告警策略")
