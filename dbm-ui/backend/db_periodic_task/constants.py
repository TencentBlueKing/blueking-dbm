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

# 任务状态轮询最大次数
MAX_QUERY_TASK_STATUS_TIMES = 5
# 任务轮询间隔时间
QUERY_TASK_STATUS_INTERVAL = 5
# backup task status success
BACKUP_TASK_SUCCESS = 4

# 原子性的获取列表所有值并清空
GET_AND_DELETE_SET_LUA = """
local elements = redis.call('SMEMBERS', KEYS[1])
redis.call('DEL', KEYS[1])
return elements
"""


class PeriodicTaskType(StrStructuredEnum):
    REMOTE = EnumField("remote", _("远程 API 周期任务"))
    LOCAL = EnumField("local", _("本地函数周期任务"))


class NoticeSignalEnum(StrStructuredEnum):
    recovered = EnumField("recovered", _("告警恢复时"))
    abnormal = EnumField("abnormal", _("告警触发时"))
    closed = EnumField("closed", _("告警关闭时"))
    ack = EnumField("ack", _("告警确认时"))
    no_data = EnumField("no_data", _("无数据告警"))


class FailoverDrillVersion(StrStructuredEnum):
    V1 = EnumField("v1", _("DBHA v1"))
    V2 = EnumField("v2", _("DBHA v2"))
    V1_V2 = EnumField("v1,v2", _("DBHA v1+v2"))


_FAILOVER_DRILL_VERSION_ATOMS = frozenset({FailoverDrillVersion.V1.value, FailoverDrillVersion.V2.value})


def parse_failover_drill_versions(version: str | None) -> frozenset[str]:
    """把配置里的 version 收成 {v1} / {v2} / {v1, v2}。空值或非法 token 视为仅 v1。"""
    if not version:
        return frozenset({FailoverDrillVersion.V1.value})
    parsed = {part.strip() for part in str(version).split(",") if part.strip()}
    if not parsed or parsed - _FAILOVER_DRILL_VERSION_ATOMS:
        return frozenset({FailoverDrillVersion.V1.value})
    return frozenset(parsed)


def failover_drill_has_v2(version: str | None) -> bool:
    return FailoverDrillVersion.V2.value in parse_failover_drill_versions(version)


def failover_drill_queue_version(version: str | None) -> str:
    """切换队列只认原子版本：含 v2 则查 v2，否则查 v1。"""
    if failover_drill_has_v2(version):
        return FailoverDrillVersion.V2.value
    return FailoverDrillVersion.V1.value


def canonical_failover_drill_version(version: str | None) -> str:
    parsed = parse_failover_drill_versions(version)
    if parsed == _FAILOVER_DRILL_VERSION_ATOMS:
        return FailoverDrillVersion.V1_V2.value
    if FailoverDrillVersion.V2.value in parsed:
        return FailoverDrillVersion.V2.value
    return FailoverDrillVersion.V1.value
