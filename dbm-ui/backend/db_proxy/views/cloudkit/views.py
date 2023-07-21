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

from django.forms.models import model_to_dict
from django.utils.translation import ugettext_lazy as _
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from backend.bk_web.pagination import AuditedLimitOffsetPagination
from backend.bk_web.swagger import common_swagger_auto_schema
from backend.bk_web.viewsets import SystemViewSet
from backend.db_proxy.models import DBCloudKit, DBExtension
from backend.db_services.ipchooser.query.resource import ResourceQueryHelper
from backend.iam_app.handlers.drf_perm.base import DBManagePermission

from .filters import DBCloudKitListFilter
from .serializers import CheckDBCloudKitExist, DBCloudKitListResponseSerializer

SWAGGER_TAG = _("云区域管理")


class CloudKitViewSet(SystemViewSet):
    """云区域管理视图接口"""

    pagination_class = AuditedLimitOffsetPagination
    queryset = DBCloudKit.objects.prefetch_related("dbextension_set").all()
    filter_class = None

    def _get_custom_permissions(self):
        return [DBManagePermission()]

    @common_swagger_auto_schema(
        operation_summary=_("获取DB套件列表信息"),
        responses={status.HTTP_200_OK: DBCloudKitListResponseSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=False, filter_class=DBCloudKitListFilter)
    def list_cloudkit(self, request, *args, **kwargs):
        # 获取云区域套件查询集
        cloud_kits = self.filter_queryset(self.get_queryset())
        page_cloud_kits = self.paginate_queryset(cloud_kits)
        cloud_info = ResourceQueryHelper.search_cc_cloud(get_cache=True)
        # 获取每个组件的信息
        page_cloud_kit_infos: List[Dict] = []
        for cloud_kit in page_cloud_kits:
            cloud_kit_info = model_to_dict(cloud_kit)
            cloud_kit_info["bk_cloud_name"] = cloud_info[str(cloud_kit_info["bk_cloud_id"])]["bk_cloud_name"]
            cloud_kit_info.update(DBExtension.get_extension_info(cloud_kit.dbextension_set.all()))
            page_cloud_kit_infos.append(cloud_kit_info)

        return Response({"count": cloud_kits.count(), "results": page_cloud_kit_infos})

    @common_swagger_auto_schema(
        operation_summary=_("检查云区域组件是否部署"),
        query_serializer=CheckDBCloudKitExist(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=False, serializer_class=CheckDBCloudKitExist)
    def check_cloudkit_exist(self, request, *args, **kwargs):
        bk_cloud_id = self.params_validate(self.get_serializer_class())["bk_cloud_id"]
        is_exist = DBExtension.objects.filter(bk_cloud_id=bk_cloud_id).exists()
        return Response(is_exist)
