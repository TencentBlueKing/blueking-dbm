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
from rest_framework.decorators import action
from rest_framework.response import Response

from backend.bk_web import viewsets
from backend.bk_web.swagger import common_swagger_auto_schema
from backend.components import UserManagerApi

from .serializers import ListUsersSerializer

TICKET_TAG = "user"


class UserViewSet(viewsets.SystemViewSet):
    @common_swagger_auto_schema(
        operation_summary=_("人员列表"),
        query_serializer=ListUsersSerializer(),
        tags=[TICKET_TAG],
    )
    @action(methods=["GET"], detail=False, serializer_class=ListUsersSerializer)
    def list_users(self, request, *args, **kwargs):
        validated_data = self.params_validate(self.get_serializer_class())
        fuzzy_lookups = validated_data["fuzzy_lookups"]
        no_page = validated_data["no_page"]
        return Response(
            UserManagerApi.list_users(
                {"fields": "username,display_name", "fuzzy_lookups": fuzzy_lookups, "no_page": no_page}
            )
        )
