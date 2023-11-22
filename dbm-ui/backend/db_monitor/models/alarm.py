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
import copy
import datetime
import json
import logging
from collections import defaultdict

from django.db import models
from django.db.models import Count
from django.utils.translation import gettext_lazy as _

from backend import env
from backend.bk_web.constants import LEN_LONG, LEN_MIDDLE, LEN_NORMAL, LEN_SHORT
from backend.bk_web.models import AuditedModel
from backend.components import BKMonitorV3Api
from backend.configuration.constants import PLAT_BIZ_ID, DBType, SystemSettingsEnum
from backend.configuration.models import SystemSettings
from backend.db_meta.models import AppMonitorTopo, DBModule
from backend.db_monitor.constants import (
    APP_PRIORITY,
    BK_MONITOR_SAVE_DISPATCH_GROUP_TEMPLATE,
    BK_MONITOR_SAVE_USER_GROUP_TEMPLATE,
    DEFAULT_ALERT_NOTICE,
    PLAT_PRIORITY,
    PROMQL_FILTER_TPL,
    TARGET_LEVEL_TO_PRIORITY,
    AlertSourceEnum,
    DutyRuleCategory,
    PolicyStatus,
    TargetLevel,
)
from backend.db_monitor.exceptions import (
    BkMonitorDeleteAlarmException,
    BkMonitorSaveAlarmException,
    BuiltInNotAllowDeleteException,
)
from backend.db_monitor.tasks import update_app_policy
from backend.exceptions import ApiError, ApiResultError

__all__ = ["NoticeGroup", "AlertRule", "RuleTemplate", "DispatchGroup", "MonitorPolicy", "DutyRule"]

logger = logging.getLogger("root")


class NoticeGroup(AuditedModel):
    """告警通知组：一期粒度仅支持到业务级，可开关是否同步DBA人员数据"""

    bk_biz_id = models.IntegerField(help_text=_("业务ID, 0代表全业务"), default=PLAT_BIZ_ID)
    name = models.CharField(_("告警通知组名称"), max_length=LEN_MIDDLE, default="")
    monitor_group_id = models.BigIntegerField(help_text=_("监控通知组ID"), default=0)
    monitor_duty_rule_id = models.IntegerField(verbose_name=_("监控轮值规则 ID"), default=0)
    db_type = models.CharField(_("数据库类型"), choices=DBType.get_choices(), max_length=LEN_SHORT, default="")
    receivers = models.JSONField(_("告警接收人员/组列表"), default=dict)
    details = models.JSONField(verbose_name=_("通知方式详情"), default=dict)
    is_built_in = models.BooleanField(verbose_name=_("是否内置"), default=False)
    sync_at = models.DateTimeField(_("最近一次的同步时间"), null=True)
    dba_sync = models.BooleanField(help_text=_("自动同步DBA人员配置"), default=True)

    class Meta:
        verbose_name_plural = verbose_name = _("告警通知组")
        unique_together = ("bk_biz_id", "name")

    @classmethod
    def get_monitor_groups(cls, db_type=None, group_ids=None, **kwargs):
        """查询监控告警组id"""
        qs = cls.objects.all()

        if db_type:
            qs = qs.filter(db_type=db_type)

        if group_ids is not None:
            qs = qs.filter(id__in=group_ids)

        # is_built_in/bk_biz_id等
        if kwargs:
            qs = qs.filter(**kwargs)

        return list(qs.values_list("monitor_group_id", flat=True))

    @classmethod
    def get_groups(cls, bk_biz_id, id_name="monitor_group_id") -> dict:
        """业务内置"""
        return dict(cls.objects.filter(bk_biz_id=bk_biz_id, is_built_in=True).values_list("db_type", id_name))

    def save_monitor_group(self) -> int:
        # 深拷贝保存用户组的模板
        save_monitor_group_params = copy.deepcopy(BK_MONITOR_SAVE_USER_GROUP_TEMPLATE)
        # 更新差异字段
        bk_monitor_group_name = f"{self.name}_{self.bk_biz_id}"
        save_monitor_group_params.update(
            {
                "name": bk_monitor_group_name,
                "alert_notice": self.details.get("alert_notice") or DEFAULT_ALERT_NOTICE,
                "bk_biz_id": env.DBA_APP_BK_BIZ_ID,
            }
        )
        if self.is_built_in:
            # 内置告警组
            # 创建/更新一条轮值规则
            save_duty_rule_params = {
                "name": f"{self.name}_{self.bk_biz_id}",
                "bk_biz_id": env.DBA_APP_BK_BIZ_ID,
                "effective_time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "end_time": "",
                "labels": [self.db_type],
                "enabled": True,
                "category": DutyRuleCategory.REGULAR.value,
                "duty_arranges": [
                    {
                        "duty_time": [{"work_type": "daily", "work_time": ["00:00--23:59"]}],
                        "duty_users": [self.receivers],
                    }
                ],
            }
            if self.monitor_duty_rule_id:
                save_duty_rule_params["id"] = self.monitor_duty_rule_id
            try:
                resp = BKMonitorV3Api.save_duty_rule(save_duty_rule_params)
                self.monitor_duty_rule_id = resp["id"]
            except ApiError as err:
                logger.error(f"request monitor api error: {err}")
                save_monitor_group_params["duty_arranges"][0]["users"] = self.receivers
            else:
                # 轮值生效，把相同 db_type 的轮值应用到此告警组中
                monitor_duty_rule_ids = (
                    DutyRule.objects.filter(db_type=self.db_type)
                    .exclude(monitor_duty_rule_id=0)
                    .order_by("-priority")
                    .values_list("monitor_duty_rule_id", flat=True)
                )
                save_monitor_group_params["need_duty"] = True
                save_monitor_group_params["duty_rules"] = list(monitor_duty_rule_ids)
        else:
            save_monitor_group_params["duty_arranges"][0]["users"] = self.receivers

        if self.monitor_group_id:
            save_monitor_group_params["id"] = self.monitor_group_id
        # 调用监控接口写入
        try:
            resp = BKMonitorV3Api.save_user_group(save_monitor_group_params)
        except ApiResultError:
            # 告警组重名的情况下，匹配告警组名称，获取 id 进行更新
            bk_monitor_groups = BKMonitorV3Api.search_user_groups({"bk_biz_ids": [env.DBA_APP_BK_BIZ_ID]})
            for group in bk_monitor_groups:
                if group["name"] == bk_monitor_group_name:
                    save_monitor_group_params["id"] = group["id"]
                    break
            resp = BKMonitorV3Api.save_user_group(save_monitor_group_params)
        self.sync_at = datetime.datetime.now()
        return resp["id"]

    def save(self, *args, **kwargs):
        """
        保存告警组
        """
        self.monitor_group_id = self.save_monitor_group()
        if self.is_built_in:
            # 更新业务策略绑定的告警组
            update_app_policy.delay(self.bk_biz_id, self.id, self.db_type)
        super().save(*args, **kwargs)

    def delete(self, using=None, keep_parents=False):
        if self.is_built_in:
            raise BuiltInNotAllowDeleteException
        BKMonitorV3Api.delete_user_groups({"ids": [self.monitor_group_id], "bk_biz_ids": [env.DBA_APP_BK_BIZ_ID]})
        super().delete()


