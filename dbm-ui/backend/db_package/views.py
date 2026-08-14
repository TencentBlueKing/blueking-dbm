# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with  the License.
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
from django.utils import timezone
from django.utils.translation import gettext as _
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response

from backend.bk_web import viewsets
from backend.bk_web.swagger import common_swagger_auto_schema
from backend.configuration.constants import DEFAULT_PACKAGE_SUPPORT_SYSTEMS, SystemSettingsEnum
from backend.configuration.models import SystemSettings
from backend.core.storages.handlers import StorageHandler
from backend.core.storages.storage import get_storage
from backend.db_meta.models import DBVersion, Distribution, ProxyInstance, StorageInstance, VersionSeries
from backend.db_package.constants import DB_PACKAGE_TAG, INSTALL_PACKAGE_LIST, PARSE_FILE_EXT, PackageType
from backend.db_package.exceptions import DBPackageBaseException, PackageNotExistException
from backend.db_package.filters import PackageListFilter
from backend.db_package.models import Package
from backend.db_package.serializers import (
    BulkCreatePackageSerializer,
    BulkDeletePackageSerializer,
    ListPackageVersionSerializer,
    PackageSerializer,
    SyncMediumSerializer,
    UploadPackageSerializer,
)
from backend.flow.consts import MediumEnum
from backend.iam_app.dataclass import ResourceEnum
from backend.iam_app.dataclass.actions import ActionEnum
from backend.iam_app.handlers.drf_perm.base import ResourceActionPermission, get_request_key_id
from backend.iam_app.handlers.permission import Permission
from backend.utils.files import md5sum

logger = logging.getLogger("root")


