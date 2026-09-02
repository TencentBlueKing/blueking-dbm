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

# VictoriaMetrics 部署相关的常量集中定义，避免多处 magic string / magic number

# 命名空间前缀，最终形如 "{NAMESPACE_PREFIX}-{db_app_abbr}-{bk_biz_id}"
NAMESPACE_PREFIX = "victoriametrics"

# dbs 侧标识
STORAGE_ADDON_TYPE = "victoriametrics"
HA_TOPO_NAME = "cluster"
HA_TAGS = ["dbm", "victoriametrics"]

# 组件名（与 dbs 约定的 componentName 一致）
COMPONENT_VMINSERT = "vminsert"
COMPONENT_VMSELECT = "vmselect"
COMPONENT_VMSTORAGE = "vmstorage"

# 服务暴露相关
VMINSERT_SERVICE_NAME = "vminsert-clb"
VMSELECT_SERVICE_NAME = "vmselect-clb"
VMINSERT_PORT = 8480
VMSELECT_PORT = 8481

# CLB 名称后缀
VMINSERT_CLB_SUFFIX = "vminsert-clb"
VMSELECT_CLB_SUFFIX = "vmselect-clb"

# 域名前缀，最终形如 "{DOMAIN_PREFIX}.{cluster_name}.{db_app_abbr}.db"
VMINSERT_DOMAIN_PREFIX = "vminsert"
VMSELECT_DOMAIN_PREFIX = "vmselect"
