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
import base64

from django.utils.decorators import method_decorator
from django.utils.translation import ugettext as _
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from backend.bk_web.swagger import common_swagger_auto_schema
from backend.bk_web.viewsets import SystemViewSet
from backend.components import DBConfigApi, DBPrivManagerApi
from backend.components.dbconfig.constants import FormatType, LevelName
from backend.db_meta.enums import ClusterType
from backend.db_meta.models.cluster import Cluster
from backend.db_services.bigdata.resources import constants, yasg_slz
from backend.db_services.dbbase.resources.constants import ResourceNodeType
from backend.db_services.dbbase.resources.serializers import SearchResourceTreeSLZ
from backend.db_services.dbbase.resources.views import BaseListResourceViewSet
from backend.db_services.dbbase.resources.viewsets import ResourceViewSet
from backend.db_services.dbbase.resources.yasg_slz import ResourceTreeSLZ
from backend.flow.consts import ConfigTypeEnum, LevelInfoEnum, UserName
from backend.flow.utils.pulsar.consts import PulsarConfigEnum


@method_decorator(
    name="list",
    decorator=common_swagger_auto_schema(tags=[constants.RESOURCE_TAG]),
)
class ListResourceViewSet(BaseListResourceViewSet):
    pass


class BigdataResourceViewSet(ResourceViewSet):
    def _get_password(cls, cluster, username, port=0):
        """查询密码"""
        query_params = {
            "instances": [{"ip": cluster.immute_domain, "port": port, "bk_cloud_id": cluster.bk_cloud_id}],
            "users": [
                {"username": username, "component": cluster.cluster_type},
            ],
        }

        resp = DBPrivManagerApi.get_password(query_params)
        if resp.get("count") > 0:
            return base64.b64decode(resp["items"][0]["password"]).decode("utf-8")

        return ""

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

        username, password, token = "", "", ""

        # 查询真实账户
        if cluster.cluster_type == ClusterType.Hdfs.value:
            username = UserName.HDFS_DEFAULT
        else:
            username = self._get_password(cluster, f"{cluster.cluster_type}_user")

        # 根据真实账户获取密码
        if username:
            password = self._get_password(cluster, username)

        # only for pulsar cluster
        if cluster.cluster_type == ClusterType.Pulsar:
            token = self._get_password(cluster, PulsarConfigEnum.ClientAuthenticationParameters)

        if not (username and password):
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
            username, password = resp_content.get("username"), resp_content.get("password")

            # only for pulsar cluster
            if cluster.cluster_type == ClusterType.Pulsar:
                token = resp_content.get("broker.brokerClientAuthenticationParameters")

        return Response(
            {
                "cluster_name": cluster.name,
                "domain": cluster.immute_domain,
                "access_port": cluster.access_port,
                "password": password,
                "username": username,
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
