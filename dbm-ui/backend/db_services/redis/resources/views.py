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
from rest_framework import status
from rest_framework.response import Response

from backend.bk_web.swagger import common_swagger_auto_schema
from backend.bk_web.viewsets import SystemViewSet
from backend.db_meta.models.cluster import Cluster
from backend.iam_app.handlers.drf_perm.base import DBManagePermission

from ...dbbase.resources.constants import ResourceNodeType
from ...dbbase.resources.serializers import SearchResourceTreeSLZ
from ...dbbase.resources.views import BaseListResourceViewSet
from ...dbbase.resources.yasg_slz import ResourceTreeSLZ
from . import constants


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
                        "proxy_version": cluster.proxy_version,
                    },
                }
                for cluster in clusters
            ]
        )
