# -*- coding:utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""

from django.utils.translation import ugettext_lazy as _
from django_filters import rest_framework as filters

from backend.db_meta.models.spec import ClusterDeployPlan, Spec


class SpecListFilter(filters.FilterSet):
    spec_name = filters.CharFilter(field_name="spec_name", lookup_expr="icontains", label=_("规格名称"))
    desc = filters.CharFilter(field_name="desc", lookup_expr="icontains", label=_("描述"))
    spec_cluster_type = filters.CharFilter(field_name="spec_cluster_type", lookup_expr="exact", label=_("规格集群类型"))
    spec_machine_type = filters.CharFilter(field_name="spec_machine_type", lookup_expr="exact", label=_("规格机器类型"))

    class Meta:
        model = Spec
        fields = ["spec_name", "spec_cluster_type", "spec_machine_type", "desc"]


class ClusterDeployPlanFilter(filters.FilterSet):
    name = filters.CharFilter(field_name="name", lookup_expr="icontains", label=_("Redis部署方案名称"))
    cluster_type = filters.CharFilter(field_name="cluster_type", lookup_expr="exact", label=_("Redis集群类型"))

    class Meta:
        model = ClusterDeployPlan
        fields = ["name", "cluster_type"]
