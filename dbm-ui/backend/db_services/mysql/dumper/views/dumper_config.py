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
from backend.bk_web.pagination import AuditedLimitOffsetPagination
from backend.bk_web.swagger import common_swagger_auto_schema
from backend.db_services.mysql.dumper.filters import DumperConfigListFilter
from backend.db_services.mysql.dumper.models import DumperSubscribeConfig
from backend.db_services.mysql.dumper.serializers import DumperSubscribeConfigSerializer, VerifyDuplicateNamsSerializer

SWAGGER_TAG = "dumper"


class DumperConfigViewSet(viewsets.AuditedModelViewSet):
    pagination_class = AuditedLimitOffsetPagination
    queryset = DumperSubscribeConfig.objects.all()
    serializer_class = DumperSubscribeConfigSerializer
    filter_class = DumperConfigListFilter

    def get_queryset(self):
        return self.queryset.filter(bk_biz_id=self.kwargs["bk_biz_id"])

    @common_swagger_auto_schema(
        operation_summary=_("查询数据订阅配置列表"),
        tags=[SWAGGER_TAG],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @common_swagger_auto_schema(
        operation_summary=_("数据订阅配置详情"),
        tags=[SWAGGER_TAG],
    )
    def retrieve(self, request, *args, **kwargs):
        return super().retrieve(request, *args, **kwargs)

    @common_swagger_auto_schema(
        operation_summary=_("校验订阅配置是否重名"),
        query_serializer=VerifyDuplicateNamsSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=False, serializer_class=VerifyDuplicateNamsSerializer, filter_class=None)
    def verify_duplicate_name(self, request, *args, **kwargs):
        name = self.params_validate(self.get_serializer_class())["name"]
        is_duplicate = self.queryset.filter(bk_biz_id=kwargs["bk_biz_id"], name=name).count() != 0
        return Response(is_duplicate)
