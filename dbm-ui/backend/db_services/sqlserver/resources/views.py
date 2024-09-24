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
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from backend.bk_web.swagger import common_swagger_auto_schema
from backend.bk_web.viewsets import SystemViewSet
from backend.configuration.constants import DBType
from backend.db_meta.models.cluster import Cluster
from backend.db_meta.models.db_module import DBModule
from backend.db_meta.models.storage_set_dtl import SqlserverClusterSyncMode
from backend.db_services.dbbase.resources import viewsets
from backend.db_services.dbbase.resources.constants import ResourceNodeType
from backend.db_services.dbbase.resources.serializers import SearchResourceTreeSLZ, SqlserverListInstanceSerializer
from backend.db_services.dbbase.resources.views import BaseListResourceViewSet
from backend.db_services.dbbase.resources.yasg_slz import ResourceTreeSLZ
from backend.db_services.sqlserver.resources import constants
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


class ResourceTreeViewSet(SystemViewSet):
    pagination_class = None

    default_permission_class = [DBManagePermission()]

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


class BaseSQLServerViewSet(viewsets.ResourceViewSet):

    db_type = DBType.Sqlserver

    list_perm_actions = [ActionEnum.SQLSERVER_VIEW]
    list_instance_perm_actions = [ActionEnum.SQLSERVER_VIEW]
    list_external_perm_actions = [ActionEnum.ACCESS_ENTRY_EDIT]

    @staticmethod
    def _external_perm_param_field(kwargs):
        return {
            ResourceEnum.BUSINESS.id: kwargs["bk_biz_id"],
            ResourceEnum.DBTYPE.id: kwargs["view_class"].db_type.value,
        }

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

        # 处理筛选sqlserver db模块主从方式符合的集群
        if "sys_mode" in query_params:
            alwayson_ids = list(
                SqlserverClusterSyncMode.objects.filter(sync_mode=query_params["sys_mode"]).values_list(
                    "cluster_id", flat=True
                )
            )
            # 如果不存在alwayson_ids 直接返回空列表
            if not alwayson_ids:
                return self.get_paginated_response([])
            query_params["cluster_ids"] = alwayson_ids

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
        query_params = self.params_validate(SqlserverListInstanceSerializer)

        # 过滤模块实例
        if "db_module_id" in query_params:
            module_ids = query_params["db_module_id"].split(",")
            cluster_name_list = list(
                Cluster.objects.filter(storageinstance__db_module_id__in=module_ids).values_list("name", flat=True)
            )
            # 如果不存在cluster_name_list 直接返回空列表
            if not cluster_name_list:
                return self.get_paginated_response([])
            query_params["name"] = ",".join(cluster_name_list)

        data = self.paginator.paginate_list(request, bk_biz_id, self.query_class.list_instances, query_params)
        return self.get_paginated_response(data)
