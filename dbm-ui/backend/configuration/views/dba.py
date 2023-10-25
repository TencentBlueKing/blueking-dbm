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
from backend.iam_app.dataclass import ResourceEnum
from backend.iam_app.dataclass.actions import ActionEnum
from backend.iam_app.handlers.drf_perm.base import ResourceActionPermission

SWAGGER_TAG = _("DBA人员")


class DBAdminViewSet(viewsets.SystemViewSet):
    def _get_custom_permissions(self):
        if self.action == "list_admins":
            return []

        if not int(self.request.data.get("bk_biz_id", 0)):
            return [ResourceActionPermission([ActionEnum.GLOBAL_DBA_ADMINISTRATOR_EDIT])]
        else:
            instance_getter = lambda request, view: [request.data["bk_biz_id"]]  # noqa: E731
            return [
                ResourceActionPermission([ActionEnum.DBA_ADMINISTRATOR_EDIT], ResourceEnum.BUSINESS, instance_getter)
            ]

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
