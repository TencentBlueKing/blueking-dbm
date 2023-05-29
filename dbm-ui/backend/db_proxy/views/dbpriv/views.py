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

from backend.bk_web.swagger import common_swagger_auto_schema
from backend.components import DBPrivManagerApi
from backend.db_proxy.constants import SWAGGER_TAG

from ..views import BaseProxyPassViewSet
from .serializers import ProxyPasswordSerializer


class DBPrivProxyPassViewSet(BaseProxyPassViewSet):
    """
    DB权限服务透传接口
    """

    @common_swagger_auto_schema(
        operation_summary=_("[dbpriv]获取proxy密码"),
        request_body=ProxyPasswordSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=ProxyPasswordSerializer, url_path="dbpriv/proxy_password")
    def query_proxy_password(self, request):
        validated_data = self.params_validate(self.get_serializer_class())
        return Response(DBPrivManagerApi.get_password(validated_data))
