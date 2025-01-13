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
from collections import defaultdict
from datetime import datetime, timezone
from typing import Dict

from django.core.cache import cache
from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from backend.bk_web import viewsets
from backend.bk_web.pagination import AuditedLimitOffsetPagination
from backend.bk_web.swagger import common_swagger_auto_schema
from backend.bk_web.viewsets import AuditedModelViewSet
from backend.configuration.models import DBAdministrator
from backend.db_report.enums import REPORT_COUNT_CACHE_KEY, SWAGGER_TAG, ReportType
from backend.db_report.filters import ReportFilterBackend
from backend.db_report.register import db_report_maps
from backend.db_report.serializers import GetReportCountSerializer, GetReportOverviewSerializer
from backend.iam_app.handlers.drf_perm.db_report import DBReportPermission


class ReportBaseViewSet(AuditedModelViewSet):
    # 分页类
    pagination_class = AuditedLimitOffsetPagination
    # 巡检类型
    report_type = None
    # 巡检名称
    report_name = ""
    # 巡检表头
    report_title = []
    # 巡检过滤类
    filter_backends = [ReportFilterBackend]
    filter_fields = {
        "bk_biz_id": ["exact"],
        "cluster_type": ["exact", "in"],
        "create_at": ["gte", "lte"],
        "status": ["exact", "in"],
    }
    # 鉴权类
    action_permission_map = {("list",): [DBReportPermission()]}

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        response.data["name"] = self.report_name or ReportType.get_choice_label(self.report_type)
        response.data["title"] = self.report_title
        return response


class ReportCommonViewSet(viewsets.SystemViewSet):
    """巡检通用接口视图"""

    default_permission_class = []

    @common_swagger_auto_schema(
        operation_summary=_("获取巡检报告总览"),
        responses={status.HTTP_200_OK: GetReportOverviewSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=False, serializer_class=GetReportOverviewSerializer)
    def get_report_overview(self, request, *args, **kwargs):
        db_report_types = defaultdict(list)
        for db_type, report_cls_list in db_report_maps.items():
            db_report_types[db_type] = [cls.report_type for cls in report_cls_list]
            db_report_types[db_type].sort()
        return Response(db_report_types)

    @common_swagger_auto_schema(
        operation_summary=_("获取巡检报告代办数量"),
        responses={status.HTTP_200_OK: GetReportCountSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=False, serializer_class=GetReportCountSerializer)
    def get_report_count(self, request, *args, **kwargs):
        username = request.user.username
        cache_key = REPORT_COUNT_CACHE_KEY.format(user=username)

        # 有缓存优先返回缓存，数量精确性要求性不高
        report_count_cache = cache.get(cache_key)
        if report_count_cache:
            return Response(report_count_cache)

        report_count_map: Dict[str, Dict[str, Dict]] = defaultdict(lambda: defaultdict(dict))
        for db_type, report_classes in db_report_maps.items():
            # 获取用户的管理业务和协助业务
            manage_bizs, assist_bizs = DBAdministrator.get_manage_bizs(db_type, username)
            for cls in report_classes:
                # 过滤当天的代办
                now_date = datetime.now(timezone.utc).date()
                queryset = cls.queryset.filter(status=False, update_at__gte=now_date)
                report_count_map[db_type][cls.report_type].update(
                    manage_count=queryset.filter(status=False, bk_biz_id__in=manage_bizs).count(),
                    assist_count=queryset.filter(status=False, bk_biz_id__in=assist_bizs).count(),
                )

        # 默认可以做1h的缓存
        cache.set(cache_key, report_count_map, 60 * 60)
        return Response(report_count_map)
