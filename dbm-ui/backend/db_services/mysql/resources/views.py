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
from collections import defaultdict

from django.utils.decorators import method_decorator
from django.utils.translation import ugettext_lazy as _
from django_filters import rest_framework as filters
from rest_framework import status
from rest_framework.response import Response

from backend.bk_web.swagger import common_swagger_auto_schema
from backend.bk_web.viewsets import AuditedModelViewSet, SystemViewSet
from backend.db_meta.models.cluster import Cluster
from backend.db_meta.models.db_module import DBModule
from backend.db_services.dbbase.resources import constants
from backend.db_services.dbbase.resources.constants import ResourceNodeType
from backend.db_services.dbbase.resources.serializers import ClusterSLZ, SearchResourceTreeSLZ
from backend.db_services.dbbase.resources.yasg_slz import ResourceTreeSLZ
from backend.iam_app.handlers.drf_perm import DBManageIAMPermission


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


@method_decorator(
    name="list",
    decorator=common_swagger_auto_schema(tags=[constants.RESOURCE_TAG]),
)
class ListResourceViewSet(AuditedModelViewSet):
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


class ResourceTreeViewSet(SystemViewSet):
    pagination_class = None

    def _get_custom_permissions(self):
        return [DBManageIAMPermission()]

    @common_swagger_auto_schema(
        operation_summary=_("获取资源拓扑树"),
        query_serializer=SearchResourceTreeSLZ(),
        responses={status.HTTP_200_OK: ResourceTreeSLZ()},
        tags=[constants.RESOURCE_TAG],
    )
    def get_resource_tree(self, request, bk_biz_id):
        cluster_type = self.params_validate(SearchResourceTreeSLZ)["cluster_type"]

        db_module_qset = DBModule.objects.filter(bk_biz_id=bk_biz_id, cluster_type=cluster_type)
        cluster_qset = Cluster.objects.filter(
            bk_biz_id=bk_biz_id,
            cluster_type=cluster_type,
            db_module_id__in=[db_module.db_module_id for db_module in db_module_qset],
        )

        module_clusters = defaultdict(list)
        for cluster in cluster_qset:
            module_clusters[cluster.db_module_id].append(
                {
                    "instance_name": cluster.name,
                    "instance_id": cluster.id,
                    "obj_id": ResourceNodeType.CLUSTER.value,
                    "obj_name": ResourceNodeType.CLUSTER.name,
                    "extra": {
                        "domain": cluster.immute_domain,
                        "version": cluster.major_version,
                    },
                }
            )

        tree = [
            {
                "obj_id": ResourceNodeType.MODULE.value,
                "obj_name": ResourceNodeType.MODULE.name,
                "instance_id": db_module.db_module_id,
                "instance_name": db_module.db_module_name,
                "children": module_clusters[db_module.db_module_id],
                "extra": {},
            }
            for db_module in db_module_qset
        ]
        return Response(tree)
