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
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext as _
from django_filters import rest_framework as filters
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from backend.bk_web.swagger import common_swagger_auto_schema
from backend.bk_web.viewsets import AuditedModelViewSet, SystemViewSet
from backend.components import DBConfigApi
from backend.components.dbconfig.constants import FormatType, LevelName
from backend.db_meta.enums import ClusterType
from backend.db_meta.models.cluster import Cluster
from backend.flow.consts import ConfigTypeEnum, LevelInfoEnum

from ...dbbase.resources.constants import ResourceNodeType
from ...dbbase.resources.serializers import ClusterSLZ, SearchResourceTreeSLZ
from ...dbbase.resources.viewsets import ResourceViewSet as BaseResourceViewSet
from ...dbbase.resources.yasg_slz import ResourceTreeSLZ
from . import constants, yasg_slz


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

    def get_filterset_kwargs(self):
        return {"bk_biz_id": self.kwargs["bk_biz_id"]}


class ResourceViewSet(BaseResourceViewSet):
    @common_swagger_auto_schema(
        operation_summary=_("获取集群访问密码"),
        responses={status.HTTP_200_OK: yasg_slz.PasswordResourceSLZ},
        tags=[constants.RESOURCE_TAG],
    )
    @action(methods=["GET"], detail=True, url_path="get_password", serializer_class=None)
    def get_password(self, request, bk_biz_id: int, cluster_id: int):
        """
        获取集群密码相关信息
        """
        cluster = Cluster.objects.get(id=cluster_id)
        resp = DBConfigApi.query_conf_item(
            params={
                "bk_biz_id": str(bk_biz_id),
                "level_name": LevelName.CLUSTER,
                "level_value": cluster.immute_domain,
                "level_info": {"module": LevelInfoEnum.TendataModuleDefault},
                "conf_file": cluster.major_version,
                "conf_type": ConfigTypeEnum.DBConf,
                "namespace": cluster.cluster_type,
                "format": FormatType.MAP,
            }
        )

        resp_content = resp.get("content", {})

        # only for pulsar cluster
        token = ""
        if cluster.cluster_type == ClusterType.Pulsar:
            token = resp_content.get("broker.brokerClientAuthenticationParameters")

        return Response(
            {
                "cluster_name": cluster.name,
                "domain": cluster.immute_domain,
                "password": resp_content.get("password"),
                "username": resp_content.get("username"),
                "token": token,
            }
        )

    @common_swagger_auto_schema(
        operation_summary=_("获取集群节点列表信息"),
        responses={status.HTTP_200_OK: yasg_slz.NodesResourceSLZ},
        tags=[constants.RESOURCE_TAG],
    )
    @action(methods=["GET"], detail=True, url_path="list_nodes", serializer_class=None)
    def list_nodes(self, request, bk_biz_id: int, cluster_id: int):
        """获取集群节点列表信息"""

        data = self.paginator.paginate_list(
            request, bk_biz_id, self.query_class.list_nodes, {"cluster_id": cluster_id}
        )
        return self.get_paginated_response(data)


class ResourceTreeViewSet(SystemViewSet):
    serializer_class = SearchResourceTreeSLZ

    @common_swagger_auto_schema(
        operation_summary=_("获取资源拓扑树"),
        query_serializer=SearchResourceTreeSLZ(),
        responses={status.HTTP_200_OK: ResourceTreeSLZ()},
        tags=[constants.RESOURCE_TAG],
    )
    def get_resource_tree(self, request, bk_biz_id):
        cluster_type = self.params_validate(self.get_serializer_class())["cluster_type"]
        clusters = Cluster.objects.filter(
            bk_biz_id=bk_biz_id,
            cluster_type=cluster_type,
        )

        return Response(
            [
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
                for cluster in clusters
            ]
        )
