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
from blue_krill.data_types.enum import EnumField, StrStructuredEnum


class OracleWaitClass(StrStructuredEnum):
    """等待事件分类（Oracle 内置分类）"""

    ADMINISTRATIVE = EnumField("Administrative", "Administrative")
    APPLICATION = EnumField("Application", "Application")
    CLUSTER = EnumField("Cluster", "Cluster")
    COMMIT = EnumField("Commit", "Commit")
    CONCURRENCY = EnumField("Concurrency", "Concurrency")
    CONFIGURATION = EnumField("Configuration", "Configuration")
    IDLE = EnumField("Idle", "Idle")
    NETWORK = EnumField("Network", "Network")
    OTHER = EnumField("Other", "Other")
    SCHEDULER = EnumField("Scheduler", "Scheduler")
    SYSTEM_IO = EnumField("System I/O", "System I/O")
    USER_IO = EnumField("User I/O", "User I/O")


class OracleAwrFormat(StrStructuredEnum):
    """AWR 报告格式，值会拼入 awr_report_{fmt} 函数名；text 体积小，优先用于分析。"""

    TEXT = EnumField("text", "text")
    HTML = EnumField("html", "html")