class DutyRule(AuditedModel):
    """
    轮值规则，仅为平台设置，启用后默认应用到所有内置告警组
    duty_arranges:
    交替轮值（category=handoff）
    [
        {
            "duty_number": 2,
            "duty_day": 1,
            "members": ["admin"],
            "work_type": "weekly",
            "work_days": [6, 7],
            "work_times": ["00:00--11:59", "12:00--23:59"]
        }
    ]
    常规轮值/自定义（category=regular）
    [
        {
            "date": "2023-10-01",
            "work_times": ["00:00--11:59", "12:00--23:59"],
            "members": ["admin"]
        },
        {
            "date": "2023-10-02",
            "work_times": ["08:00--18:00"],
            "members": ["admin"]
        },
        {
            "date": "2023-10-03",
            "work_times": ["00:00--11:59", "12:00--23:59"],
            "members": ["admin"]
        }
    ]
    """

    name = models.CharField(verbose_name=_("轮值规则名称"), max_length=LEN_MIDDLE)
    monitor_duty_rule_id = models.IntegerField(verbose_name=_("监控轮值规则 ID"), default=0)
    priority = models.PositiveIntegerField(verbose_name=_("优先级"))
    is_enabled = models.BooleanField(verbose_name=_("是否启用"), default=True)
    effective_time = models.DateTimeField(verbose_name=_("生效时间"))
    end_time = models.DateTimeField(verbose_name=_("截止时间"), blank=True, null=True)
    category = models.CharField(verbose_name=_("轮值类型"), choices=DutyRuleCategory.get_choices(), max_length=LEN_SHORT)
    db_type = models.CharField(_("数据库类型"), choices=DBType.get_choices(), max_length=LEN_SHORT)
    duty_arranges = models.JSONField(_("轮值人员设置"))

    def save(self, *args, **kwargs):
        """
        保存轮值
        """
        # 1. 新建监控轮值
        params = {
            "name": f"{self.db_type}_{self.name}",
            "bk_biz_id": env.DBA_APP_BK_BIZ_ID,
            "effective_time": self.effective_time.strftime("%Y-%m-%d %H:%M:%S"),
            "end_time": self.end_time.strftime("%Y-%m-%d %H:%M:%S") if self.end_time else "",
            "labels": [self.db_type],
            "enabled": self.is_enabled,
            "category": self.category,
        }
        if self.category == DutyRuleCategory.REGULAR.value:
            params["duty_arranges"] = [
                {
                    "duty_time": [
                        {
                            "work_type": "monthly",
                            "work_days": [int(arrange["date"].split("-")[-1])],
                            "work_time": arrange["work_times"],
                        }
                    ],
                    "duty_users": [[{"id": member, "type": "user"} for member in arrange["members"]]],
                }
                for arrange in self.duty_arranges
            ]
        else:
            try:
                group_number = self.duty_arranges[0]["duty_number"]
            except (IndexError, ValueError):
                group_number = 1
            params.update(
                **{
                    "duty_arranges": [
                        {
                            "duty_time": [
                                {
                                    "work_type": arrange["work_type"],
                                    "work_days": arrange["work_days"],
                                    "work_time": arrange["work_times"],
                                    "period_settings": {
                                        "window_unit": "day",
                                        "duration": self.duty_arranges[0]["duty_day"],
                                    },
                                }
                            ],
                            "duty_users": [[{"id": member, "type": "user"} for member in arrange["members"]]],
                        }
                        for arrange in self.duty_arranges
                    ],
                    "group_type": "auto",
                    "group_number": group_number,
                }
            )
        #  2. 判断是否存量的轮值规则，如果是，则走更新流程
        is_old_rule = bool(self.monitor_duty_rule_id)
        if bool(self.monitor_duty_rule_id):
            params["id"] = self.monitor_duty_rule_id
        resp = BKMonitorV3Api.save_duty_rule(params)
        self.monitor_duty_rule_id = resp["id"]
        # 3. 判断是否需要变更用户组
        # 3.1 非老规则（即新建的规则）
        need_update_user_group = not is_old_rule
        # 3.2 调整了优先级的规则
        if self.pk:
            old_rule = DutyRule.objects.get(pk=self.pk)
            if old_rule.priority != self.priority:
                need_update_user_group = True
        # 4. 保存本地轮值规则
        super().save(*args, **kwargs)
        # 5. 变更告警组
        if need_update_user_group:
            for notice_group in NoticeGroup.objects.filter(is_built_in=True, db_type=self.db_type):
                notice_group.save()

    def delete(self, using=None, keep_parents=False):
        BKMonitorV3Api.delete_duty_rules({"ids": [self.monitor_duty_rule_id], "bk_biz_ids": [env.DBA_APP_BK_BIZ_ID]})
        super().delete()

    @classmethod
    def priority_distinct(cls) -> list:
        return list(cls.objects.values_list("priority", flat=True).distinct().order_by("-priority"))

    class Meta:
        verbose_name_plural = verbose_name = _("轮值规则")


