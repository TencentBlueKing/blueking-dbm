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
from dataclasses import dataclass
from typing import Any

from django.utils.translation import gettext_lazy as _

from backend.db_meta.api.cluster_state.fields.base import StoredStateField
from backend.db_meta.enums import StateValueType


@dataclass
class CapacityExtra:
    """容量明细，used / total 单位为字节，in_use 为保留两位小数的使用率百分比"""

    used: float
    total: float
    in_use: float


class CapacityField(StoredStateField):
    """
    集群容量使用率，取值为四舍五入后的整数百分比，没有采集到时为空（没有默认值）。
    由容量采集任务 sync_cluster_stat_by_cluster_type 调用 sync_cluster_capacity_state 批量写入，
    每次采集覆盖同业务同类型的全部集群
    """

    key = "capacity"
    name = _("容量使用率")
    help_text = _("集群容量使用率（%），由容量采集任务定期写入")
    value_type = StateValueType.NUMBER.value
    filterable = True
    extra_class = CapacityExtra

    def get_display(self, value: Any) -> str:
        """展示为百分比"""
        return "" if value is None else f"{value}%"
