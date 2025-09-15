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
from backend.db_meta.models import RedisHotKeyDetail
from backend.db_proxy.constants import SWAGGER_TAG
from backend.db_proxy.views.redis_hot_key_analysis.serializers import (
    CreateHotKeyDetailSerializer,
    RedisHotKeyDetailSerializer,
)
from backend.db_proxy.views.views import BaseProxyPassViewSet


class HotKeyAnalysisViewSet(BaseProxyPassViewSet):
    """
    HotKeyAnalysis API 代理
    """

    @common_swagger_auto_schema(
        operation_summary=_("创建热key分析报告"),
        request_body=RedisHotKeyDetailSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(
        methods=["POST"],
        detail=False,
        serializer_class=CreateHotKeyDetailSerializer,
    )
    def create_analysis_report(self, request):
        hot_key_infos = request.data.get("hot_key_infos", [])
        serializer = self.get_serializer(data=hot_key_infos, many=True)
        serializer.is_valid(raise_exception=True)
        analyses = [RedisHotKeyDetail(**validated_data) for validated_data in serializer.validated_data]
        RedisHotKeyDetail.objects.bulk_create(analyses)
        return Response({})
