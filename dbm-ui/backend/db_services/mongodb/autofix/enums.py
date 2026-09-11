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
from django.utils.translation import gettext_lazy as _

from blue_krill.data_types.enum import EnumField, StrStructuredEnum


class MongoAutofixCtlItem(StrStructuredEnum):
    """Mongo 后端自愈控制项"""

    ENABLE = EnumField("enable", _("总开关"))
    BIZ_WHITELIST = EnumField("biz_whitelist", _("业务白名单(逗号分隔)"))
    DOMAIN_WHITELIST = EnumField("domain_whitelist", _("域名白名单(逗号分隔)"))
    DELAY_MINUTES = EnumField("delay_minutes", _("监控延迟窗口分钟"))
    PEER_MIN_COUNT = EnumField("peer_min_count", _("旁观者最少人数"))
    ZONE_HOST_THRESHOLD = EnumField("zone_host_threshold", _("同园区异常主机数熔断阈值"))
    ZONE_PERCENT_THRESHOLD = EnumField("zone_percent_threshold", _("同园区异常占比熔断阈值"))
    CITY_HOST_THRESHOLD = EnumField("city_host_threshold", _("同城市异常主机数熔断阈值"))
    ENABLE_CONFIGSVR = EnumField("enable_configsvr", _("是否允许 configsvr 自愈"))
    DRY_RUN = EnumField("dry_run", _("仅发现不出单"))


class MongoAutofixStatus(StrStructuredEnum):
    """Mongo 后端自愈状态机"""

    DETECTED = EnumField("detected", _("已发现"))
    PRE_RUNNING = EnumField("pre_running", _("PRE确认中"))
    TICKETED = EnumField("ticketed", _("已出修复/替换单"))
    RUNNING = EnumField("running", _("修复/替换执行中"))
    SUCCESS = EnumField("success", _("成功"))
    FAIL = EnumField("fail", _("失败"))
    IGNORE = EnumField("ignore", _("忽略"))


class MongoAutofixConfirmResult(StrStructuredEnum):
    """PRE 确认结果"""

    DISK_RO = EnumField("disk_ro", _("数据盘只读"))
    MACHINE_DEAD = EnumField("machine_dead", _("机器不可达"))
    DISK_DEAD = EnumField("disk_dead", _("数据盘不可写"))
    PROCESS_BAD = EnumField("process_bad", _("进程异常"))
    LOGIN_OK = EnumField("login_ok", _("能登录仍异常"))
    IGNORED = EnumField("ignored", _("忽略"))
    AUTH_ERROR = EnumField("auth_error", _("鉴权失败"))


class MongoAutofixLogEvent(StrStructuredEnum):
    """自愈流水事件"""

    DETECTED = EnumField("detected", _("发现故障"))
    PRE_TICKET = EnumField("pre_ticket", _("创建PRE单据"))
    TRIAGE = EnumField("triage", _("PRE确认分叉"))
    FOLLOWUP_TICKET = EnumField("followup_ticket", _("创建修复/替换单据"))
    STATUS = EnumField("status", _("状态变更"))
    IGNORE = EnumField("ignore", _("忽略"))
    ERROR = EnumField("error", _("异常"))


# deal_status 非终态：同 IP 禁止并发 Core
MONGO_AUTOFIX_ACTIVE_STATUSES = frozenset(
    {
        MongoAutofixStatus.DETECTED.value,
        MongoAutofixStatus.PRE_RUNNING.value,
        MongoAutofixStatus.TICKETED.value,
        MongoAutofixStatus.RUNNING.value,
    }
)

# 副本集成员异常态（旁观者视角）
PEER_ABNORMAL_STATES = frozenset({6, 8})  # UNKNOWN / DOWN
PEER_HEALTHY_STATES = frozenset({1, 2, 7})  # PRIMARY / SECONDARY / ARBITER
