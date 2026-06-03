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
import logging

from django.utils.translation import gettext_lazy as _
from rest_framework.exceptions import ValidationError

from backend.bk_web import viewsets
from backend.bk_web.swagger import common_swagger_auto_schema
from backend.db_meta.models import Distribution, VersionSeries
from backend.db_services.version.exceptions import VersionBaseException
from backend.db_services.version.serializers import VersionSeriesDeleteSerializer, VersionSeriesSerializer
from backend.iam_app.dataclass import ActionEnum, ResourceEnum
from backend.iam_app.handlers.drf_perm.base import ResourceActionPermission, get_request_key_id

logger = logging.getLogger("root")
SWAGGER_TAG = _("版本系列")


def instance_getter(request, view):
    distribution = Distribution.objects.filter(id=get_request_key_id(request, "distribution")).first()
    if not distribution:
        return []
    return [distribution.db_type]


class VersionSeriesViewSet(viewsets.AuditedModelViewSet):
    queryset = VersionSeries.objects.all().order_by("-create_at")
    serializer_class = VersionSeriesSerializer
    pagination_class = None
    filterset_fields = ["distribution"]

    action_permission_map = {("list",): []}
    default_permission_class = [
        ResourceActionPermission([ActionEnum.PACKAGE_MANAGE], ResourceEnum.DBTYPE, instance_getter)
    ]

    def filter_queryset(self, queryset):
        """重写过滤方法，当 distribution 不存在时返回空查询集而不是报错"""
        try:
            return super().filter_queryset(queryset)
        except ValidationError:
            return queryset.none()

    @common_swagger_auto_schema(
        operation_summary=_("版本系列列表"),
        tags=[SWAGGER_TAG],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @common_swagger_auto_schema(
        operation_summary=_("新建版本系列"),
        tags=[SWAGGER_TAG],
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @common_swagger_auto_schema(
        operation_summary=_("版本系列删除"),
        request_body=VersionSeriesDeleteSerializer(),
        tags=[SWAGGER_TAG],
    )
    def destroy(self, request, *args, **kwargs):
        # 验证查询参数（distribution 从 URL 查询参数中获取）
        validated_data = self.params_validate(VersionSeriesDeleteSerializer, init_params=request.data)
        distribution_id = validated_data.get("distribution")
        series = VersionSeries.objects.get(id=kwargs["pk"])
        # 验证 distribution 是否匹配
        if series.distribution_id != distribution_id:
            raise VersionBaseException(_("distribution 参数与版本系列的 distribution 不匹配"))
        # 关联了版本则不允许删除
        if series.dbversion_set.exists():
            raise VersionBaseException(_("版本系列关联了版本，不允许删除"))
        return super().destroy(request, *args, **kwargs)

    @common_swagger_auto_schema(
        operation_summary=_("版本系列更新"),
        tags=[SWAGGER_TAG],
    )
    def update(self, request, *args, **kwargs):
        return super().update(request, *args, **kwargs)
