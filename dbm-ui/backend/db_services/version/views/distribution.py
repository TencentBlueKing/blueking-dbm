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

from django.db.models import Count
from django.db.transaction import atomic
from django.utils.translation import gettext_lazy as _
from rest_framework.response import Response

from backend.bk_web import viewsets
from backend.bk_web.swagger import common_swagger_auto_schema
from backend.db_meta.models import DBVersion, Distribution
from backend.db_services.version.exceptions import VersionBaseException
from backend.db_services.version.serializers import DistributionSerializer
from backend.iam_app.dataclass import ActionEnum, ResourceEnum
from backend.iam_app.handlers.drf_perm.base import ResourceActionPermission, get_request_key_id
from backend.iam_app.handlers.permission import Permission

logger = logging.getLogger("root")
SWAGGER_TAG = _("发行版")


def instance_getter(request, view):
    if view.action == "destroy":
        return [Distribution.objects.get(id=view.kwargs["pk"]).db_type]
    else:
        return [get_request_key_id(request, "db_type")]


class DistributionViewSet(viewsets.AuditedModelViewSet):
    queryset = Distribution.objects.all()
    serializer_class = DistributionSerializer
    filter_fields = ["db_type", "pkg_type"]
    pagination_class = None

    default_permission_class = [
        ResourceActionPermission([ActionEnum.PACKAGE_MANAGE], ResourceEnum.DBTYPE, instance_getter)
    ]

    def get_queryset(self):
        # 重写 queryset，使用 annotate 添加版本系列计数和介质版本计数，避免 N+1 查询
        # 按创建时间倒序排列，新增的发行版排在上面
        return Distribution.objects.annotate(
            version_series_count=Count("versionseries", distinct=True),
            dbversion_count=Count("versionseries__dbversion", distinct=True),
        ).order_by("-create_at")

    @common_swagger_auto_schema(
        operation_summary=_("发行版列表"),
        tags=[SWAGGER_TAG],
    )
    @Permission.decorator_external_permission_field(
        param_field=lambda d: d["db_type"],
        actions=[ActionEnum.PACKAGE_VIEW, ActionEnum.PACKAGE_MANAGE],
        resource_meta=ResourceEnum.DBTYPE,
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @common_swagger_auto_schema(
        operation_summary=_("新建发行版"),
        tags=[SWAGGER_TAG],
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @common_swagger_auto_schema(
        operation_summary=_("发行版删除"),
        request_body=DistributionSerializer(),
        tags=[SWAGGER_TAG],
    )
    def destroy(self, request, *args, **kwargs):
        distribution = Distribution.objects.get(id=kwargs["pk"])

        # 检查是否存在介质版本
        dbversion_count = DBVersion.objects.filter(version_series__distribution=distribution).count()
        if dbversion_count > 0:
            raise VersionBaseException(_("发行版下存在介质版本，不允许删除"))

        # 如果不存在介质版本，则级联删除关联的版本系列
        with atomic():
            # 删除所有关联的版本系列
            distribution.versionseries_set.all().delete()
            # 删除发行版
            distribution.delete()

        return Response()

    @common_swagger_auto_schema(
        operation_summary=_("发行版更新"),
        tags=[SWAGGER_TAG],
    )
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)