class RuleTemplate(AuditedModel):
    """告警策略模板：just for export"""

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

    @classmethod
    def clear(cls, ids=None):
        """清理所有平台告警策略"""

        ids = list(cls.objects.all().values_list("monitor_policy_id", flat=True)) if not ids else ids.split(",")
        params = {"bk_biz_id": env.DBA_APP_BK_BIZ_ID, "ids": ids}
        response = BKMonitorV3Api.delete_alarm_strategy_v3(params, use_admin=True, raw=True)
        if not response.get("result"):
            logger.error("bkm_delete_alarm_strategy failed: params: %s\n response: %s", params, response)
            raise BkMonitorDeleteAlarmException(message=response.get("message"))

        cls.objects.all().delete()

    class Meta:
        verbose_name = _("告警策略实例")


class DispatchGroup(AuditedModel):
    """分派策略组"""

    bk_biz_id = models.IntegerField(verbose_name=_("业务ID, 0代表全业务"), default=PLAT_BIZ_ID, unique=True)
    monitor_dispatch_id = models.IntegerField(verbose_name=_("蓝鲸监控分派策略组ID"), default=0)
    # name = models.CharField(verbose_name=_("策略名称，全局唯一"), max_length=LEN_MIDDLE)
    # priority = models.PositiveIntegerField(verbose_name=_("监控策略优先级，跟随targets调整"))
    details = models.JSONField(verbose_name=_("策略模板详情"), default=dict)
    rules = models.JSONField(verbose_name=_("规则列表"), default=list)
    # is_synced = models.BooleanField(verbose_name=_("是否已同步到监控"), default=False)
    sync_at = models.DateTimeField(_("最近一次的同步时间"), null=True)

    class Meta:
        verbose_name = _("分派策略组")

    @classmethod
    def save_dispatch_group(cls, params):
        return BKMonitorV3Api.save_rule_group(params)

    @classmethod
    def get_rule_by_dbtype(cls, db_type, bk_biz_id):
        """根据db类型生成规则"""

        rule_mixin = {
            "actions": [
                {
                    "action_type": "notice",
                    "is_enabled": True,
                    "upgrade_config": {"is_enabled": False, "user_groups": [], "upgrade_interval": 0},
                }
            ],
            "alert_severity": 0,
            "additional_tags": [],
            "is_enabled": True,
        }

        conditions = []
        # 仅分派平台策略
        policies = MonitorPolicy.get_policies(db_type)

        # 排除无效的db类型，比如cloud
        if not policies:
            return {}

        conditions.append({"field": "alert.strategy_id", "value": policies, "method": "eq", "condition": "and"})
        user_groups = NoticeGroup.get_groups(bk_biz_id)

        # 业务级分派策略
        if bk_biz_id != PLAT_BIZ_ID:
            conditions.append({"field": "appid", "value": [str(bk_biz_id)], "method": "eq", "condition": "and"})

        return {
            "user_groups": [user_groups.get(db_type)],
            "conditions": conditions,
            **rule_mixin,
        }

    @classmethod
    def get_rules(cls, bk_biz_id=PLAT_BIZ_ID):
        rules = []

        notify_groups = NoticeGroup.objects.filter(is_built_in=True, bk_biz_id=bk_biz_id)
        for db_type in notify_groups.values_list("db_type", flat=True):
            rule = cls.get_rule_by_dbtype(db_type, bk_biz_id)

            if not rule:
                continue

            rules.append(rule)
        return rules

    def save(self, *args, **kwargs):
        """
        保存分派规则组
        """

        data = copy.deepcopy(BK_MONITOR_SAVE_DISPATCH_GROUP_TEMPLATE)
        data.update(
            {
                "name": _("DBM平台规则_勿动_{}").format(self.bk_biz_id),
                "bk_biz_id": env.DBA_APP_BK_BIZ_ID,
                # 请求参数格式错误：(priority) 当前业务下已经存在优先级别为(100)的分派规则组
                # 优先级必能重复，故叠加业务id作为优先级调整
                "priority": PLAT_PRIORITY if self.bk_biz_id == PLAT_BIZ_ID else APP_PRIORITY + self.bk_biz_id,
                "rules": self.rules,
            }
        )

        if self.monitor_dispatch_id:
            # data["id"] = self.monitor_dispatch_id
            data["assign_group_id"] = self.monitor_dispatch_id

            # 复用旧的rule_id
            for index, rule_id in enumerate(self.details.get("rules", [])[: len(self.rules)]):
                data["rules"][index]["id"] = rule_id

        # 调用监控接口写入
        resp = self.save_dispatch_group(data)
        self.monitor_dispatch_id = resp.get("assign_group_id", 0)

        self.details = resp
        self.sync_at = datetime.datetime.now()

        super().save(*args, **kwargs)


