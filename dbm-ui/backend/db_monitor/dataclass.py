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

from backend.db_monitor.constants import MonitorEventType


@dataclass
class BaseAutoFixFailDimension:
    """
    基础自愈失败维度
    这些维度会随事件上报到监控，并且制作监控策略的时候也可以用到这些维度
    """

    appid: int
    bk_biz_name: str
    ticket_id: int


@dataclass
class MySQLAutoFixFailDimension(BaseAutoFixFailDimension):
    """mysql故障自愈监控事件维度"""

    ip: str
    cluster_domain: str
    machine_type: str
    instance_role: str


@dataclass
class MonitorEvent:
    # 事件名称
    event_name: MonitorEventType
    # 事件内容，其中content必填: "event": {"content": "xxx"}
    event: dict
    # 事件维度
    dimension: BaseAutoFixFailDimension
