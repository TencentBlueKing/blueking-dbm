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
from rest_framework.decorators import action
from rest_framework.response import Response

from backend.bk_web import viewsets
from backend.bk_web.swagger import common_swagger_auto_schema
from backend.core.storages.handlers import StorageHandler
from backend.db_meta.models import DBVersion, ProxyInstance, StorageInstance, VersionSeries
from backend.db_package.models import Package
from backend.db_services.version.exceptions import VersionBaseException
from backend.db_services.version.serializers import (
    DBVersionConflictCheckResponseSerializer,
    DBVersionConflictCheckSerializer,
    DBVersionSerializer,
)
from backend.db_services.version.utils import pad_full_version
from backend.exceptions import ApiRequestError
from backend.iam_app.dataclass import ActionEnum, ResourceEnum
from backend.iam_app.handlers.drf_perm.base import ResourceActionPermission, get_request_key_id

logger = logging.getLogger("root")
SWAGGER_TAG = _("介质版本")


def instance_getter(request, view):
    if view.action in ["create", "check_name_conflict"]:
        version_series = VersionSeries.objects.filter(id=get_request_key_id(request, "version_series")).first()
        if version_series and version_series.distribution:
            return [version_series.distribution.db_type]
        return []

    if view.action in ["destroy", "update"]:
        dbversion = DBVersion.objects.filter(id=view.kwargs["pk"]).first()
        return [dbversion.version_series.distribution.db_type]

    return []


class DBVersionViewSet(viewsets.AuditedModelViewSet):
    """介质版本视图集"""

    queryset = DBVersion.objects.prefetch_related("package_set").all().order_by("-recommend", "-create_at")
    serializer_class = DBVersionSerializer
    pagination_class = None
    filter_fields = {
        "version_series": ["exact", "in"],
        "phase": ["exact", "in"],
    }

    default_permission_class = [
        ResourceActionPermission([ActionEnum.PACKAGE_MANAGE], ResourceEnum.DBTYPE, instance_getter)
    ]

    @common_swagger_auto_schema(
        operation_summary=_("介质版本列表"),
        tags=[SWAGGER_TAG],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @common_swagger_auto_schema(
        operation_summary=_("新建介质版本"),
        tags=[SWAGGER_TAG],
    )
    def create(self, request, *args, **kwargs):
        # 如果设置为推荐版本，则清除同一发行版下其他版本的推荐标记
        if request.data.get("recommend") is True:
            version_series_id = request.data.get("version_series")
            version_series = VersionSeries.objects.filter(id=version_series_id).first()
            if version_series and version_series.distribution:
                # 清除该发行版下所有现有版本的推荐标记
                DBVersion.objects.filter(version_series__distribution=version_series.distribution.id).update(
                    recommend=False
                )
        return super().create(request, *args, **kwargs)

    @common_swagger_auto_schema(
        operation_summary=_("介质版本删除"),
        tags=[SWAGGER_TAG],
    )
    def destroy(self, request, *args, **kwargs):
        db_version = DBVersion.objects.get(id=kwargs["pk"])
        package_ids = list(db_version.package_set.values_list("id", flat=True))
        # 如果介质关联了实例则不允许删除
        if StorageInstance.objects.filter(db_package__in=package_ids).exists():
            raise VersionBaseException(_("版本介质关联了实例，不允许删除"))
        if ProxyInstance.objects.filter(db_package__in=package_ids).exists():
            raise VersionBaseException(_("版本介质关联了实例，不允许删除"))
        # 删除制品库文件
        packages = Package.objects.filter(id__in=package_ids)
        for package in packages:
            try:
                StorageHandler().delete_file(package.path)
            except ApiRequestError as e:
                logger.error(_("文件删除异常，错误信息: {}").format(e))
        # 删除本地记录
        packages.delete()
        return super().destroy(request, *args, **kwargs)

    @common_swagger_auto_schema(
        operation_summary=_("介质版本更新"),
        tags=[SWAGGER_TAG],
    )
    def partial_update(self, request, *args, **kwargs):
        instance = self.get_object()

        # 设置启停的话联动下面的packages启停
        if request.data.get("enable") is not None:
            Package.objects.filter(db_version=instance).update(enable=request.data["enable"])
            # 停用版本时，自动取消推荐标识
            if request.data.get("enable") is False:
                request.data["recommend"] = False

        # 设置了推荐字段的话，其他版本的推荐字段需要设置为False
        if request.data.get("recommend") is not None:
            distribution = self.get_object().version_series.distribution.id
            DBVersion.objects.filter(version_series__distribution=distribution).update(recommend=False)
            # 联动修改v1的推荐字段
            Package.objects.filter(db_version__version_series__distribution=distribution).update(priority=0)
            Package.objects.filter(db_version=instance).update(priority=request.data["recommend"])

        return super().partial_update(request, *args, **kwargs)

    @common_swagger_auto_schema(
        operation_summary=_("校验介质版本名称/版本号在所属发行版下是否冲突"),
        query_serializer=DBVersionConflictCheckSerializer(),
        responses={200: DBVersionConflictCheckResponseSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(
        detail=False,
        methods=["GET"],
        serializer_class=DBVersionConflictCheckSerializer,
        pagination_class=None,
        filter_fields=None,
    )
    def check_name_conflict(self, request, *args, **kwargs):
        """
        校验在 version_series.distribution 维度下:
        - 介质版本名称(name) 是否已被占用
        - 介质完整版本号(full_version, 前端按 pkg_type 段数传) 是否已被占用
        编辑场景可传 exclude_id 排除自身
        """
        data = self.params_validate(self.get_serializer_class())

        version_series = VersionSeries.objects.filter(id=data["version_series"]).first()
        if not version_series or not version_series.distribution:
            raise VersionBaseException(_("版本系列不存在或未关联发行版"))

        distribution_id = version_series.distribution_id
        name = data.get("name") or ""
        full_version = data.get("full_version") or ""
        exclude_id = data.get("exclude_id")

        # 校验名称不能重复
        name_conflict = False
        if name:
            qs = DBVersion.objects.filter(distribution_id=distribution_id, name=name)
            qs = qs.exclude(id=exclude_id) if exclude_id else qs
            name_conflict = qs.exists()

        # 校验版本不能重复
        version_conflict = False
        if full_version:
            padded_full_version = pad_full_version(full_version)
            qs = DBVersion.objects.filter(distribution_id=distribution_id, full_version=padded_full_version)
            qs = qs.exclude(id=exclude_id) if exclude_id else qs
            version_conflict = qs.exists()

        return Response({"name_conflict": name_conflict, "version_conflict": version_conflict})
