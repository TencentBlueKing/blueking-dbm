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
import os

from django.conf import settings

DEFAULT_ORG_ID = 1
DEFAULT_ORG_NAME = "dbm"

DASHBOARD_JSON_PATH = os.path.join(settings.BASE_DIR, "backend/bk_dataview/dashboards/json")
DASHBOARD_APP_ID = "dbm"

# k8s 组件指标中用于定位集群的维度，代理层按这些维度鉴权
# namespace 形如 {name}-{biz_name}-{biz_id}
K8S_NAMESPACE_KEY = "namespace"
# DBM K8S 集群名
K8S_INSTANCE_KEY = "app_kubernetes_io_instance"
# BCS 集群 ID
K8S_BCS_CLUSTER_ID_KEY = "bcs_cluster_id"
K8S_AUTH_KEYS = (K8S_NAMESPACE_KEY, K8S_INSTANCE_KEY, K8S_BCS_CLUSTER_ID_KEY)
