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
import logging
from collections import defaultdict

from django.db import models
from django.utils.translation import gettext_lazy as _

from backend.bk_web.constants import LEN_LONG, LEN_MIDDLE, LEN_NORMAL, LEN_SHORT
from backend.bk_web.models import AuditedModel
from backend.configuration.constants import PLAT_BIZ_ID, DBType, SystemSettingsEnum
from backend.db_monitor.constants import TARGET_LEVEL_TO_PRIORITY, GroupType, PolicyStatus, TargetLevel, TargetPriority

from ... import env
from ...components import BKMonitorV3Api
from ..exceptions import BkMonitorDeleteAlarmException, BkMonitorSaveAlarmException

__all__ = ["NoticeGroup", "AlertRule", "RuleTemplate", "DispatchGroup", "MonitorPolicy"]

from ...configuration.models import SystemSettings

logger = logging.getLogger("root")


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
    parent_details = models.JSONField(verbose_name=_("父级策略模板详情，可用于还原"), default=dict)

    name = models.CharField(verbose_name=_("策略名称，全局唯一"), max_length=LEN_MIDDLE, unique=True)
    bk_biz_id = models.IntegerField(verbose_name=_("业务ID, 0代表全业务"), default=PLAT_BIZ_ID)

    db_type = models.CharField(
        _("DB类型"), choices=DBType.get_choices(), max_length=LEN_NORMAL, default=DBType.MySQL.value
    )

    details = models.JSONField(verbose_name=_("当前策略详情，可用于patch"), default=dict)

    # 拆解部分details中的字段到外层
    # TODO: MethodEnum: eq|neq|include|exclude|regex|nregex
    # item[*].query_configs[*].agg_condition[*]
    # {
    #     "agg_condition": [
    #         {
    #             "key": "app_id",
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
    # [{"level": platform, "rule":{"key": "app_id/db_module/cluster_domain", "value": ["aa", "bb"]}}]
    targets = models.JSONField(verbose_name=_("监控目标"), default=dict)
    target_level = models.CharField(
        verbose_name=_("监控目标级别，跟随targets调整"),
        choices=TargetLevel.get_choices(),
        max_length=LEN_NORMAL,
        default=TargetLevel.APP.value,
    )
    target_priority = models.PositiveIntegerField(verbose_name=_("监控策略优先级，跟随targets调整"))
    target_keyword = models.TextField(verbose_name=_("监控目标检索冗余字段"), default="")

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
    test_rules = models.JSONField(verbose_name=_("检测规则"), default=dict)
    # NoticeSignalEnum: notice.signal -> ["recovered", "abnormal", "closed", "ack", "no_data"]
    # item[*].no_data_config.is_enabled
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

        self.target_keyword = ",".join(
            [str(value) for target_level in self.targets for value in target_level["rule"]["value"]]
        )

        self.local_save()

    def patch_bk_biz_id(self, details, bk_biz_id=env.DBA_APP_BK_BIZ_ID):
        details["bk_biz_id"] = self.bk_biz_id or bk_biz_id
        return details

    def patch_notice_group(self, details):
        """"TODO: 告警组"""

        # 用最新告警组覆盖模板中的
        details["notice"]["user_groups"] = NoticeGroup.get_monitor_groups(db_type=self.db_type)
        return details

    def patch_metric_id(self, details):
        """自定义事件和指标需要渲染
        metric_id: {bk_biz_id}_bkmoinitor_event_{event_data_id}
        """

        bkm_dbm_report = SystemSettings.get_setting_value(key=SystemSettingsEnum.BKM_DBM_REPORT.value)

        items = details["items"]
        for item in items:
            for query_config in item["query_configs"]:
                if "custom.event" not in query_config["metric_id"]:
                    continue
                query_config["metric_id"] = query_config["metric_id"].format(
                    bk_biz_id=env.DBA_APP_BK_BIZ_ID, event_data_id=bkm_dbm_report["event"]["data_id"]
                )
                query_config["result_table_id"] = query_config["result_table_id"].format(
                    bk_biz_id=env.DBA_APP_BK_BIZ_ID, event_data_id=bkm_dbm_report["event"]["data_id"]
                )
        return details

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
                    query_config_agg_condition = list(
                        filter(lambda cond: cond["key"] not in TargetLevel.get_values(), query_config["agg_condition"])
                    )
                    query_config_agg_condition.extend(agg_conditions)
                    # overwrite agg_condition
                    query_config["agg_condition"] = query_config_agg_condition
                else:
                    logger.error(_("{name}: 无法配置目标，暂不支持promql策略填充目标").format(**details))

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
        """TODO: 依赖告警组的落地规则"""
        # notify_rules -> notice.signal
        details["notice"]["signal"] = self.notify_rules

        # notice_groups -> notice.user_groups
        details["notice"]["user_groups"] = self.notify_groups

        return details

    @classmethod
    def bkm_save_alarm_strategy(cls, params):
        response = BKMonitorV3Api.save_alarm_strategy_v3(params, use_admin=True, raw=True)
        if not response.get("result"):
            logger.error("bkm_save_alarm_strategy failed: params: %s\n response: %s", params, response)
            raise BkMonitorSaveAlarmException(message=response.get("message"))
        logger.info("bkm_save_alarm_strategy success: %s", params["name"])
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
        details = self.patch_notice_group(details)
        details = self.patch_metric_id(details)

        return details

    def save(self, *args, **kwargs):
        """保存策略对象的同时，同步记录到监控"""

        # step1. sync to model
        details = self.patch_all()

        # step2. sync to bkm
        res = self.bkm_save_alarm_strategy(details)

        # overwrite by bkm strategy details
        # if not self.pk:
        #     pass

        self.details = res
        self.monitor_policy_id = self.details["id"]

        self.is_synced = True
        self.sync_at = datetime.datetime.now()

        # step3. save to db
        super().save(*args, **kwargs)

    def delete(self, using=None, keep_parents=False):
        if self.is_synced and self.monitor_policy_id:
            self.bkm_delete_alarm_strategy()

        super().delete(using, keep_parents)

    def enable(self) -> bool:
        """启用：is_enabled:true -> save"""
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
        policy.details = copy.deepcopy(parent.details)
        policy.db_type = parent.db_type
        policy.details.pop("id", None)
        policy.details.update(name=policy.name)
        policy.creator = policy.updater = username
        policy.id = None

        # obj.calc_from_targets()

        # create -> overwrite details
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
        # self.calc_from_targets()

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
        # todo: 这里的user_groups可能需要转换为本地的notify_group
        result["notify_groups"] = details["notice"]["user_groups"] or [0]

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

    class Meta:
        verbose_name = _("告警策略")
