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
from django.utils.translation import ugettext as _
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from backend.bk_web import viewsets
from backend.bk_web.swagger import common_swagger_auto_schema
from backend.db_services.mysql.remote_service.handlers import RemoteServiceHandler
from backend.db_services.mysql.remote_service.serializers import (
    CheckClusterDatabaseResponseSerializer,
    CheckClusterDatabaseSerializer,
    CheckFlashbackInfoResponseSerializer,
    CheckFlashbackInfoSerializer,
    ShowDatabasesRequestSerializer,
    ShowDatabasesResponseSerializer,
)
from backend.iam_app.handlers.drf_perm import DBManageIAMPermission

SWAGGER_TAG = "db_services/remote_service"


class RemoteServiceViewSet(viewsets.SystemViewSet):
    def _get_custom_permissions(self):
        return [DBManageIAMPermission()]

    def _get_cluster_id_and_role(self, validated_data):
        cluster_id__role_map = {}
        cluster_ids = validated_data.get("cluster_ids")

        if validated_data.get("cluster_infos"):
            cluster_ids = [info["cluster_id"] for info in validated_data["cluster_infos"]]
            cluster_id__role_map = {info["cluster_id"]: info["role"] for info in validated_data["cluster_infos"]}

        return cluster_ids, cluster_id__role_map

    @common_swagger_auto_schema(
        operation_summary=_("查询集群数据库列表"),
        request_body=ShowDatabasesRequestSerializer(),
        tags=[SWAGGER_TAG],
        responses={status.HTTP_200_OK: ShowDatabasesResponseSerializer()},
    )
    @action(methods=["POST"], detail=False, serializer_class=ShowDatabasesRequestSerializer)
    def show_cluster_databases(self, request, bk_biz_id):
        validated_data = self.params_validate(self.get_serializer_class())
        cluster_ids, cluster_id__role_map = self._get_cluster_id_and_role(validated_data)
        return Response(
            RemoteServiceHandler(bk_biz_id=bk_biz_id).show_databases(
                cluster_ids=cluster_ids, cluster_id__role_map=cluster_id__role_map
            ),
        )

    @common_swagger_auto_schema(
        operation_summary=_("校验DB是否在集群内"),
        request_body=CheckClusterDatabaseSerializer(),
        tags=[SWAGGER_TAG],
        responses={status.HTTP_200_OK: CheckClusterDatabaseResponseSerializer()},
    )
    @action(methods=["POST"], detail=False, serializer_class=CheckClusterDatabaseSerializer)
    def check_cluster_database(self, request, bk_biz_id):
        validated_data = self.params_validate(self.get_serializer_class())
        return Response(
            RemoteServiceHandler(bk_biz_id=bk_biz_id).check_cluster_database(check_infos=validated_data["infos"])
        )

    @common_swagger_auto_schema(
        operation_summary=_("校验flashback信息是否合法"),
        request_body=CheckFlashbackInfoSerializer(),
        responses={status.HTTP_200_OK: CheckFlashbackInfoResponseSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=CheckFlashbackInfoSerializer)
    def check_flashback_database(self, request, bk_biz_id):
        validated_data = self.params_validate(self.get_serializer_class())
        return Response(RemoteServiceHandler(bk_biz_id=bk_biz_id).check_flashback_database(validated_data["infos"]))
