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
from django.utils.translation import ugettext_lazy as _

from blue_krill.data_types.enum import EnumField, StructuredEnum

# 任务状态轮询最大次数
MAX_QUERY_TASK_STATUS_TIMES = 5
# 任务轮询间隔时间
QUERY_TASK_STATUS_INTERVAL = 5
# backup task status success
BACKUP_TASK_SUCCESS = 4


class PeriodicTaskType(str, StructuredEnum):
    REMOTE = EnumField("remote", _("远程 API 周期任务"))
    LOCAL = EnumField("local", _("本地函数周期任务"))


class NoticeSignalEnum(str, StructuredEnum):
    recovered = EnumField("recovered", _("告警恢复时"))
    abnormal = EnumField("abnormal", _("告警触发时"))
    closed = EnumField("closed", _("告警关闭时"))
    ack = EnumField("ack", _("告警确认时"))
    no_data = EnumField("no_data", _("无数据告警"))
