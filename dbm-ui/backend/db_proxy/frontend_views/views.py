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
from typing import Dict, List

from django.utils.translation import gettext_lazy as _
from rest_framework.decorators import action
from rest_framework.response import Response

from backend.bk_web.swagger import common_swagger_auto_schema
from backend.bk_web.viewsets import SystemViewSet
from backend.components.hadb.client import HADBApi
from backend.db_proxy.constants import ExtensionType
from backend.db_proxy.frontend_views.serializers import ListDBExtensionSerializer
from backend.db_proxy.models import DBExtension
from backend.db_services.ipchooser.query.resource import ResourceQueryHelper
from backend.iam_app.dataclass import ActionEnum
from backend.iam_app.handlers.drf_perm.base import ResourceActionPermission

SWAGGER_TAG = _("云区域组件")


class DBExtensionViewSet(SystemViewSet):
    """云区域组件视图"""

    action_permission_map = {("fetch_available_clouds",): []}
    default_permission_class = [ResourceActionPermission([ActionEnum.PLATFORM_MANAGE])]
    pagination_class = None

    @common_swagger_auto_schema(
        operation_summary=_("获取可用云区域"),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=False)
    def fetch_available_clouds(self, request, *args, **kwargs):
        bk_cloud_ids = DBExtension.objects.values_list("bk_cloud_id", flat=True).distinct()
        cloud_map = ResourceQueryHelper.search_cc_cloud(get_cache=True)
        cloud_infos = [
            {"bk_cloud_id": cloud, "bk_cloud_name": cloud_map[str(cloud)]["bk_cloud_name"]} for cloud in bk_cloud_ids
        ]
        return Response(cloud_infos)

    @common_swagger_auto_schema(
        operation_summary=_("获取云区域组件信息"),
        tags=[SWAGGER_TAG],
        query_serializer=ListDBExtensionSerializer(),
    )
    @action(methods=["GET"], detail=False, serializer_class=ListDBExtensionSerializer)
    def fetch_extensions(self, request, *args, **kwargs):
        bk_cloud_id = self.validated_data["bk_cloud_id"]
        db_extensions = DBExtension.objects.filter(bk_cloud_id=bk_cloud_id).values()

        # 根据 extension 分组，并格式化组件信息
        db_extension_map: Dict[ExtensionType, List] = {e: [] for e in ExtensionType.get_values()}
        for db_extension in db_extensions:
            db_extension.update(db_extension["details"])
            # 忽略不展示的组件
            if not hasattr(self.serializer_class, db_extension["extension"]):
                continue
            serializer = getattr(self.serializer_class, db_extension["extension"])(data=db_extension)
            serializer.is_valid()
            db_extension_map[db_extension["extension"]].append(serializer.data)

        # 目前dbha展示信息直接从hadb api获取
        params = {"name": "agent_get_agent_info", "query_args": {"cloud_id": bk_cloud_id}}
        dbha_infos = HADBApi.ha_status(params)
        for info in dbha_infos:
            info["bk_cloud_id"] = info.pop("cloud_id", 0)
            info["bk_city_name"] = info.pop("campus", "")
        db_extension_map[ExtensionType.DBHA] = dbha_infos

        return Response(db_extension_map)
