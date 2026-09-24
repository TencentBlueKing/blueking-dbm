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

# Qdrant 部署相关的常量集中定义，避免多处 magic string / magic number

# CLB 名称后缀，最终形如 "{cluster_name}-{bk_biz_id}-{CLB_NAME_SUFFIX}"
CLB_NAME_SUFFIX = "qdrant-clb"

# CLB 名称时间戳格式（精确到秒，避免名称过长）
CLB_NAME_TIME_FORMAT = "%Y%m%d%H%M%S"
