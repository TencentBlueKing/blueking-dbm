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
import os
import re

from django.core.files.uploadedfile import InMemoryUploadedFile
from django.utils.translation import ugettext as _
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response

from backend.bk_web import viewsets
from backend.bk_web.swagger import common_swagger_auto_schema
from backend.core.storages.storage import get_storage
from backend.db_package.filters import PackageListFilter
from backend.db_package.models import Package
from backend.db_package.serializers import PackageSerializer, UpdateOrCreateSerializer, UploadPackageSerializer
from backend.flow.consts import MediumEnum
from backend.iam_app.handlers.drf_perm import GlobalManageIAMPermission
from backend.utils.files import md5sum

DB_PACKAGE_TAG = "db_package"
PARSE_FILE_EXT = re.compile(r"^.*?[.](?P<ext>tar\.gz|tar\.bz2|\w+)$")


class DBPackageViewSet(viewsets.AuditedModelViewSet):
    queryset = Package.objects.all()
    filter_class = PackageListFilter
    serializer_class = PackageSerializer

    def _get_custom_permissions(self):
        return [GlobalManageIAMPermission()]

    @common_swagger_auto_schema(
        operation_summary=_("新建版本文件"),
        tags=[DB_PACKAGE_TAG],
    )
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @common_swagger_auto_schema(
        operation_summary=_("新建或者更新版本文件(适用于medium初始化)"),
        tags=[DB_PACKAGE_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=UpdateOrCreateSerializer)
    def update_or_create(self, request, *args, **kwargs):
        data = self.params_validate(self.get_serializer_class())
        Package.objects.update_or_create(md5=data["md5"], db_type=data["db_type"], defaults=data)
        return Response()

    @common_swagger_auto_schema(
        operation_summary=_("查询版本文件列表"),
        tags=[DB_PACKAGE_TAG],
    )
    def list(self, request, *args, **kwargs):
        return super().list(request, *args, **kwargs)

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
