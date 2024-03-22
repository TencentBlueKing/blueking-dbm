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
import os
from typing import Dict, Tuple

from django.core.files.uploadedfile import InMemoryUploadedFile
from django.db.transaction import atomic
from django.utils.translation import ugettext as _
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response

from backend.bk_web import viewsets
from backend.bk_web.swagger import common_swagger_auto_schema
from backend.core.storages.storage import get_storage
from backend.db_package.constants import DB_PACKAGE_TAG, INSTALL_PACKAGE_LIST, PARSE_FILE_EXT, PackageType
from backend.db_package.exceptions import PackageNotExistException
from backend.db_package.filters import PackageListFilter
from backend.db_package.models import Package
from backend.db_package.serializers import (
    ListPackageVersionSerializer,
    PackageSerializer,
    SyncMediumSerializer,
    UploadPackageSerializer,
)
from backend.flow.consts import MediumEnum
from backend.iam_app.handlers.drf_perm import GlobalManageIAMPermission
from backend.utils.files import md5sum

logger = logging.getLogger("root")


class DBPackageViewSet(viewsets.AuditedModelViewSet):
    queryset = Package.objects.all()
    filter_class = PackageListFilter
    serializer_class = PackageSerializer

    def _get_custom_permissions(self):
        if self.action in ["list_install_pkg_types", "list_install_packages"]:
            return []
        return [GlobalManageIAMPermission()]

    @common_swagger_auto_schema(
        operation_summary=_("新建版本文件"),
        tags=[DB_PACKAGE_TAG],
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @common_swagger_auto_schema(
        operation_summary=_("同步制品库的文件信息(适用于medium初始化)"),
        tags=[DB_PACKAGE_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=SyncMediumSerializer)
    def sync_medium(self, request, *args, **kwargs):
        data = self.params_validate(self.get_serializer_class())
        db_type, sync_medium_infos = data["db_type"], data["sync_medium_infos"]
        # 获取原来介质的优先级信息
        old_packages = Package.objects.filter(db_type=db_type)
        old_package_persist: Dict[str, Tuple[int, bool]] = {
            f"{package.pkg_type}-{package.name}-{package.version}": (package.priority, package.enable)
            for package in old_packages
        }
        # 更新新介质的优先级和启用信息，如果没有在原来介质中存在，则默认为0和启用
        for info in sync_medium_infos:
            if info.get("pkg_type") not in PackageType.get_values():
                logger.warning(
                    f"pkg type({info.get('pkg_type')}) not in PackageType Enum, ignore",
                )
                continue
            persistent_info = old_package_persist.get(
                f"{info['pkg_type']}-{info['name']}-{info['version']}", (0, True)
            )
            info["priority"], info["enable"] = persistent_info[0], persistent_info[1]
        # 按照DBType进行原子更新：先删除存量介质信息，然后在更新介质信息
        with atomic():
            old_packages.delete()
            Package.objects.bulk_create([Package(**info) for info in sync_medium_infos])

        return Response()

    @common_swagger_auto_schema(
        operation_summary=_("查询版本文件列表"),
        tags=[DB_PACKAGE_TAG],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

    @common_swagger_auto_schema(
        operation_summary=_("查询组件安装包类型"),
        tags=[DB_PACKAGE_TAG],
    )
    @action(methods=["GET"], detail=False)
    def list_install_pkg_types(self, request, *args, **kwargs):
        return Response(INSTALL_PACKAGE_LIST)

    @common_swagger_auto_schema(
        operation_summary=_("查询组件安装包列表"),
        query_serializer=ListPackageVersionSerializer(),
        tags=[DB_PACKAGE_TAG],
    )
    @action(methods=["GET"], detail=False, serializer_class=ListPackageVersionSerializer, filter_class=None)
    def list_install_packages(self, request, *args, **kwargs):
        db_type, pkg_type = self.validated_data["db_type"], self.validated_data["query_key"]

        if pkg_type not in INSTALL_PACKAGE_LIST[db_type]:
            raise PackageNotExistException(_("请保证过滤类型是[{}]安装包类型").format(db_type))

        package_versions = (
            Package.objects.filter(db_type=db_type, pkg_type=pkg_type, enable=True)
            .order_by("-priority", "-update_at")
            .values_list("version", flat=True)
        )
        # 对有序列表package_versions进行去重
        package_versions = list(dict.fromkeys(list(package_versions)))
        return Response(package_versions)

    @common_swagger_auto_schema(
        operation_summary=_("更新版本文件属性"),
        tags=[DB_PACKAGE_TAG],
    )
    def partial_update(self, request, *args, **kwargs):
        # 如果有进行默认版本的变更，则需要把当前类型下的默认版本清零
        if "priority" in self.request.data:
            instance = self.get_object()
            Package.objects.filter(db_type=instance.db_type, pkg_type=instance.pkg_type, priority__gt=0).update(
                priority=0
            )

        super().partial_update(request, *args, **kwargs)
        return Response()

    @common_swagger_auto_schema(
        operation_summary=_("删除版本文件"),
        tags=[DB_PACKAGE_TAG],
    )
    def destroy(self, request, *args, **kwargs):
        super().destroy(request, *args, **kwargs)
        return Response()

    @common_swagger_auto_schema(
        operation_summary=_("上传文件"),
        tags=[DB_PACKAGE_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=UploadPackageSerializer, parser_classes=[MultiPartParser])
    def upload(self, request, *args, **kwargs):
        slz = self.get_serializer_class()(data=request.data)
        slz.is_valid(raise_exception=True)
        file: InMemoryUploadedFile = slz.validated_data["file"]

        version = slz.validated_data.get("version")
        file_name = file.name
        if not version:
            # 解析文件后缀：.gz/.tar.gz/.zip
            file_ext = PARSE_FILE_EXT.match(file_name).group("ext")
            filename_versions = file_name.replace(f".{file_ext}", "").split("-", maxsplit=1)
            version = filename_versions[1] if len(filename_versions) == 2 else MediumEnum.Latest

        with file.open("rb") as upload_file:
            # 计算上传文件的md5
            md5 = md5sum(file_obj=upload_file, closed=False)
            storage = get_storage()
            path = storage.save(
                name=os.path.join(
                    slz.validated_data["db_type"],
                    slz.validated_data["pkg_type"],
                    version,
                    file_name,
                ),
                content=upload_file,
            )
        return Response({"name": file_name, "size": file.size, "md5": md5, "path": path, "version": version})
