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
import os

from blue_krill.data_types.enum import EnumField, StructuredEnum
from django.conf import settings
from django.utils.translation import ugettext as _

DB_MONITOR_TPLS_DIR = os.path.join(settings.BASE_DIR, "backend/db_monitor/tpls")
TPLS_COLLECT_DIR = os.path.join(DB_MONITOR_TPLS_DIR, "collect")
TPLS_ALARM_DIR = os.path.join(DB_MONITOR_TPLS_DIR, "alarm")

SWAGGER_TAG = "db_monitor"


class GroupType(str, StructuredEnum):
    """告警组类别: 平台级->业务级->集群级->一次性"""

    PLATFORM = EnumField("PLATFORM", _("platform"))
    APP = EnumField("APP", _("app"))
    CLUSTER = EnumField("CLUSTER", _("cluster"))
    SINGLE = EnumField("SINGLE", _("single"))


class DutyRuleCategory(str, StructuredEnum):
    """轮值规则分类"""

    REGULAR = EnumField("regular", _("固定值班"))
    HANDOFF = EnumField("handoff", _("交替轮值"))


class TargetLevel(str, StructuredEnum):
    """告警策略类别: 平台级->业务级->模块级->集群级->实例级
    ROLE: 角色不确定所处的位置
    CUSTOM: 用于表达额外过滤条件
    """

    PLATFORM = EnumField("platform", _("platform"))
    APP = EnumField("appid", _("app id"))
    MODULE = EnumField("db_module", _("db module"))
    CLUSTER = EnumField("cluster_domain", _("cluster domain"))
    CUSTOM = EnumField("custom", _("custom"))


class TargetPriority(int, StructuredEnum):
    """监控策略优先级: 0-10000"""

    PLATFORM = EnumField(0, _("platform"))
    APP = EnumField(1, _("app id"))
    MODULE = EnumField(10, _("db module"))
    CLUSTER = EnumField(100, _("cluster domain"))
    CUSTOM = EnumField(5000, _("custom"))


TARGET_LEVEL_TO_PRIORITY = {
    TargetLevel.PLATFORM.value: TargetPriority.PLATFORM,
    TargetLevel.APP.value: TargetPriority.APP,
    TargetLevel.MODULE.value: TargetPriority.MODULE,
    TargetLevel.CLUSTER.value: TargetPriority.CLUSTER,
    TargetLevel.CUSTOM.value: TargetPriority.CUSTOM,
}


class PolicyStatus(str, StructuredEnum):
    """监控策略状态"""

    VALID = EnumField("valid", _("有效"))
    TARGET_INVALID = EnumField("target_invalid", _("监控目标已失效"))


class OperatorEnum(str, StructuredEnum):
    """比较操作符"""

    EQ = EnumField("eq", _("等于"))
    NEQ = EnumField("neq", _("不等于"))
    LT = EnumField("lt", _("小于"))
    GT = EnumField("gt", _("大于"))
    LTE = EnumField("lte", _("小于等于"))
    GTE = EnumField("gte", _("大于等于"))


class AlertLevelEnum(int, StructuredEnum):
    """告警级别"""

    HIGH = EnumField(1, _("致命"))
    MID = EnumField(2, _("预警"))
    LOW = EnumField(3, _("提醒"))


class AlertSourceEnum(str, StructuredEnum):
    """告警数据来源"""

    TIME_SERIES = EnumField("time_series", _("时序数据"))
    EVENT = EnumField("event", _("事件数据"))
    LOG = EnumField("log", _("日志关键字"))


class DetectAlgEnum(str, StructuredEnum):
    """检测算法"""

    THRESHOLD = EnumField("Threshold", _("阈值检测"))


class NoticeWayEnum(str, StructuredEnum):
    """通知方式"""

    BY_RULE = EnumField("by_rule", _("基于分派规则通知"))
    ONLY_NOTICE = EnumField("only_notice", _("基于告警组直接通知"))


# 非ui方式监控策略模板占位符
PROMQL_FILTER_TPL = "__COND__"

# 蓝鲸监控保存用户组模板
DEFAULT_ALERT_NOTICE = [
    {
        "time_range": "00:00:00--23:59:59",
        "notify_config": [
            {"notice_ways": [{"name": "rtx"}], "level": 3},
            {"notice_ways": [{"name": "rtx"}, {"name": "sms"}], "level": 2},
            {"notice_ways": [{"name": "rtx"}, {"name": "voice"}], "level": 1},
        ],
    }
]

BK_MONITOR_SAVE_USER_GROUP_TEMPLATE = {
    "name": "",
    "desc": "",
    "need_duty": False,
    "duty_arranges": [{"duty_type": "always", "work_time": "always", "users": []}],
    "alert_notice": DEFAULT_ALERT_NOTICE,
    "action_notice": [
        {
            "time_range": "00:00:00--23:59:00",
            "notify_config": [
                {"phase": 3, "notice_ways": [{"name": "mail"}]},
                {"phase": 2, "notice_ways": [{"name": "mail"}]},
                {"phase": 1, "notice_ways": [{"name": "mail"}]},
            ],
        }
    ],
    "channels": ["user"],
    "bk_biz_id": 0,
}

# 分派优先级定义
PLAT_PRIORITY = 100
APP_PRIORITY = 1000

# 分派规则模板
BK_MONITOR_SAVE_DISPATCH_GROUP_TEMPLATE = {
    "id": 0,
    "bk_biz_id": 0,
    "priority": PLAT_PRIORITY,
    "name": _("平台级分派给业务"),
    "rules": [
        {
            "id": 2,
            "user_groups": [],
            "conditions": [
                {"field": "alert.strategy_id", "value": ["95"], "method": "eq", "condition": "and"},
                {"field": "appid", "value": ["1", "2", "3"], "method": "eq", "condition": "and"},
            ],
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
        },
    ],
}

MONITOR_EVENTS = "monitor_events"