class DBPackageViewSet(viewsets.AuditedModelViewSet):
    queryset = Package.objects.all().order_by("-update_at")
    filter_class = PackageListFilter
    serializer_class = PackageSerializer

    def get_action_permission_map(self):
        return {
            (
                "list",
                "list_install_pkg_types",
                "list_install_packages",
            ): []
        }

    def get_default_permission_class(self):
        return [ResourceActionPermission([ActionEnum.PACKAGE_MANAGE], ResourceEnum.DBTYPE, self.instance_getter)]

    @staticmethod
    def instance_getter(request, view):
        if view.action == "destroy":
            return [Package.objects.get(id=view.kwargs["pk"]).db_type]
        elif view.action == "bulk_create":
            return list(set([data["db_type"] for data in request.data["packages"]]))
        else:
            return [get_request_key_id(request, "db_type")]

    @common_swagger_auto_schema(
        operation_summary=_("新建版本文件"),
        tags=[DB_PACKAGE_TAG],
    )
    def create(self, request, *args, **kwargs):
        data = self.params_validate(self.get_serializer_class())
        data["updater"] = request.user.username
        data.update(update_at=timezone.now())
        # 先将暂存区文件转移到正式目录，再以正式路径入库，保证 DB 记录与制品库实际文件路径一致
        data["path"] = StorageHandler().move_staging_file_to_formal(data["path"])
        package, created = Package.objects.update_or_create(
            defaults=data,
            name=data["name"],
            # TODO: db_version后续会代替version
            version=data["version"],
            db_version=data.get("db_version"),
            pkg_type=data["pkg_type"],
            db_type=data["db_type"],
        )
        return Response(PackageSerializer(package).data)

    @common_swagger_auto_schema(
        operation_summary=_("批量创建介质"),
        tags=[DB_PACKAGE_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=BulkCreatePackageSerializer)
    def bulk_create(self, request, *args, **kwargs):
        """批量创建介质包，参考 create 方法的逻辑"""
        data = self.params_validate(self.get_serializer_class())
        packages_data = data["packages"]
        username = request.user.username
        now = timezone.now()

        storage_handler = StorageHandler()
        created_packages = []
        with atomic():
            for pkg_data in packages_data:
                pkg_data["updater"] = username
                pkg_data["update_at"] = now
                # 先将暂存区文件转移到正式目录，再以正式路径入库，保证 DB 记录与制品库实际文件路径一致
                pkg_data["path"] = storage_handler.move_staging_file_to_formal(pkg_data["path"])
                package, created = Package.objects.update_or_create(
                    defaults=pkg_data,
                    name=pkg_data["name"],
                    version=pkg_data["version"],
                    db_version=pkg_data.get("db_version"),
                    pkg_type=pkg_data["pkg_type"],
                    db_type=pkg_data["db_type"],
                )
                created_packages.append(package)

        return Response(PackageSerializer(created_packages, many=True).data)

    @common_swagger_auto_schema(
        operation_summary=_("同步制品库的文件信息(适用于medium初始化)"),
        tags=[DB_PACKAGE_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=SyncMediumSerializer)
    def sync_medium(self, request, *args, **kwargs):
        def package_identity_key(pkg):
            # 介质唯一身份：version 存的是 version_series 名，同一 series 下可有多个 full_version，故需叠加 full_version
            if isinstance(pkg, Package):
                full_version = pkg.db_version.full_version if pkg.db_version_id else ""
                return pkg.name, pkg.version, pkg.pkg_type, pkg.db_type, full_version
            return pkg["name"], pkg["version"], pkg["pkg_type"], pkg["db_type"], pkg["full_version"]

        def patch_version_model(info):
            # 获取发行版，不存在则不自动创建，返回 None 以跳过该介质的同步
            distribution = Distribution.objects.filter(
                name=info.pop("distribution_name"),
                engine=info.pop("distribution_engine"),
                db_type=info["db_type"],
                pkg_type=info["pkg_type"],
            ).first()
            if not distribution:
                logger.warning(f"distribution not found for medium: {info}, skip sync")
                return None
            # 获取版本系列
            version_series, __ = VersionSeries.objects.get_or_create(
                name=info.pop("version_series"), distribution=distribution
            )
            # 获取介质版本
            full_version = info.pop("full_version")
            dbversion = DBVersion.objects.filter(full_version=full_version, version_series=version_series).first()
            # 如果已存在则只修改更新时间
            if dbversion:
                dbversion.updated_at = info["update_at"]
                dbversion.save(update_fields=["update_at"])
            else:
                dbversion = DBVersion.objects.create(
                    full_version=full_version,
                    version_series=version_series,
                    distribution_snapshot=distribution.snapshot(),
                    description=info.pop("description", ""),
                    phase=info.pop("phase"),
                    name=info.pop("version_name"),
                )
            info.update(db_version=dbversion)
            return info

        data = self.params_validate(self.get_serializer_class())
        db_type, sync_medium_infos = data["db_type"], data["sync_medium_infos"]

        if not sync_medium_infos:
            return Response()

        # 获取原来介质的优先级信息（关联 db_version 以取到 full_version，避免 N+1 查询）
        old_packages = Package.objects.filter(db_type=db_type).select_related("db_version")
        old_package_map: Dict[Tuple, Package] = {package_identity_key(pkg): pkg for pkg in old_packages}
        # 更新新介质的优先级和启用信息，如果没有在原来介质中存在，则默认为0和启用
        update_packages, create_packages = [], []
        for info in sync_medium_infos:
            if info.get("pkg_type") not in PackageType.get_values():
                logger.warning(f"pkg type({info.get('pkg_type')}) not in PackageType Enum, ignore")
                continue

            pkg_key = package_identity_key(info)
            if pkg_key in old_package_map:
                old_package_map[pkg_key].__dict__.update(info)
                update_packages.append(old_package_map[pkg_key])
            else:
                info = patch_version_model(info)
                if info is None:
                    continue
                info.update(priority=0, enable=True)
                create_packages.append(Package(**info))

        # 按照DBType进行原子更新
        info_fields = list(sync_medium_infos[0].keys())
        update_fields = [field.name for field in Package._meta.fields if field.name in info_fields]
        with atomic():
            Package.objects.bulk_update(update_packages, fields=update_fields)
            Package.objects.bulk_create(create_packages)

        return Response()

    @common_swagger_auto_schema(
        operation_summary=_("查询版本文件列表"),
        tags=[DB_PACKAGE_TAG],
    )
    @Permission.decorator_external_permission_field(
        param_field=lambda d: d["db_type"],
        actions=[ActionEnum.PACKAGE_MANAGE],
        resource_meta=ResourceEnum.DBTYPE,
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
        if "priority" in self.request.data:
            obj = self.get_object()
            is_default = int(self.request.data["priority"]) > 0
            # 设为默认版本时，才需要把当前类型下其他的默认版本清零；取消默认仅影响自身
            if is_default:
                pkgs = Package.objects.filter(db_type=obj.db_type, pkg_type=obj.pkg_type)
                pkgs.exclude(id=obj.id).update(priority=0)
            # 联动修改V2推荐字段，一个发行版下只允许一个推荐版本
            if obj.db_version:
                if is_default:
                    dbs = DBVersion.objects.filter(distribution_id=obj.db_version.distribution_id)
                    dbs.exclude(id=obj.db_version_id).update(recommend=False)
                DBVersion.objects.filter(id=obj.db_version_id).update(recommend=is_default)

        super().partial_update(request, *args, **kwargs)
        return Response()

    @common_swagger_auto_schema(
        operation_summary=_("删除版本文件"),
        tags=[DB_PACKAGE_TAG],
    )
    def destroy(self, request, *args, **kwargs):
        # 如果关联了实例，则不允许删除
        package = self.get_object()
        if package.storageinstance_set.exists() or package.proxyinstance_set.exists():
            raise DBPackageBaseException(_("请保证该版本文件没有关联实例"))
        path = package.path
        # 删除本地记录
        super().destroy(request, *args, **kwargs)
        # 记录删除后再清理制品库文件，路径仍被其他介质包引用时会自动跳过
        Package.clean_unreferenced_files([path])
        return Response()

    @common_swagger_auto_schema(
        operation_summary=_("删除版本文件"), tags=[DB_PACKAGE_TAG], request_body=BulkDeletePackageSerializer()
    )
    @action(methods=["DELETE"], detail=False, serializer_class=BulkDeletePackageSerializer)
    def bulk_destroy(self, request, *args, **kwargs):
        package_ids = self.validated_data["package_ids"]
        # 检查是否有关联实例
        if StorageInstance.objects.filter(db_package__in=package_ids).exists():
            raise DBPackageBaseException(_("请保证该版本文件没有关联实例"))
        if ProxyInstance.objects.filter(db_package__in=package_ids).exists():
            raise DBPackageBaseException(_("请保证该版本文件没有关联实例"))
        packages = Package.objects.filter(id__in=package_ids)
        paths = list(packages.values_list("path", flat=True))
        # 删除本地记录
        packages.delete()
        # 记录删除后再清理制品库文件，路径仍被其他介质包引用时会自动跳过
        Package.clean_unreferenced_files(paths)
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
                name=os.path.join(slz.validated_data["db_type"], slz.validated_data["pkg_type"], version, file_name),
                content=upload_file,
            )
        return Response({"name": file_name, "size": file.size, "md5": md5, "path": path, "version": version})

    @common_swagger_auto_schema(
        operation_summary=_("获取介质支持的操作系统"),
        tags=[DB_PACKAGE_TAG],
    )
    @action(methods=["GET"], detail=False, serializer_class=None, filter_class=None)
    def list_support_systems(self, request, *args, **kwargs):
        systems = SystemSettings.get_setting_value(
            key=SystemSettingsEnum.PACKAGE_SUPPORT_SYSTEMS, default=DEFAULT_PACKAGE_SUPPORT_SYSTEMS
        )
        return Response(systems)
