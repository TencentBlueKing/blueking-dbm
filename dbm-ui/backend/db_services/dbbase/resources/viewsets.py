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
from functools import wraps
from typing import Callable

from rest_framework.decorators import action
from rest_framework.response import Response

from backend.bk_web.viewsets import SystemViewSet
from backend.iam_app.dataclass import ResourceEnum
from backend.iam_app.dataclass.actions import ActionEnum
from backend.iam_app.handlers.drf_perm.base import DBManagePermission
from backend.iam_app.handlers.drf_perm.cluster import ClusterDetailPermission
from backend.iam_app.handlers.permission import Permission

from . import serializers
from .pagination import ResourceLimitOffsetPagination
from .query import ListRetrieveResource


def decorator_cluster_instance_permission_field(
    id_field: Callable = lambda item: item["id"],
    data_field: Callable = lambda data_list: data_list,
    always_allowed: Callable = lambda item: False,
    many: bool = True,
):
    def wrapper(view_func):
        @wraps(view_func)
        def wrapped_view(*args, **kwargs):
            db_type = args[0].db_type.upper()

            response = view_func(*args, **kwargs)
            if not getattr(ActionEnum, f"{db_type}_VIEW", None):
                return response

            # 默认实例鉴权只有集群详情动作
            actions = [getattr(ActionEnum, f"{db_type}_VIEW")]
            resource_meta = getattr(ResourceEnum, db_type)
            return Permission.insert_permission_field(
                response, actions, resource_meta, id_field, data_field, always_allowed, many
            )

        return wrapped_view

    return wrapper


class ResourceViewSet(SystemViewSet):
    """资源查询基类"""

    # 查询字段
    lookup_field = "cluster_id"
    # 视图组件类型
    db_type = None

    # 视图接口查询类，封装了对集群列表/详情 实例列表/详情 和拓扑图的处理函数
    query_class = ListRetrieveResource
    # 集群列表serializer，主要是过滤参数
    query_serializer_class = None
    # 实例列表serializer
    list_instances_slz = serializers.ListInstancesSerializer
    # 实例详情serializer
    retrieve_instances_slz = serializers.RetrieveInstancesSerializer
    # 分页
    pagination_class = ResourceLimitOffsetPagination

    # 给集群列表数据嵌入权限字段
    list_perm_actions = []
    # 给实例列表数据嵌入权限字段
    list_instance_perm_actions = []
    # (可选)给集群列表数据嵌入全局权限字段
    # 如果此变量不为空，需要实现_external_perm_param_field方法
    list_external_perm_actions = []

    @staticmethod
    def _external_perm_param_field(kwargs):
        """
        全局权限字段资源的获取函数，默认不实现
        kwargs包含了request.data, request.query_params和view_class
        """
        raise NotImplementedError

    def _get_custom_permissions(self):
        if self.detail or self.action in ["retrieve_instance"]:
            return [ClusterDetailPermission()]
        return [DBManagePermission()]

    def retrieve(self, request, bk_biz_id: int, cluster_id: int):
        """查询集群详情"""
        return Response(self.query_class.retrieve_cluster(bk_biz_id, cluster_id))

    @Permission.decorator_permission_field(
        id_field=lambda d: d["id"],
        data_field=lambda d: d["results"],
        action_filed=lambda d: d["view_class"].list_perm_actions,
    )
    @Permission.decorator_external_permission_field(
        param_field=lambda d: d["view_class"]._external_perm_param_field(d),
        action_filed=lambda d: d["view_class"].list_external_perm_actions,
    )
    def list(self, request, bk_biz_id: int):
        """查询集群列表"""
        query_params = self.params_validate(self.query_serializer_class)
        data = self.paginator.paginate_list(request, bk_biz_id, self.query_class.list_clusters, query_params)
        return self.get_paginated_response(data)

    @action(methods=["GET"], detail=False, url_path="list_instances")
    @Permission.decorator_permission_field(
        id_field=lambda d: d["cluster_id"],
        data_field=lambda d: d["results"],
        action_filed=lambda d: d["view_class"].list_instance_perm_actions,
    )
    def list_instances(self, request, bk_biz_id: int):
        """查询实例列表"""
        query_params = self.params_validate(self.list_instances_slz)
        data = self.paginator.paginate_list(request, bk_biz_id, self.query_class.list_instances, query_params)
        return self.get_paginated_response(data)

    @action(methods=["GET"], detail=False, url_path="retrieve_instance")
    def retrieve_instance(self, request, bk_biz_id: int):
        """查询实例详情"""
        query_params = self.params_validate(self.retrieve_instances_slz)
        return Response(
            self.query_class.retrieve_instance(
                bk_biz_id, query_params.get("cluster_id"), query_params["ip"], query_params["port"]
            )
        )

    @action(methods=["GET"], detail=False, url_path="get_table_fields")
    def get_table_fields(self, request, bk_biz_id):
        """获取 table 信息"""
        return Response(self.query_class.get_fields())

    @action(methods=["GET"], detail=True, url_path="get_topo_graph")
    def get_topo_graph(self, request, bk_biz_id: int, cluster_id: int):
        """获取拓扑图"""
        return Response(self.query_class.get_topo_graph(bk_biz_id, cluster_id))

    @action(methods=["POST", "GET"], detail=False, url_path="export_cluster")
    def export_cluster(self, request, bk_biz_id: int):
        """导出集群数据为 excel 文件"""
        cluster_ids = request.data.get("cluster_ids")
        return self.query_class.export_cluster(bk_biz_id, cluster_ids)

    @action(methods=["POST", "GET"], detail=False, url_path="export_instance")
    def export_instance(self, request, bk_biz_id: int):
        """导出实例数据为 excel 文件"""
        bk_host_ids = request.data.get("bk_host_ids")
        return self.query_class.export_instance(bk_biz_id, bk_host_ids)

    def _paginate_resource_list(self, request, bk_biz_id: int):
        return self.paginator.paginate_resource_list(request, bk_biz_id, self)
