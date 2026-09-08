# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2021 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and limitations under the License.
"""
from backend.configuration.constants import DBType
from backend.db_services.dbbase.resources import serializers
from backend.db_services.kubernetes.resources.views import KubernetesResourceViewSet
from backend.iam_app.dataclass.actions import ActionEnum


class BaseVictoriaMetricsResourceViewSet(KubernetesResourceViewSet):
    query_serializer_class = serializers.ListKubernetesResourceSLZ
    db_type = DBType.K8sVictoriametrics

    list_perm_actions = [
        ActionEnum.K8S_VICTORIAMETRICS_VIEW,
        ActionEnum.K8S_VICTORIAMETRICS_EDIT,
        ActionEnum.K8S_VICTORIAMETRICS_DESTROY,
        ActionEnum.K8S_VICTORIAMETRICS_ENABLE_DISABLE,
        ActionEnum.K8S_VICTORIAMETRICS_MANAGE,
    ]
    list_instance_perm_actions = [ActionEnum.K8S_VICTORIAMETRICS_VIEW]
