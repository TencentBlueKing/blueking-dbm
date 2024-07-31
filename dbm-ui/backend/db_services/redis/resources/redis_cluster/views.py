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
from rest_framework.decorators import action
from rest_framework.response import Response

from backend.bk_web.swagger import common_swagger_auto_schema
from backend.configuration.constants import DBType
from backend.db_meta.models import Cluster
from backend.db_services.dbbase.resources import serializers, viewsets
from backend.db_services.redis.resources import constants
from backend.flow.utils.base.payload_handler import PayloadHandler
from backend.iam_app.dataclass import ResourceEnum
from backend.iam_app.dataclass.actions import ActionEnum

from . import yasg_slz
from .query import RedisListRetrieveResource


@method_decorator(
    name="list",
    decorator=common_swagger_auto_schema(
        operation_summary=_("获取集群列表"),
        query_serializer=serializers.ListResourceSLZ(),
        responses={status.HTTP_200_OK: yasg_slz.PaginatedResourceSLZ()},
        tags=[constants.RESOURCE_TAG],
    ),
)
@method_decorator(
    name="retrieve",
    decorator=common_swagger_auto_schema(
        operation_summary=_("获取集群详情"),
        responses={status.HTTP_200_OK: yasg_slz.ResourceSLZ()},
        tags=[constants.RESOURCE_TAG],
    ),
)
@method_decorator(
    name="list_instances",
    decorator=common_swagger_auto_schema(
        query_serializer=serializers.ListInstancesSerializer(),
        responses={status.HTTP_200_OK: yasg_slz.PaginatedResourceSLZ()},
        tags=[constants.RESOURCE_TAG],
    ),
)
@method_decorator(
    name="retrieve_instance",
    decorator=common_swagger_auto_schema(
        query_serializer=serializers.RetrieveInstancesSerializer(),
        tags=[constants.RESOURCE_TAG],
    ),
)
@method_decorator(
    name="get_table_fields",
    decorator=common_swagger_auto_schema(
        responses={status.HTTP_200_OK: yasg_slz.ResourceFieldSLZ()},
        tags=[constants.RESOURCE_TAG],
    ),
)
@method_decorator(
    name="get_topo_graph",
    decorator=common_swagger_auto_schema(
        operation_summary=_("获取集群拓扑"),
        responses={status.HTTP_200_OK: yasg_slz.ResourceTopoGraphSLZ()},
        tags=[constants.RESOURCE_TAG],
    ),
)
@method_decorator(
    name="list_machines",
    decorator=common_swagger_auto_schema(
        query_serializer=serializers.ListRedisMachineResourceSLZ(),
        responses={status.HTTP_200_OK: yasg_slz.PaginatedMachineResourceSLZ()},
        tags=[constants.RESOURCE_TAG],
    ),
)
@method_decorator(
    name="get_nodes",
    decorator=common_swagger_auto_schema(
        operation_summary=_("获取集群节点"),
        query_serializer=serializers.ListNodesSLZ(),
        tags=[constants.RESOURCE_TAG],
    ),
)
class RedisClusterViewSet(viewsets.ResourceViewSet):
    query_class = RedisListRetrieveResource
    query_serializer_class = serializers.ListRedisResourceSLZ
    list_machine_slz = serializers.ListRedisMachineResourceSLZ
    db_type = DBType.Redis

    list_perm_actions = [
        ActionEnum.REDIS_KEYS_DELETE,
        ActionEnum.REDIS_KEYS_EXTRACT,
        ActionEnum.REDIS_PLUGIN_CREATE_CLB,
        ActionEnum.REDIS_PLUGIN_DNS_BIND_CLB,
        ActionEnum.REDIS_PLUGIN_CREATE_POLARIS,
        ActionEnum.REDIS_DESTROY,
        ActionEnum.REDIS_OPEN_CLOSE,
        ActionEnum.REDIS_PURGE,
        ActionEnum.REDIS_VIEW,
        ActionEnum.REDIS_BACKUP,
        ActionEnum.REDIS_ACCESS_ENTRY_VIEW,
    ]
    list_instance_perm_actions = [ActionEnum.REDIS_VIEW]
    list_external_perm_actions = [ActionEnum.ACCESS_ENTRY_EDIT]

    @staticmethod
    def _external_perm_param_field(kwargs):
        return {
            ResourceEnum.BUSINESS.id: kwargs["bk_biz_id"],
            ResourceEnum.DBTYPE.id: kwargs["view_class"].db_type.value,
        }

    @action(methods=["GET"], detail=True, url_path="get_nodes", serializer_class=serializers.ListNodesSLZ)
    def get_nodes(self, request, bk_biz_id: int, cluster_id: int):
        """获取特定角色的节点"""
        params = self.params_validate(self.get_serializer_class())
        return Response(self.query_class.get_nodes(bk_biz_id, cluster_id, params["role"], params.get("keyword")))

    @common_swagger_auto_schema(
        operation_summary=_("获取集群访问密码"),
        responses={status.HTTP_200_OK: yasg_slz.PasswordResourceSLZ},
        tags=[constants.RESOURCE_TAG],
    )
    @action(methods=["GET"], detail=True, url_path="get_password", serializer_class=None)
    def get_password(self, request, bk_biz_id: int, cluster_id: int):
        """获取集群密码（proxy）"""
        cluster = Cluster.objects.get(id=cluster_id, bk_biz_id=bk_biz_id)
        redis_password_map = PayloadHandler.redis_get_cluster_password(cluster=cluster)
        return Response(
            {
                "cluster_name": cluster.name,
                "domain": f"{cluster.immute_domain}:{cluster.access_port}",
                "password": redis_password_map["redis_proxy_password"],
            }
        )