class MonitorPolicy(AuditedModel):
    """监控策略"""

    KEEPED_FIELDS = [*AuditedModel.AUDITED_FIELDS, "id", "is_enabled", "monitor_policy_id", "policy_status"]

    parent_id = models.IntegerField(verbose_name=_("父级策略ID，0代表父级"), default=0)
    parent_details = models.JSONField(verbose_name=_("父级策略模板详情，可用于还原"), default=dict)

    name = models.CharField(verbose_name=_("策略名称，全局唯一"), max_length=LEN_MIDDLE, unique=True)
    bk_biz_id = models.IntegerField(verbose_name=_("业务ID, 0代表全业务"), default=PLAT_BIZ_ID)

    db_type = models.CharField(
        _("DB类型"), choices=DBType.get_choices(), max_length=LEN_NORMAL, default=DBType.MySQL.value
    )

    details = models.JSONField(verbose_name=_("当前策略详情，可用于patch"), default=dict)
    monitor_indicator = models.CharField(verbose_name=_("监控指标名"), max_length=LEN_MIDDLE, default="")

    # 拆解部分details中的字段到外层
    # TODO: MethodEnum: eq|neq|include|exclude|regex|nregex
    # item[*].query_configs[*].agg_condition[*]
    # {
    #     "agg_condition": [
    #         {
    #             "key": "appid",
    #             "dimension_name": "dbm_meta app id",
    #             "value": [
    #                 "2"
    #             ],
    #             "method": "eq",
    #             "condition": "and"
    #         },
    #         {
    #             "key": "db_module",
    #             "dimension_name": "dbm_meta db module",
    #             "value": [
    #                 "zookeeper"
    #             ],
    #             "method": "eq",
    #             "condition": "and"
    #         }
    #         {
    #             "key": "cluster_domain",
    #             "dimension_name": "dbm_meta cluster domain",
    #             "value": [
    #                 "spider.spidertest.db"
    #             ],
    #             "method": "eq",
    #             "condition": "and"
    #         },
    #     ]
    # }
    # [{"level": platform, "rule":{"key": "appid/db_module/cluster_domain", "value": ["aa", "bb"]}}]
    targets = models.JSONField(verbose_name=_("监控目标"), default=list)
    target_level = models.CharField(
        verbose_name=_("监控目标级别，跟随targets调整"),
        choices=TargetLevel.get_choices(),
        max_length=LEN_NORMAL,
        default=TargetLevel.APP.value,
    )
    target_priority = models.PositiveIntegerField(verbose_name=_("监控策略优先级，跟随targets调整"))
    target_keyword = models.TextField(verbose_name=_("监控目标检索冗余字段"), default="")

    # [{"key": "abc", "method": "eq", "value": ["aa", "bb"], "condition": "and", "dimension_name": "abc"}]
    custom_conditions = models.JSONField(verbose_name=_("自定义过滤列表"), default=list)

    # Type 目前仅支持 Threshold
    # level: 1（致命）、2（预警）、3(提醒)
    # item[*].algorithms[*]:
    # {
    #    "id": 6212,
    #    "type": "Threshold",
    #    "level": 1,
    #    "config": [
    #      [
    #        {
    #          "method": "gte",
    #          "threshold": 90
    #        }
    #      ]
    #    ],
    #    "unit_prefix": "%"
    # }
    # [{"level": 1, "config": [[{"method": "gte", "threshold": 90}]], "unit_prefix": "%"}]
    test_rules = models.JSONField(verbose_name=_("检测规则"), default=list)
    # NoticeSignalEnum: notice.signal -> ["recovered", "abnormal", "closed", "ack", "no_data"]
    # item[*].no_data_config.is_enabled
    notify_rules = models.JSONField(verbose_name=_("通知规则"), default=list)
    # [1,2,3]
    notify_groups = models.JSONField(verbose_name=_("通知组"), default=list)
    # .notice.options.assign_mode = ["by_rule", "only_notice"]
    # assign_mode = models.JSONField(verbose_name=_("通知模式-分派|直接通知"), default=list)

    is_enabled = models.BooleanField(verbose_name=_("是否已启用"), default=True)

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

    monitor_policy_id = models.BigIntegerField(verbose_name=_("蓝鲸监控策略ID"), default=0)

    # 支持版本管理
    version = models.IntegerField(verbose_name=_("版本"), default=0)

    alert_source = models.CharField(
        verbose_name=_("告警数据来源"),
        max_length=LEN_SHORT,
        choices=AlertSourceEnum.get_choices(),
        default=AlertSourceEnum.TIME_SERIES,
    )

    class Meta:
        verbose_name = _("告警策略")

    def calc_from_targets(self):
        """根据目标计算优先级"""

        target_levels = list(map(lambda x: x["level"], self.targets))

        if TargetLevel.CUSTOM.value in target_levels:
            target_level = TargetLevel.CUSTOM.value
        elif TargetLevel.CLUSTER.value in target_levels:
            target_level = TargetLevel.CLUSTER.value
        elif TargetLevel.MODULE.value in target_levels:
            target_level = TargetLevel.MODULE.value
        elif TargetLevel.APP.value in target_levels:
            target_level = TargetLevel.APP.value
        else:
            target_level = TargetLevel.PLATFORM.value

        self.target_level = target_level
        self.target_priority = TARGET_LEVEL_TO_PRIORITY.get(target_level).value

        db_module_map = DBModule.db_module_map()
        self.target_keyword = ",".join(
            [
                db_module_map.get(int(value), value) if t["rule"]["key"] == TargetLevel.MODULE.value else value
                for t in self.targets
                for value in t["rule"]["value"]
            ]
        )

        self.local_save()

    def patch_bk_biz_id(self, details, bk_biz_id=env.DBA_APP_BK_BIZ_ID):
        """策略要跟随主机所属的cc业务，默认为dba业务"""
        host_biz_id = SystemSettings.get_exact_hosting_biz(bk_biz_id)
        details["bk_biz_id"] = host_biz_id
        return details

    def patch_target_and_metric_id(self, details):
        """监控目标/自定义事件和指标需要渲染
        metric_id: {bk_biz_id}_bkmoinitor_event_{event_data_id}
        """

        bkm_dbm_report = SystemSettings.get_setting_value(key=SystemSettingsEnum.BKM_DBM_REPORT.value)

        items = details["items"]
        # 事件类告警，无需设置告警目标，否则要求上报的数据必须携带服务实例id（告警目标匹配依据）
        for item in items:
            # 去掉目标范围，支持跨业务告警
            item["target"] = []
            # 更新监控目标为db_type对应的cmdb拓扑
            item["target"] = (
                [
                    [
                        {
                            "field": "host_topo_node",
                            "method": "eq",
                            "value": [
                                {"bk_inst_id": obj["bk_set_id"], "bk_obj_id": "set"}
                                for obj in AppMonitorTopo.get_set_by_dbtype(db_type=self.db_type)
                            ],
                        }
                    ]
                ]
                if self.alert_source == AlertSourceEnum.TIME_SERIES.value
                else []
            )

            for query_config in item["query_configs"]:
                # data_type_label: time_series | event(自定义上报，需要填充data_id)
                if query_config["data_type_label"] != "event":
                    continue

                # TODO: 自定义上报类告警策略如何支持非纳管业务?
                bkm_dbm_report_event = bkm_dbm_report["event"]
                query_config["metric_id"] = query_config["metric_id"].format(
                    bk_biz_id=env.DBA_APP_BK_BIZ_ID, event_data_id=bkm_dbm_report_event["data_id"]
                )
                query_config["result_table_id"] = query_config["result_table_id"].format(
                    bk_biz_id=env.DBA_APP_BK_BIZ_ID, event_data_id=bkm_dbm_report_event["data_id"]
                )

        return details

    def render_promql_tpl(self, promql):
        """渲染promql中的过滤表达式
        TODO: 从实例克隆时，这里的渲染将会失效
        """

        filter_expr = ""
        for target in self.targets:
            if target["level"] == TargetLevel.PLATFORM.value:
                continue

            target_rule = target["rule"]
            key, values = target_rule["key"], target_rule["value"]

            if len(values) == 1:
                filter_expr += f'{key}="{values}[0]"'
                filter_expr += ","

            # 多个值：a~="(1|2|3)"
            join_values = "|".join(map(lambda x: str(x), values))
            filter_expr += f'{key}~="({join_values})"'
            filter_expr += ","

        return promql.replace(PROMQL_FILTER_TPL, filter_expr)

    def patch_priority_and_agg_conditions(self, details):
        """将监控目标映射为所有查询的where条件"""

        self.calc_from_targets()

        # patch priority
        details["priority"] = self.target_priority

        # patch agg conditions
        agg_conditions = []
        for target in self.targets:
            if target["level"] == TargetLevel.PLATFORM.value:
                continue

            target_rule = target["rule"]
            agg_conditions.append(
                {
                    "key": target_rule["key"],
                    "dimension_name": TargetLevel.get_choice_label(target_rule["key"]),
                    "value": target_rule["value"],
                    "method": "eq",
                    "condition": "and",
                }
            )

        for item in details["items"]:
            for query_config in item["query_configs"]:
                if "agg_condition" in query_config:
                    # remove same type conditions
                    exclude_keys = list(map(lambda x: x["key"], self.custom_conditions)) + TargetLevel.get_values()
                    query_config_agg_condition = list(
                        filter(lambda cond: cond["key"] not in exclude_keys, query_config["agg_condition"])
                    )
                    query_config_agg_condition.extend(agg_conditions)
                    query_config_agg_condition.extend(self.custom_conditions)

                    # overwrite agg_condition
                    query_config["agg_condition"] = query_config_agg_condition
                else:
                    query_config["promql"] = self.render_promql_tpl(query_config["promql"])
                    logger.info("query_config.promql: %s", query_config["promql"])
                    # logger.error(_("{name}: 无法配置目标，暂不支持promql策略填充目标").format(**details))

        return details

    def patch_algorithms(self, details):
        """检测条件"""

        for rule in self.test_rules:
            rule["type"] = "Threshold"
            rule.pop("id", None)

        for item in details["items"]:
            item["algorithms"] = self.test_rules

        return details

    def patch_notice(self, details):
        """通知规则和通知对象"""
        # notify_rules -> notice.signal
        details["notice"]["signal"] = self.notify_rules

        # 克隆出来的策略，固定通知模式为：直接通知
        if self.parent_id:
            details["notice"]["options"]["assign_mode"] = ["only_notice"]

        # notice_groups -> notice.user_groups
        details["notice"]["user_groups"] = NoticeGroup.get_monitor_groups(group_ids=self.notify_groups)

        return details

    @classmethod
    def bkm_save_alarm_strategy(cls, params):
        response = BKMonitorV3Api.save_alarm_strategy_v3(params, use_admin=True, raw=True)
        if not response.get("result"):
            logger.error("bkm_save_alarm_strategy failed: params: %s\n response: %s", params, response)
            raise BkMonitorSaveAlarmException(message=response.get("message"))
        # logger.info("bkm_save_alarm_strategy success: %s", params["name"])
        return response["data"]

    def bkm_delete_alarm_strategy(self):
        params = {"bk_biz_id": self.bk_biz_id or env.DBA_APP_BK_BIZ_ID, "ids": [self.monitor_policy_id]}
        response = BKMonitorV3Api.delete_alarm_strategy_v3(params, use_admin=True, raw=True)
        if not response.get("result"):
            logger.error("bkm_delete_alarm_strategy failed: params: %s\n response: %s", params, response)
            raise BkMonitorDeleteAlarmException(message=response.get("message"))
        logger.info("bkm_delete_alarm_strategy success: %s", self.name)
        return response["data"]

    def local_save(self, *args, **kwargs):
        """仅保存到本地，不同步到监控"""
        super().save(*args, **kwargs)

    def patch_all(self):
        # model.targets -> agg_condition
        details = self.patch_priority_and_agg_conditions(self.details)

        # model.test_rules -> algorithms
        details = self.patch_algorithms(details)

        # model.notify_xxx -> notice
        details = self.patch_notice(details)

        # other
        details = self.patch_bk_biz_id(details)
        details = self.patch_target_and_metric_id(details)

        return details

    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        """保存策略对象的同时，同步记录到监控"""

        # step1. sync to model
        # 启停操作(["is_enabled"]) -> 跳过重复的patch
        details = self.details if update_fields == ["is_enabled"] else self.patch_all()

        # step2. sync to bkm
        res = self.bkm_save_alarm_strategy(details)

        # overwrite by bkm strategy details
        self.details = res
        self.monitor_policy_id = self.details["id"]
        self.sync_at = datetime.datetime.now()

        # 平台内置策略支持保存初始版本，用于恢复默认设置
        if self.pk is None and self.bk_biz_id == env.DBA_APP_BK_BIZ_ID:
            self.parent_details = self.details

        # step3. save to db
        super().save(force_insert, force_update, using, update_fields)

    def delete(self, using=None, keep_parents=False):
        # if self.bk_biz_id == PLAT_BIZ_ID:
        #     raise BuiltInNotAllowDeleteException

        if self.monitor_policy_id:
            self.bkm_delete_alarm_strategy()

        super().delete(using, keep_parents)

    def enable(self) -> bool:
        """启用：
        is_enabled:true -> save
        监控提供了批量启停的接口，若我们需要批量操作，这里可以切换接口为：
        推荐：update_partial_strategy_v3({
            "bk_biz_id":1,
            "ids":[23121],
            "edit_data":{
                "is_enabled":true,
                "notice_group_list":[4644]
            }
        })
        switch_alarm_strategy({"ids": [1], "is_enalbed": true/false})
        """
        self.is_enabled = True
        self.details.update(is_enabled=self.is_enabled)
        self.save(update_fields=["is_enabled"])

        return self.is_enabled

    def disable(self) -> bool:
        """禁用：is_enabled:false -> save"""
        self.is_enabled = False
        self.details.update(is_enabled=self.is_enabled)
        self.save(update_fields=["is_enabled"])

        return self.is_enabled

    @classmethod
    def clone(cls, params, username="system") -> dict:
        """克隆：patch -> create"""

        # params -> model
        policy = cls(**params)

        # transfer details from parent to self
        parent = cls.objects.get(id=policy.parent_id)

        policy.parent_details = copy.deepcopy(parent.details)
        policy.db_type = parent.db_type
        policy.monitor_indicator = parent.monitor_indicator

        policy.details = copy.deepcopy(parent.details)
        policy.details.pop("id", None)
        policy.details.update(name=policy.name)

        policy.creator = policy.updater = username
        policy.id = None

        policy.save()

        # 重新获取policy
        policy.refresh_from_db()

        return {"local_id": policy.id, "bkm_id": policy.monitor_policy_id}

    def update(self, params, username="system") -> dict:
        """更新：patch -> update"""

        update_fields = ["targets", "test_rules", "notify_rules", "notify_groups"]

        # param -> model
        for key in update_fields:
            setattr(self, key, params[key])

        # 可选参数
        if "custom_conditions" in params:
            self.custom_conditions = params["custom_conditions"]

        # update -> overwrite details
        self.creator = self.updater = username
        self.save()

        return {"local_id": self.id, "bkm_id": self.monitor_policy_id}

    def parse_details(self, details=None):
        """从模板反向提取部分参数"""

        details = details or self.details
        result = defaultdict(list)

        result["test_rules"] = [
            {
                "level": alg["level"],
                "config": alg["config"],
                "unit_prefix": alg["unit_prefix"],
            }
            # 这里假设item长度恒为1
            for alg in details["items"][0]["algorithms"]
        ]

        first_query_config = details["items"][0]["query_configs"][0]
        target_conditions = (
            list(filter(lambda cond: cond["key"] in TargetLevel.get_values(), first_query_config["agg_condition"]))
            if "agg_condition" in first_query_config
            else []
        )

        result["targets"] = [
            {"level": condition["key"], "rule": {"key": condition["key"], "value": condition["value"]}}
            for condition in target_conditions
        ]

        # 默认填充平台级目标
        if not result["targets"]:
            result["targets"].append(
                {"level": TargetLevel.PLATFORM.value, "rule": {"key": TargetLevel.PLATFORM.value, "value": []}}
            )

        result["notify_rules"] = details["notice"]["signal"]
        result["notify_groups"] = list(
            NoticeGroup.objects.filter(monitor_group_id__in=details["notice"]["user_groups"])
            .values_list("id", flat=True)
            .distinct()
        )

        return result

    def reset(self) -> dict:
        """恢复默认：parent_details -> save"""

        # patch by parent details
        self.details = self.parent_details
        self.details["id"] = self.monitor_policy_id
        self.details["name"] = self.name

        # fetch targets/test_rules/notify_rules/notify_groups from parent details
        for attr, value in self.parse_details().items():
            setattr(self, attr, value)

        self.save()

        return {"local_id": self.id, "bkm_id": self.monitor_policy_id}

    @classmethod
    def get_policies(cls, db_type, bk_biz_id=PLAT_BIZ_ID):
        """获取监控策略id列表"""
        return list(
            cls.objects.filter(db_type=db_type, bk_biz_id=bk_biz_id).values_list("monitor_policy_id", flat=True)
        )

    @staticmethod
    def bkm_search_event(
        bk_biz_ids: list,
        strategy_id: list,
        event_status: list = None,
        days=7,
        level=None,
        data_source=None,
        time_range=None,
        group_count=True,
    ):
        """事件搜索
        bk_biz_ids:[2] 必填

        id: 事件ID
        strategy_id: 事件关联的策略ID
        days: 查询最近几天内的时间，这个参数存在，time_range则失效
        time_range:"2020-02-26 00:00:00 -- 2020-02-28 23:59:59"
        conditions:
            level - 告警级别
                1 - 致命
                2 - 预警
                3 - 提醒
            event_status - 事件状态
                ABNORMAL - 未恢复
                CLOSED - 已关闭
                RECOVERED - 已恢复
            data_source: ["bk_monitor|time_series"]
                数据类型:
                time_series - 时序数据
                event - 事件
                log - 日志关键字
        返回格式:
         {
            "status": "ABNORMAL",
            "bk_biz_id": 2,
            "is_ack": false,
            "level": 1,
            "origin_alarm": {
              "data": {
                "record_id": "d751713988987e9331980363e24189ce.1574439900",
                "values": {
                  "count": 10,
                  "dtEventTimeStamp": 1574439900
                },
                "dimensions": {},
                "value": 10,
                "time": 1574439900
              },
              "trigger": {
                "level": "1",
                "anomaly_ids": [
                  "d751713988987e9331980363e24189ce.15744396",
                ]
              },
              "anomaly": {
                "1": {
                  "anomaly_message": "count >= 1.0, 当前值10.0",
                  "anomaly_time": "2019-11-22 16:31:06",
                  "anomaly_id": "d751713988987e9331980363e24189ce.1574439"
                }
              },
              "dimension_translation": {},
              "strategy_snapshot_key": "bk_bkmonitor.ee.cache.strategy.snapshot.88."
            },
            "target_key": "",
            "strategy_id": 88,
            "id": 1364253,
            "is_shielded": false,
            "event_id": "d751713988987e9331980363e24189ce.15744396",
            "create_time": "2019-11-22 16:31:07",
            "end_time": null,
            "begin_time": "2019-11-22 16:25:00",
            "origin_config": {},
            "p_event_id": ""
          }
        ]
        """

        # 默认搜索未恢复
        event_status = event_status or ["ABNORMAL"]
        condition_kwargs = {
            "strategy_id": strategy_id,
            "event_status": event_status,
            "level": level,
            "data_source": data_source,
        }

        # TODO: 单次查询上限5000条，若需要突破上限，需要循环查询
        params = {
            "bk_biz_ids": bk_biz_ids,
            "conditions": [
                {"key": cond_key, "value": cond_value}
                for cond_key, cond_value in condition_kwargs.items()
                if cond_value
            ],
            "days": days,
            "page": 1,
            "page_size": 5000,
        }

        # 精确范围查找
        if time_range:
            params["time_range"] = time_range
            params.pop("days")

        events = BKMonitorV3Api.search_event(params)

        # 需要根据app_id来拆分全局内置策略的告警数量
        if group_count:
            tmp = defaultdict(int)
            for event in events:
                app_id = event["origin_alarm"]["data"]["dimensions"].get("appid") or 0
                # 缺少业app_id维度的策略
                if not app_id:
                    logger.error("find bad appid event: %s", json.dumps(event))

                tmp[(event["strategy_id"], app_id)] += 1

            event_counts = defaultdict(dict)
            for (strategy_id, appid), event_count in tmp.items():
                event_counts[strategy_id][appid] = event_count
            # return dict(Counter(event["strategy_id"] for event in events))
            return event_counts

        return events
