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

from django.utils.translation import ugettext as _
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from backend.bk_web import viewsets
from backend.bk_web.pagination import AuditedLimitOffsetPagination
from backend.bk_web.swagger import common_swagger_auto_schema
from backend.configuration.constants import DBType
from backend.db_meta.models import AppCache
from backend.db_services.redis.hot_key_analysis.filters import RedisHotKeyAnalysisFilter, RedisHotKeyDetailsFilter
from backend.db_services.redis.hot_key_analysis.models import RedisHotKeyRecord, RedisHotKeyRecordDetail
from backend.db_services.redis.hot_key_analysis.serializers import (
    AnalysisRecordsSerializer,
    ExportHotKeyDetailSerializer,
    QueryHotKeyDetailSerializer,
)
from backend.iam_app.handlers.drf_perm.base import DBManagePermission
from backend.utils.excel import ExcelHandler

SWAGGER_TAG = "db_services/redis/hot_key_analysis"


class RedisHotKeyAnalysisViewSet(viewsets.SystemViewSet):
    queryset = RedisHotKeyRecord.objects.all()
    default_permission_class = [DBManagePermission()]
    pagination_class = AuditedLimitOffsetPagination
    filter_class = RedisHotKeyAnalysisFilter

    @common_swagger_auto_schema(
        operation_summary=_("获取热key分析记录"),
        tags=[SWAGGER_TAG],
        responses={status.HTTP_200_OK: AnalysisRecordsSerializer()},
    )
    @action(methods=["GET"], detail=False)
    def query_analysis_records(self, request, bk_biz_id):
        analysis_qs = self.paginate_queryset(
            self.filter_queryset(self.queryset.filter(bk_biz_id=bk_biz_id).order_by("-create_at"))
        )
        analysis_data = AnalysisRecordsSerializer(analysis_qs, many=True).data
        return self.paginator.get_paginated_response(data=analysis_data)


class RedisHotKeyDetailsViewSet(viewsets.SystemViewSet):
    default_permission_class = [DBManagePermission()]
    queryset = RedisHotKeyRecordDetail.objects.all()
    filter_class = RedisHotKeyDetailsFilter
    serializer_class = QueryHotKeyDetailSerializer

    @common_swagger_auto_schema(
        operation_summary=_("获取热key分析记录详情"),
        tags=[SWAGGER_TAG],
        query_serializer=QueryHotKeyDetailSerializer(),
        responses={status.HTTP_200_OK: QueryHotKeyDetailSerializer()},
    )
    @action(methods=["GET"], detail=False)
    def get_analysis_details(self, request, bk_biz_id):
        data = self.params_validate(self.get_serializer_class())
        record_id = data.get("record_id", 0)
        querysets = self.filter_queryset(self.queryset.filter(bk_biz_id=bk_biz_id, record_id=record_id))

        result = defaultdict(list)
        for queryset in querysets:
            instance_data = {
                "id": queryset.id,
                "cmd_info": queryset.cmd_info,
                "key": queryset.key,
                "exec_count": queryset.exec_count,
                "ratio": queryset.ratio,
            }
            result[queryset.ins].append(instance_data)

        return Response(result)

    @common_swagger_auto_schema(
        operation_summary=_("导出热key分析记录"),
        query_serializer=ExportHotKeyDetailSerializer(),
        tags=[SWAGGER_TAG],
        responses={status.HTTP_200_OK: ExportHotKeyDetailSerializer()},
    )
    @action(methods=["GET"], detail=False, serializer_class=ExportHotKeyDetailSerializer)
    def export_hot_key_analysis(self, request, bk_biz_id: int):
        data = self.params_validate(self.get_serializer_class())
        record_ids = data.get("record_ids", "")
        querysets = self.filter_queryset(
            self.queryset.filter(bk_biz_id=bk_biz_id, record_id__in=record_ids.split(","))
        )

        headers = [
            {"id": "ins", "name": _("实例列表")},
            {"id": "cmd_info", "name": _("执行命令")},
            {"id": "key", "name": _("key")},
            {"id": "exec_count", "name": _("数量")},
            {"id": "ratio", "name": _("执行占比")},
        ]

        data_list = [
            {
                "ins": record.ins,
                "cmd_info": record.cmd_info,
                "key": record.key,
                "exec_count": record.exec_count,
                "ratio": f"{record.ratio}%",
            }
            for record in querysets
        ]

        biz_name = AppCache.get_biz_name(bk_biz_id)
        db_type = DBType.Redis
        wb = ExcelHandler.serialize(data_list, headers=headers, match_header=True)
        return ExcelHandler.response(wb, f"{biz_name}({bk_biz_id}){db_type}_hot_key_analysis.xlsx")
