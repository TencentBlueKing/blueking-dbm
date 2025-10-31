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

from django.utils.translation import gettext as _
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.response import Response

from backend.bk_web import viewsets
from backend.bk_web.pagination import AuditedLimitOffsetPagination
from backend.bk_web.swagger import common_swagger_auto_schema
from backend.configuration.constants import DBType
from backend.db_services.redis.capacity_evaluate_service.util import UNIFY_QUERY_PARAMS
from backend.db_services.redis.redis_keystat_report.filters import (
    KeyStatRecordDetailFilter,
    KeyStatReportRecordFilter,
    RankItemDetailFilter,
)
from backend.db_services.redis.redis_keystat_report.models import RankItem, ReportItem, ReportRecord
from backend.db_services.redis.redis_keystat_report.serializers import (
    ExportKeyStatDetailSerializer,
    KeyStatRecordDetailSerializer,
    KeyStatReportRecordsSerializer,
    RankItemDetailSerializer,
    ReportItemDetailSerializer,
)
from backend.iam_app.handlers.drf_perm.base import DBManagePermission
from backend.utils.excel import ExcelHandler
from backend.utils.string import format_size

SWAGGER_TAG = "db_services/redis/redis_keystat_report"


class KeyStatReportViewSet(viewsets.SystemViewSet):
    queryset = ReportRecord.objects.all()
    default_permission_class = [DBManagePermission()]
    pagination_class = AuditedLimitOffsetPagination
    filter_class = KeyStatReportRecordFilter

    @common_swagger_auto_schema(
        operation_summary=_("获取redis内存分析记录"),
        tags=[SWAGGER_TAG],
        responses={status.HTTP_200_OK: KeyStatReportRecordsSerializer()},
    )
    @action(methods=["GET"], detail=False)
    def query_keystat_records(self, request, bk_biz_id):
        keystat_qs = self.paginate_queryset(
            self.filter_queryset(self.queryset.filter(bk_biz_id=bk_biz_id).order_by("-create_at"))
        )
        keystat_data = KeyStatReportRecordsSerializer(keystat_qs, many=True).data
        return self.paginator.get_paginated_response(data=keystat_data)


class KeyStatReportDetailsViewSet(viewsets.SystemViewSet):
    default_permission_class = [DBManagePermission()]
    queryset = ReportItem.objects.all().order_by("-mem_used_bytes")
    filter_class = KeyStatRecordDetailFilter
    serializer_class = KeyStatRecordDetailSerializer

    @common_swagger_auto_schema(
        operation_summary=_("获取redis内存分析记录详情"),
        tags=[SWAGGER_TAG],
        query_serializer=KeyStatRecordDetailSerializer(),
        responses={status.HTTP_200_OK: ReportItemDetailSerializer()},
    )
    @action(methods=["GET"], detail=False)
    def get_keystat_details(self, request, bk_biz_id):
        data = self.params_validate(self.get_serializer_class())
        record_id = data.get("record_id", 0)
        querysets = self.filter_queryset(self.queryset.filter(record_id=record_id))
        keystat_data = ReportItemDetailSerializer(querysets, many=True).data
        return Response(keystat_data)

    @common_swagger_auto_schema(
        operation_summary=_("获取redis内存分析大Key排行榜"),
        tags=[SWAGGER_TAG],
        query_serializer=KeyStatRecordDetailSerializer(),
        responses={status.HTTP_200_OK: RankItemDetailSerializer()},
    )
    @action(
        methods=["GET"],
        detail=False,
        serializer_class=RankItemDetailSerializer,
        queryset=RankItem.objects.all().order_by("-memory_size"),
        filter_class=RankItemDetailFilter,
    )
    def get_keystat_rank(self, request, bk_biz_id):
        data = self.params_validate(self.get_serializer_class())
        record_id = data.get("record_id", 0)
        querysets = self.filter_queryset(self.queryset.filter(record_id=record_id))
        keystat_data = RankItemDetailSerializer(querysets, many=True).data
        return Response(keystat_data)

    @common_swagger_auto_schema(
        operation_summary=_("导出内存分析记录"),
        query_serializer=ExportKeyStatDetailSerializer(),
        tags=[SWAGGER_TAG],
        responses={status.HTTP_200_OK: ExportKeyStatDetailSerializer()},
    )
    @action(methods=["GET"], detail=False, serializer_class=ExportKeyStatDetailSerializer)
    def export_keystat_analysis(self, request, bk_biz_id):

        data = self.params_validate(self.get_serializer_class())
        record_ids = data.get("record_ids", "")

        # 处理内存分析导出报告
        key_stat_querysets = self.filter_queryset(self.queryset.filter(record_id__in=record_ids.split(",")))
        headers = [
            {"id": "key_type", "name": _("Key类型")},
            {"id": "key_class", "name": _("Key模式")},
            {"id": "key_name", "name": _("Key样本")},
            {"id": "count", "name": _("数量")},
            {"id": "count_with_ttl", "name": _("数量(有过期)")},
            {"id": "avg_ttl", "name": _("过期时间")},
            {"id": "min_idletime", "name": _("最近访问时间")},
            {"id": "avg_key_used_bytes", "name": _("单Key平均内存占用")},
            {"id": "avg_key_length", "name": _("平均成员数量")},
            {"id": "mem_used_bytes", "name": _("内存占用")},
            {"id": "mem_used_pct", "name": _("内存占用占比")},
        ]

        key_stat_data = [
            {
                "key_type": queryset.key_type,
                "key_class": queryset.key_class,
                "key_name": queryset.key_name,
                "count": queryset.count,
                "count_with_ttl": queryset.count_with_ttl,
                "avg_ttl": str(queryset.avg_ttl) + "s",
                "min_idletime": str(queryset.min_idletime) + "s",
                "avg_key_used_bytes": format_size(queryset.avg_key_used_bytes),
                "avg_key_length": queryset.avg_key_length,
                "mem_used_bytes": format_size(queryset.mem_used_bytes),
                "mem_used_pct": str(queryset.mem_used_pct) + "%",
            }
            for queryset in key_stat_querysets
        ]

        # 处理rank大Key排行榜查询集导出
        rank_querysets = RankItemDetailFilter(
            data=request.GET, queryset=RankItem.objects.filter(record_id__in=record_ids.split(","))
        ).qs
        rank_headers = [
            {"id": "key_type", "name": _("Key类型")},
            {"id": "key_name", "name": _("Key名称")},
            {"id": "ttl", "name": _("过期时间")},
            {"id": "key_length", "name": _("Key长度")},
            {"id": "value_size", "name": _("Value长度")},
            {"id": "member", "name": _("成员数量")},
            {"id": "member_len", "name": _("成员平均长度")},
            {"id": "memory_size", "name": _("内存占用")},
        ]

        rank_data = [
            {
                "key_type": queryset.key_type,
                "key_name": queryset.key_name,
                "ttl": str(queryset.ttl) + "s",
                "key_length": queryset.key_length,
                "value_size": format_size(queryset.value_size),
                "member": queryset.member,
                "member_len": queryset.member_len,
                "memory_size": format_size(queryset.memory_size),
            }
            for queryset in rank_querysets
        ]

        wb = ExcelHandler.serialize(key_stat_data, headers=headers, match_header=True, sheet_name=_("内存分析报告"))
        ExcelHandler.add_sheet(
            wb=wb, sheet_name=_("大Key排行榜"), data_dict__list=rank_data, headers=rank_headers, match_header=True
        )

        db_type = DBType.Redis
        return ExcelHandler.response(wb, f"{bk_biz_id}_{db_type}_keystat_analysis.xlsx")
