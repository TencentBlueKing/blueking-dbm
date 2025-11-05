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
from django.utils.translation import gettext_lazy as _
from rest_framework.decorators import action
from rest_framework.response import Response

from backend.bk_web.swagger import common_swagger_auto_schema
from backend.db_proxy.constants import SWAGGER_TAG
from backend.db_proxy.views.redis_keystat_report.serializers import (
    CreateKeyStatRankItemSerializer,
    CreateKeyStatReportItemSerializer,
    CreateKeyStatReportRecordSerializer,
    UpdateKeyStatReportRecordSerializer,
)
from backend.db_proxy.views.views import BaseProxyPassViewSet
from backend.db_services.redis.redis_keystat_report.models.redis_keystat_report import (
    RankItem,
    ReportItem,
    ReportRecord,
)


class KeyStatReportViewSet(BaseProxyPassViewSet):
    """
    KeyStatReport API 代理
    """

    @common_swagger_auto_schema(
        operation_summary=_("创建内存分析统计报告"),
        request_body=CreateKeyStatReportRecordSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(
        methods=["POST"],
        detail=False,
        serializer_class=CreateKeyStatReportRecordSerializer,
    )
    def create_keystat_report_record(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        report_data = serializer.validated_data
        ReportRecord.objects.create(**report_data.dict())
        return Response({"success": True})

    @common_swagger_auto_schema(
        operation_summary=_("更新内存分析统计报告"),
        request_body=UpdateKeyStatReportRecordSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(
        methods=["POST"],
        detail=False,
        serializer_class=UpdateKeyStatReportRecordSerializer,
    )
    def update_keystat_report_record(self, request):
        """
        更新内存分析统计报告状态、
        执行ip、分析时长、redis版本、数据来源类型、数据来源角色、数据来源地址列表、atime可用性、参与分析的分片数、集群分片数
        """
        record_id = request.data.get("record_id", 0)
        if record_id <= 0:
            raise Exception("record_id is required")
        print("request.data", request.data)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ReportRecord.objects.filter(record_id=record_id).update(**serializer.validated_data)
        return Response({"success": True})

    @common_swagger_auto_schema(
        operation_summary=_("写入内存分析统计报告详情"),
        request_body=CreateKeyStatReportItemSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(
        methods=["POST"],
        detail=False,
        serializer_class=CreateKeyStatReportItemSerializer,
    )
    def upsert_keystat_report_item(self, request):
        # 在分批写入记录时，需要先清空记录表中 record_id 对应的记录.
        truncate = request.data.get("truncate", False)
        if truncate:
            record_id = request.data.get("record_id", 0)
            if record_id > 0:
                ReportItem.objects.filter(record_id=record_id).delete()
            else:
                raise Exception("record_id is required when truncate is true")

        # 继续写入记录表中 record_id 对应的记录.
        keystat_report_item = request.data.get("keystat_report_item", [])
        print("keystat_report_item", keystat_report_item)
        serializer = self.get_serializer(data=keystat_report_item, many=True)
        serializer.is_valid(raise_exception=True)
        items = [ReportItem(**item) for item in serializer.validated_data]
        ReportItem.objects.bulk_create(items)
        return Response(
            {
                "success": True,
                "affected_rows": len(items),
            }
        )

    @common_swagger_auto_schema(
        operation_summary=_("写入内存分析统计排行详情"),
        request_body=CreateKeyStatRankItemSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(
        methods=["POST"],
        detail=False,
        serializer_class=CreateKeyStatRankItemSerializer,
    )
    def upsert_keystat_rank_item(self, request):
        # 在分批写入记录时，需要先清空记录表中 record_id 对应的记录.
        truncate = request.data.get("truncate", False)
        if truncate:
            record_id = request.data.get("record_id", 0)
            if record_id > 0:
                RankItem.objects.filter(record_id=record_id).delete()
            else:
                raise Exception("record_id is required when truncate is true")
        keystat_rank_item = request.data.get("keystat_rank_item", [])
        serializer = self.get_serializer(data=keystat_rank_item, many=True)
        serializer.is_valid(raise_exception=True)
        items = [RankItem(**item) for item in serializer.validated_data]
        RankItem.objects.bulk_create(items)
        return Response(
            {
                "success": True,
                "affected_rows": len(items),
            }
        )
