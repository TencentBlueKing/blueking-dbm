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
from django.utils.translation import gettext as _
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from backend.bk_web.swagger import common_swagger_auto_schema
from backend.bk_web.viewsets import SystemViewSet
from backend.db_meta.models.cluster import Cluster
from backend.db_services.bigdata.resources.views import (
    decorator_cluster_permission_field,
    decorator_nodes_permission_field,
)
from backend.db_services.dbbase.resources.constants import ResourceNodeType
from backend.db_services.dbbase.resources.serializers import SearchResourceTreeSLZ
from backend.db_services.dbbase.resources.views import BaseListResourceViewSet
from backend.db_services.dbbase.resources.viewsets import ResourceViewSet
from backend.db_services.dbbase.resources.yasg_slz import ResourceTreeSLZ
from backend.db_services.kubernetes.resources import constants
from backend.db_services.kubernetes.resources.query import KubernetesBaseListRetrieveResource
from backend.db_services.kubernetes.resources.serializers import (
    ClusterOperationLogSerializer,
    KubernetesHscalingSerializer,
    KubernetesRestartSerializer,
    KubernetesTopoGraphSerializer,
    NodeListSerializer,
)
from backend.iam_app.dataclass import ResourceEnum
from backend.iam_app.dataclass.actions import ActionEnum
from backend.iam_app.handlers.drf_perm.base import DBManagePermission
from backend.iam_app.handlers.permission import Permission


@method_decorator(
    name="list",
    decorator=common_swagger_auto_schema(tags=[constants.RESOURCE_TAG]),
)
class ListResourceViewSet(BaseListResourceViewSet):
    pass


class KubernetesResourceViewSet(ResourceViewSet):
    query_class = KubernetesBaseListRetrieveResource

    @common_swagger_auto_schema(
        operation_summary=_("获取集群节点列表信息"),
        query_serializer=NodeListSerializer(),
        tags=[constants.RESOURCE_TAG],
    )
    @decorator_nodes_permission_field()
    @action(methods=["GET"], detail=True, url_path="list_nodes", serializer_class=NodeListSerializer)
    def list_nodes(self, request, *args, **kwargs):
        data = self.params_validate(self.get_serializer_class())
        """获取集群节点列表信息"""
        data = self.paginator.paginate_list(request, data["bk_biz_id"], self.query_class.list_nodes, data)
        return self.get_paginated_response(data)

    @decorator_cluster_permission_field()
    @Permission.decorator_external_permission_field(
        param_field=lambda d: d["view_class"].db_type,
        actions=[ActionEnum.ACCESS_ENTRY_EDIT],
        resource_meta=ResourceEnum.DBTYPE,
    )
    def list(self, request, bk_biz_id: int, *args, **kwargs):
        return super().list(request, bk_biz_id)

    @common_swagger_auto_schema(
        operation_summary=_("获取集群操作记录"),
        tags=[constants.RESOURCE_TAG],
    )
    @action(
        methods=["GET"], detail=False, url_path="get_operation_log", serializer_class=ClusterOperationLogSerializer
    )
    def get_operation_log(self, request, *args, **kwargs):
        """获取集群操作日志"""
        data = self.params_validate(self.get_serializer_class())
        data = self.paginator.paginate_list(request, data["bk_biz_id"], self.query_class.get_operation_log, data)
        return self.get_paginated_response(data)

    @common_swagger_auto_schema(
        operation_summary=_("获取集群拓扑"),
        tags=[constants.RESOURCE_TAG],
    )
    @action(methods=["GET"], detail=True, url_path="get_topo_graph", serializer_class=KubernetesTopoGraphSerializer)
    def get_topo_graph(self, request, bk_biz_id: int, cluster_id: int):
        """获取拓扑图"""
        data = self.params_validate(self.get_serializer_class())
        return Response(
            self.query_class.get_topo_graph(bk_biz_id, cluster_id, data["bcs_cluster_name"], data["namespace"])
        )

    @common_swagger_auto_schema(
        operation_summary=_("重启组件"),
        tags=[constants.RESOURCE_TAG],
    )
    @action(methods=["POST"], detail=False, url_path="restart_component", serializer_class=KubernetesRestartSerializer)
    def restart_component(self, request, *args, **kwargs):
        """重启组件"""
        data = self.params_validate(self.get_serializer_class())
        return Response(self.query_class.restart_component(data))

    @common_swagger_auto_schema(
        operation_summary=_("组件水平扩缩容"),
        tags=[constants.RESOURCE_TAG],
    )
    @action(
        methods=["POST"], detail=False, url_path="restart_component", serializer_class=KubernetesHscalingSerializer
    )
    def hscaling_component(self, request, *args, **kwargs):
        data = self.params_validate(self.get_serializer_class())
        return Response(self.query_class.hscaling_component(data))


class ResourceTreeViewSet(SystemViewSet):
    serializer_class = SearchResourceTreeSLZ

    def _get_custom_permissions(self):
        return [DBManagePermission()]

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
