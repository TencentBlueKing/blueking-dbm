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
from django_filters import rest_framework as filters

from backend.bk_web.viewsets import AuditedModelViewSet
from backend.db_meta.models.cluster import Cluster
from backend.iam_app.handlers.drf_perm import DBManageIAMPermission

from ...dbbase.resources.serializers import ClusterSLZ


class ResourceFilterBackend(filters.DjangoFilterBackend):
    def get_filterset_kwargs(self, request, queryset, view):
        kwargs = super().get_filterset_kwargs(request, queryset, view)

        # merge filterset kwargs provided by view class
        if hasattr(view, "get_filterset_kwargs"):
            kwargs.update(view.get_filterset_kwargs())

        return kwargs


class ResourceFilter(filters.FilterSet):
    bk_biz_id = filters.NumberFilter(field_name="bk_biz_id", lookup_expr="exact")
    db_module_id = filters.NumberFilter(field_name="db_module_id", lookup_expr="exact")

    class Meta:
        model = Cluster
        fields = ["bk_biz_id", "db_module_id"]

    def __init__(self, *args, bk_biz_id=None, **kwargs):
        """将路径参数 bk_biz_id 添加到 QueryDict"""
        data = kwargs["data"].copy()
        data.update({"bk_biz_id": bk_biz_id})
        kwargs["data"] = data

        super().__init__(*args, **kwargs)


# TODO: 这个方法有在使用吗？
class BaseListResourceViewSet(AuditedModelViewSet):
    """提供资源(集群)通用属性的查询. 这些属性与集群类型无关, 如集群名, 集群创建者等"""

    queryset = Cluster.objects.all()
    serializer_class = ClusterSLZ
    filter_backends = (ResourceFilterBackend,)
    filterset_class = ResourceFilter
    pagination_class = None

    def _get_custom_permissions(self):
        return [DBManageIAMPermission()]

    def get_filterset_kwargs(self):
        return {"bk_biz_id": self.kwargs["bk_biz_id"]}
