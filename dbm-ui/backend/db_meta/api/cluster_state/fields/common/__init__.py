# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

平台可选字段集合，按数据来源拆分：

- cluster：集群基础字段（phase / status），位于 CommonClusterStateSchema
- ticket：运行中单据，位于 CommonClusterStateSchema
- dbha：DBHA 屏蔽开关，MySQL 组件按需引入
- capacity：容量使用率，MySQL 组件按需引入
- portrait：健康报告，MySQL 组件按需引入
"""
from .capacity import CapacityExtra, CapacityField
from .cluster import PhaseField, StatusField
from .dbha import DBHA_DISABLED_FOREVER, DBHADisabledDetail, DBHADisabledField
from .independently_hosted import IndependentlyHostedField
from .portrait import PortraitReportDetail, PortraitReportField
from .ticket import RunningTicketField

__all__ = [
    "DBHA_DISABLED_FOREVER",
    "CapacityExtra",
    "CapacityField",
    "DBHADisabledDetail",
    "DBHADisabledField",
    "PhaseField",
    "PortraitReportDetail",
    "PortraitReportField",
    "RunningTicketField",
    "StatusField",
    "IndependentlyHostedField",
]
