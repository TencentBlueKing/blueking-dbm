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
from collections import defaultdict
from typing import Dict, Iterable, List, Optional

from django.db.models import Count
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers
from rest_framework.decorators import action
from rest_framework.response import Response

from backend.bk_web import viewsets
from backend.bk_web.swagger import common_swagger_auto_schema
from backend.configuration.constants import SystemSettingsEnum
from backend.configuration.models import SystemSettings
from backend.db_meta.models import DBVersion, Distribution, ProxyInstance, StorageInstance, VersionSeries
from backend.db_package.constants import INIT_DB_PKG_SETTINGS, PackageType
from backend.db_package.models import Package
from backend.db_services.version.exceptions import VersionBaseException
from backend.db_services.version.serializers import (
    DBPackageTypeItemSerializer,
    DBPackageTypeListQuerySerializer,
    DBPackageTypeUpdateSerializer,
    DBVersionConflictCheckResponseSerializer,
    DBVersionConflictCheckSerializer,
    DBVersionSerializer,
)
from backend.db_services.version.utils import pad_full_version
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

    if view.action in ["list_pkg_types", "update_pkg_types"]:
        db_type = get_request_key_id(request, "db_type")
        return [db_type] if db_type else []

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

    action_permission_map = {
        ("list_pkg_types", "check_name_conflict", "list"): [],
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
                _clear_distribution_recommend(version_series.distribution)
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
        packages = Package.objects.filter(id__in=package_ids)
        paths = list(packages.values_list("path", flat=True))
        # 删除本地记录
        packages.delete()
        # 记录删除后再清理制品库文件，路径仍被其他介质包引用时会自动跳过
        Package.clean_unreferenced_files(paths)
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

        if request.data.get("recommend") is not None:
            recommend = bool(request.data["recommend"])
            # 一个发行版下只允许一个推荐版本，因此设为推荐时才需要清理其他版本的推荐标记
            if recommend:
                distribution = instance.version_series.distribution
                _clear_distribution_recommend(distribution, exclude_version_id=instance.id)
            # 联动修改v1的推荐字段，取消推荐仅影响当前版本自身
            Package.objects.filter(db_version=instance).update(priority=int(recommend))

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

    @common_swagger_auto_schema(
        operation_summary=_("获取某 DB 类型下的 pkg 类型配置"),
        query_serializer=DBPackageTypeListQuerySerializer(),
        responses={200: DBPackageTypeItemSerializer(many=True)},
        tags=[SWAGGER_TAG],
    )
    @action(
        detail=False,
        methods=["GET"],
        serializer_class=DBPackageTypeListQuerySerializer,
        pagination_class=None,
        filter_fields=None,
    )
    def list_pkg_types(self, request, *args, **kwargs):
        """
        返回某 db_type 下的 pkg 类型配置列表
        """
        db_type = self.params_validate(self.get_serializer_class())["db_type"]
        pkg_settings = SystemSettings.get_setting_value(
            key=SystemSettingsEnum.DB_PACKAGE_SETTINGS, default=INIT_DB_PKG_SETTINGS
        )
        items = pkg_settings.get(db_type, [])

        # 一次 group by 拿到 {pkg_type: dbversion_count}
        pkg_type_values = [item["value"] for item in items]
        version_count_map = dict(
            DBVersion.objects.filter(
                version_series__distribution__db_type=db_type,
                version_series__distribution__pkg_type__in=pkg_type_values,
            )
            .values("version_series__distribution__pkg_type")
            .annotate(cnt=Count("id"))
            .values_list("version_series__distribution__pkg_type", "cnt")
        )
        # 一次 group by 拿到 {pkg_type: distribution_count}
        distribution_count_map = dict(
            Distribution.objects.filter(db_type=db_type, pkg_type__in=pkg_type_values)
            .values("pkg_type")
            .annotate(cnt=Count("id"))
            .values_list("pkg_type", "cnt")
        )
        # 是否可删除
        delete_rules = _build_pkg_delete_rules(db_type, pkg_type_values)

        db_pkg_settings = [
            {
                "name": item.get("name", PackageType.get_choice_label(item["value"])),
                "value": item["value"],
                "version_num": item["version_num"],
                "related_versions": version_count_map.get(item["value"], 0),
                "related_distributions": distribution_count_map.get(item["value"], 0),
                "can_delete": delete_rules[item["value"]] is not None,
            }
            for item in items
        ]
        return Response(db_pkg_settings)

    @common_swagger_auto_schema(
        operation_summary=_("覆盖更新某 DB 类型下的 pkg 类型配置"),
        request_body=DBPackageTypeUpdateSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(
        detail=False,
        methods=["POST"],
        serializer_class=DBPackageTypeUpdateSerializer,
        pagination_class=None,
        filter_fields=None,
    )
    def update_pkg_types(self, request, *args, **kwargs):
        """
        覆盖更新某 db_type 下的 pkg 类型配置
        - 要求前端全量传递该 db_type 下的所有 pkg 定义, 服务端按 db_type 整段替换
        - 其他 db_type 的配置不受影响
        - 仅入库 value/version_num; name 在读时动态派生
        - 对新增的 pkg 类型, 创建占位发行版 (name=DBM, engine="")
        - 对删除的 pkg 类型, 按 _build_pkg_delete_rules 规则校验, 允许时级联删除 DBM 占位
        """
        data = self.params_validate(self.get_serializer_class())
        db_type = data["db_type"]

        # 计算新增 / 删除项 (相对于现有配置)
        pkg_settings = SystemSettings.get_setting_value(
            key=SystemSettingsEnum.DB_PACKAGE_SETTINGS, default=INIT_DB_PKG_SETTINGS
        )
        origin_values = {str(item["value"]) for item in pkg_settings.get(db_type, [])}
        new_values = {str(item["value"]) for item in data["items"]}
        added_pkg_types = new_values - origin_values
        removed_pkg_types = origin_values - new_values

        # 校验删除项, 不可删的拒绝整次更新; 允许的收集要级联删除的 DBM 占位 ID
        cascade_distribution_ids: List[int] = []
        if removed_pkg_types:
            delete_rules = _build_pkg_delete_rules(db_type, removed_pkg_types)
            if any(ids is None for ids in delete_rules.values()):
                raise serializers.ValidationError(_("存在关联发行版/介质版本，不允许删除"))
            cascade_distribution_ids = [i for ids in delete_rules.values() if ids for i in ids]

        # 1. 覆盖更新 pkg 配置
        pkg_settings[db_type] = data["items"]
        SystemSettings.insert_setting_value(
            key=SystemSettingsEnum.DB_PACKAGE_SETTINGS,
            value=pkg_settings,
            value_type="dict",
            user=request.user.username,
        )

        # 2. 对新增的 pkg 类型直接创建 DBM 占位发行版
        add_dbs = [Distribution(name="DBM", engine="", db_type=db_type, pkg_type=pt) for pt in added_pkg_types]
        if add_dbs:
            Distribution.objects.bulk_create(add_dbs)

        # 3. 级联删除可删 pkg 类型下的 DBM 占位发行版
        VersionSeries.objects.filter(distribution_id__in=cascade_distribution_ids).delete()
        Distribution.objects.filter(id__in=cascade_distribution_ids).delete()

        return Response()


def _clear_distribution_recommend(distribution: Distribution, exclude_version_id: Optional[int] = None) -> None:
    """
    清除某发行版下的推荐标记, 用于保证一个发行版下最多只有一个推荐版本
    v1 中推荐版本由 Package.priority 表达, 需要一起清零
    """
    versions = DBVersion.objects.filter(version_series__distribution=distribution.id)
    packages = Package.objects.filter(db_type=distribution.db_type, pkg_type=distribution.pkg_type)
    if exclude_version_id is not None:
        versions = versions.exclude(id=exclude_version_id)
        packages = packages.exclude(db_version_id=exclude_version_id)

    versions.update(recommend=False)
    packages.update(priority=0)


def _build_pkg_delete_rules(db_type: str, pkg_types: Iterable[str]) -> Dict[str, Optional[List[int]]]:
    """
    判断每个 pkg_type 是否可删除, 返回 {pkg_type: dbm_distribution_ids 或 None}
    - None: 不可删 (存在非 DBM 发行版 或 存在 DBVersion)
    - list: 可删, 元素为需级联删除的 DBM 占位发行版 ID (无 DBM 时为空列表)
    """
    pkg_types = list(pkg_types)
    if not pkg_types:
        return {}

    dbm_ids: Dict[str, List[int]] = defaultdict(list)
    blocked: set = set()
    for d in Distribution.objects.filter(db_type=db_type, pkg_type__in=pkg_types).values("id", "name", "pkg_type"):
        if d["name"].lower() == "dbm":
            dbm_ids[d["pkg_type"]].append(d["id"])
        else:
            blocked.add(d["pkg_type"])

    blocked |= set(
        DBVersion.objects.filter(
            version_series__distribution__db_type=db_type,
            version_series__distribution__pkg_type__in=pkg_types,
        ).values_list("version_series__distribution__pkg_type", flat=True)
    )

    return {pt: None if pt in blocked else dbm_ids[pt] for pt in pkg_types}
