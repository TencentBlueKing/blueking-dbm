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
from typing import Dict

from django.db.models import Count
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.filters import OrderingFilter
from rest_framework.response import Response

from backend.bk_web import viewsets
from backend.bk_web.pagination import AuditedLimitOffsetPagination
from backend.bk_web.swagger import common_swagger_auto_schema
from backend.bk_web.viewsets import AuditedModelViewSet
from backend.configuration.constants import SystemSettingsEnum
from backend.configuration.models import DBAdministrator, SystemSettings
from backend.db_report.enums import SWAGGER_TAG, ReportStateType, ReportType
from backend.db_report.filters import DrillReportFilterBackend, ReportFilterBackend, ReportListFilter
from backend.db_report.register import db_report_maps, report_kind_register_map
from backend.db_report.serializers import GetReportCountSerializer, GetReportOverviewSerializer
from backend.iam_app.handlers.drf_perm.db_report import DBReportPermission


class ReportBaseViewSet(AuditedModelViewSet):
    # 序列化器
    serializer_class = None
    # 分页类
    pagination_class = AuditedLimitOffsetPagination
    # 巡检类型
    report_type = None
    # 巡检名称
    report_name = ""
    # 巡检表头
    report_title = []
    # 巡检过滤/排序
    filter_backends = [ReportFilterBackend, OrderingFilter]
    filter_fields = {
        "cluster_type": ["exact", "in"],
        "create_at": ["gte", "lte"],
        "status": ["exact", "in"],
        "state": ["exact", "in"],
        "failed_days": ["exact", "lte", "gte"],
    }
    ordering_fields = ["create_at", "failed_days"]
    # 鉴权类
    action_permission_map = {("list",): [DBReportPermission()]}

    def filter_queryset(self, queryset):
        # 先调用父类的过滤逻辑，应用 filter_backends 中配置的过滤器
        queryset = super().filter_queryset(queryset)
        # 全局过滤排除掉特定业务
        exclude_bk_biz_ids = SystemSettings.get_setting_value(SystemSettingsEnum.DB_REPORT_EXCLUDE_BIZS, default=[])
        return queryset.exclude(bk_biz_id__in=exclude_bk_biz_ids)

    @staticmethod
    def _to_aware_datetime(value):
        """URL 上的时间是本地时间字符串，补齐时区后再查询，与 django-filter 的解析口径保持一致"""
        parsed = parse_datetime(value)
        if parsed is None:
            return value
        if timezone.is_naive(parsed):
            parsed = timezone.make_aware(parsed, timezone.get_current_timezone())
        return parsed

    def _filter_time_range(self, queryset):
        """
        时间过滤：优先使用精确区间 create_at__gte/create_at__lte(演练报告等页面的日期选择器)，
        都没传时才回退到 time_range(同样没传则默认近24小时)，保证统计与列表的时间范围一致
        """
        create_at_gte = self.request.query_params.get("create_at__gte")
        create_at_lte = self.request.query_params.get("create_at__lte")
        if create_at_gte or create_at_lte:
            if create_at_gte:
                queryset = queryset.filter(create_at__gte=self._to_aware_datetime(create_at_gte))
            if create_at_lte:
                queryset = queryset.filter(create_at__lte=self._to_aware_datetime(create_at_lte))
            return queryset

        time_range = self.request.query_params.get("time_range", "")
        filter_instance = ReportListFilter(
            data=self.request.query_params,
            queryset=queryset,
            request=self.request,
        )
        return filter_instance.filter_time_range(queryset, "time_range", time_range)

    def _get_time_filtered_queryset(self):
        """
        获取经过时间范围、bk_biz_id 和 manage 过滤的查询集，不受其他搜索/过滤条件影响
        """
        queryset = self.get_queryset()

        # 应用时间过滤
        queryset = self._filter_time_range(queryset)

        # 应用 bk_biz_id 过滤
        bk_biz_id = self.request.query_params.get("bk_biz_id")
        if bk_biz_id:
            queryset = queryset.filter(bk_biz_id=bk_biz_id)

        # 应用 manage 过滤
        manage = self.request.query_params.get("manage")
        if manage:
            username = self.request.user.username
            # 从请求路径中获取 db_type
            db_type = self.request.path.strip("/").split("/")[1]
            manage_bizs, assist_bizs = DBAdministrator.get_manage_bizs(db_type, username)
            # 待我处理
            if manage == "todo":
                queryset = queryset.filter(bk_biz_id__in=manage_bizs)
            # 待我协助
            elif manage == "assist":
                queryset = queryset.filter(bk_biz_id__in=assist_bizs)

        # 全局过滤排除掉特定业务
        exclude_bk_biz_ids = SystemSettings.get_setting_value(SystemSettingsEnum.DB_REPORT_EXCLUDE_BIZS, default=[])
        if exclude_bk_biz_ids:
            queryset = queryset.exclude(bk_biz_id__in=exclude_bk_biz_ids)

        return queryset

    def summary_state_count(self):
        """
        统计各状态的数量，受 time_range、manage 和 bk_biz_id(可观测页面) 影响，不受其他过滤参数(state等)影响
        """
        # 应用 time_range、manage、bk_biz_id 过滤和业务排除，不应用其他过滤条件
        queryset = self._get_time_filtered_queryset()

        # 这里使用order_by()清除排序字段，否则会加到group_by中，影响聚合逻辑
        state_count_info = queryset.order_by().values("state").annotate(count=Count("state"))
        state_map = {state: 0 for state in ReportStateType.get_values()}
        state_map.update({info["state"]: info["count"] for info in state_count_info})
        return state_map

    def get_total_count(self):
        """
        获取全量数据的总记录数，为 state_count 的总和
        """
        return self._get_time_filtered_queryset().count()

    def get_total_abnormal_count(self):
        """
        获取状态为异常或预警的总数，为 state_count 中异常+预警的总和
        """
        return (
            self._get_time_filtered_queryset()
            .filter(state__in=[ReportStateType.ABNORMAL, ReportStateType.WARNING])
            .count()
        )

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        response.data["name"] = self.report_name or ReportType.get_choice_label(self.report_type)
        response.data["title"] = self.report_title
        response.data["state_count"] = self.summary_state_count()
        response.data["total_count"] = self.get_total_count()
        response.data["total_abnormal_count"] = self.get_total_abnormal_count()
        return response


