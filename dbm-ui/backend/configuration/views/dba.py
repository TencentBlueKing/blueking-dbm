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
from django.utils.translation import ugettext_lazy as _
from rest_framework.decorators import action
from rest_framework.response import Response

from backend.bk_web import viewsets
from backend.bk_web.swagger import common_swagger_auto_schema
from backend.configuration.models.dba import DBAdministrator
from backend.configuration.serializers import ListDBAdminSerializer, UpsertDBAdminSerializer
from backend.iam_app.handlers.drf_perm import DBManageIAMPermission, GlobalManageIAMPermission

SWAGGER_TAG = _("DBA人员")


class DBAdminViewSet(viewsets.SystemViewSet):
    def _get_custom_permissions(self):
        if self.action == self.list_admins.__name__:
            return []

        bk_biz_id = self.request.query_params.get("bk_biz_id", 0) or self.request.data.get("bk_biz_id", 0)
        if int(bk_biz_id):
            return [DBManageIAMPermission()]

        return [GlobalManageIAMPermission()]

    @common_swagger_auto_schema(
        operation_summary=_("查询DBA人员列表"), query_serializer=ListDBAdminSerializer, tags=[SWAGGER_TAG]
    )
    @action(methods=["GET"], detail=False, serializer_class=ListDBAdminSerializer)
    def list_admins(self, request, *args, **kwargs):
        validated_data = self.params_validate(self.get_serializer_class())
        bk_biz_id = validated_data["bk_biz_id"]
        return Response(DBAdministrator.list_biz_admins(bk_biz_id=bk_biz_id))

    @common_swagger_auto_schema(operation_summary=_("更新DBA人员"), tags=[SWAGGER_TAG])
    @action(methods=["POST"], detail=False, serializer_class=UpsertDBAdminSerializer)
    def upsert_admins(self, request, *args, **kwargs):
        validated_data = self.params_validate(self.get_serializer_class())
        bk_biz_id = validated_data["bk_biz_id"]
        db_admins = validated_data["db_admins"]
        return Response(DBAdministrator.upsert_biz_admins(bk_biz_id, db_admins))
