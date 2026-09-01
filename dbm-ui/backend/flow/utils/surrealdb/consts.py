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

# SurrealDB 部署相关的常量集中定义，避免多处 magic string / magic number

# 命名空间前缀，最终形如 "{NAMESPACE_PREFIX}-{db_app_abbr}-{bk_biz_id}"
NAMESPACE_PREFIX = "surreal"

# dbs 侧标识
STORAGE_ADDON_TYPE = "surrealdb"
SINGLE_TOPO_NAME = "surreal-rocksdb"
SINGLE_TAGS = ["dbm", "surrealdb", "single"]

# HA 版本常量
HA_TOPO_NAME = "surreal-tikv"
HA_TAGS = ["dbm", "surrealdb", "ha"]

# 组件名（与 dbs 约定的 componentName 一致）
COMPONENT_SURREAL = "surreal"

# 服务暴露相关
SERVICE_NAME = "surreal-clb"
SURREALDB_PORT = 8000

# CLB 名称后缀
CLB_NAME_SUFFIX = "surrealdb-clb"

# 域名前缀，最终形如 "{DOMAIN_PREFIX}.{cluster_name}.{db_app_abbr}.db"
DOMAIN_PREFIX = "surrealdb"

# 异步 schedule 轮询相关
SCHEDULE_INTERVAL_SECONDS = 20
SCHEDULE_MAX_RETRIES = 15