class BaseDrillReportViewSet(ReportBaseViewSet):
    filter_backends = [DrillReportFilterBackend, OrderingFilter]
    # 过滤、排序字段下放到字段声明
    filter_fields = {"bk_biz_id": ["exact"], "state": ["exact", "in"]}
    ordering_fields = []

    def list(self, request, *args, **kwargs):
        response = super().list(request, *args, **kwargs)
        return response


class ReportCommonViewSet(viewsets.SystemViewSet):
    """巡检通用接口视图"""

    default_permission_class = []

    @common_swagger_auto_schema(
        operation_summary=_("获取巡检报告总览"),
        query_serializer=GetReportOverviewSerializer(),
        responses={status.HTTP_200_OK: GetReportOverviewSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=False, serializer_class=GetReportOverviewSerializer)
    def get_report_overview(self, request, *args, **kwargs):
        data = self.params_validate(self.get_serializer_class())
        report_maps = report_kind_register_map[data["kind"]]
        # 获取报告类型与db组件映射
        report_types = defaultdict(list)
        for db_type, report_cls_list in report_maps.items():
            for cls in report_cls_list:
                report_types[db_type].append(cls.report_type)
            # 排序以固定前端展示顺序
            report_types[db_type].sort()
        return Response(report_types)

    @common_swagger_auto_schema(
        operation_summary=_("获取巡检报告代办数量"),
        responses={status.HTTP_200_OK: GetReportCountSerializer()},
        tags=[SWAGGER_TAG],
    )
    @action(methods=["GET"], detail=False, serializer_class=GetReportCountSerializer)
    def get_report_count(self, request, *args, **kwargs):
        username = request.user.username
        # cache_key = REPORT_COUNT_CACHE_KEY.format(user=username)
        # 获取 time_range 参数
        time_range = request.query_params.get("time_range", "")
        bk_biz_id = request.query_params.get("bk_biz_id")
        # 有缓存优先返回缓存，数量精确性要求性不高
        # report_count_cache = cache.get(cache_key)
        # if report_count_cache:
        #     return Response(report_count_cache)

        report_count_map: Dict[str, Dict[str, Dict]] = defaultdict(lambda: defaultdict(dict))
        for db_type, report_classes in db_report_maps.items():
            # 获取用户的管理业务和协助业务
            manage_bizs, assist_bizs = DBAdministrator.get_manage_bizs(db_type, username)
            for cls in report_classes:
                # 基础过滤：状态为异常或预警（与列表页面统计逻辑一致）
                queryset = cls.queryset.filter(state__in=[ReportStateType.ABNORMAL, ReportStateType.WARNING])
                # 应用 time_range 过滤
                if time_range:
                    filter_instance = ReportListFilter(
                        data=request.query_params,
                        queryset=queryset,
                        request=request,
                    )
                    queryset = filter_instance.filter_time_range(queryset, "time_range", time_range)
                if bk_biz_id:
                    queryset = queryset.filter(bk_biz_id=bk_biz_id)
                report_count_map[db_type][cls.report_type].update(
                    manage_count=queryset.filter(bk_biz_id__in=manage_bizs).count(),
                    assist_count=queryset.filter(bk_biz_id__in=assist_bizs).count(),
                )

        # 默认可以做1h的缓存
        # cache.set(cache_key, report_count_map, 60 * 10)
        return Response(report_count_map)
