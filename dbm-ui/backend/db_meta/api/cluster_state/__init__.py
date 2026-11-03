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
# 集群状态框架：以集群类型为中心声明状态字段，统一提供列表展示、过滤、下钻和业务读写。
# - 使用状态（读、写、过滤）：只用 ClusterStateService，见 service.py
# - 新增状态字段：继承 NativeStateField（数据已有专表）或 StoredStateField（存 ClusterState 竖表），
#   约定见 fields/base.py 中 StateField 的说明，参考实现见 fields/common.py
# - 把字段挂到集群类型：在 schemas/<组件>.py 中声明 ClusterStateSchema 并用 register_state_schema 注册，
#   见 schemas/base.py；列表默认展示列在 DEFAULT_CLUSTER_STATE_DISPLAY_FIELDS 配置
# - 声明自检：manage.py check（checks.py）；测试基类：backend/tests/db_meta/api/cluster_state/base.py
from .fields import NativeStateField, StateField, StoredStateField
from .registry import register_state_schema
from .schemas import ClusterStateSchema, CommonClusterStateSchema
from .service import ClusterStateService
from .values import StateDetail, StateValue
