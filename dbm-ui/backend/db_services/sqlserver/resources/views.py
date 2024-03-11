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
from rest_framework.response import Response

from backend.bk_web.swagger import common_swagger_auto_schema
from backend.bk_web.viewsets import SystemViewSet
from backend.db_meta.models.cluster import Cluster
from backend.db_meta.models.db_module import DBModule
from backend.db_services.dbbase.resources.constants import ResourceNodeType
from backend.db_services.dbbase.resources.serializers import SearchResourceTreeSLZ
from backend.db_services.dbbase.resources.views import BaseListResourceViewSet
from backend.db_services.dbbase.resources.yasg_slz import ResourceTreeSLZ
from backend.db_services.sqlserver.resources import constants
from backend.iam_app.handlers.drf_perm.base import DBManagePermission


@method_decorator(
    name="list",
    decorator=common_swagger_auto_schema(tags=[constants.RESOURCE_TAG]),
)
class ListResourceViewSet(BaseListResourceViewSet):
    pass


class ResourceTreeViewSet(SystemViewSet):
    pagination_class = None

    def _get_custom_permissions(self):
        return [DBManagePermission()]

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
