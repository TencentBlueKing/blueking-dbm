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


class KafkaDiskGrowthRule(StrStructuredEnum):
    """Kafka磁盘持续增长的触发规则"""

    CONTINUOUS_NEW_HIGH = EnumField("continuous_new_high", _("持续创新高"))
    SINGLE_DAY_JUMP = EnumField("single_day_jump", _("单日跳涨"))


class KafkaDiskGrowthRunKind(StrStructuredEnum):
    """巡检运行时段：早上用昨天的完整峰值，下午用今天截至当时的峰值"""

    MORNING = EnumField("morning", _("早间巡检"))
    AFTERNOON = EnumField("afternoon", _("午后巡检"))


class KafkaDiskGrowthAiStatus(StrStructuredEnum):
    """命中集群的 AI 分析状态"""

    PENDING = EnumField("pending", _("分析中"))
    SUCCESS = EnumField("success", _("已完成"))
    FAILED = EnumField("failed", _("分析失败"))
    SKIPPED = EnumField("skipped", _("已跳过"))
    NOT_SUBMITTED = EnumField("not_submitted", _("未提交"))
