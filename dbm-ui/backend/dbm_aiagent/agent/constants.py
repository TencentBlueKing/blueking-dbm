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


class DBMAgentCode(StrStructuredEnum):
    DBM = EnumField("ai-am", _("DBM 主智能体"))
    LOG_ANALYSIS = EnumField("ai-loganalysis", _("日志分析智能体"))
    MYSQL_SLOW_SQL_TUNER = EnumField("ai-sql-tune", _("MySQL 慢查询调优智能体"))
    MYSQL_SLOW_LOGS_QUERY = EnumField("ai-mysql-slowlog", _("MySQL慢日志分析智能体"))
