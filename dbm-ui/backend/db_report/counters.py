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

from django.db.models import Count, Q

from backend.configuration.constants import SystemSettingsEnum
from backend.configuration.models import DBAdministrator, SystemSettings
from backend.db_report.enums import ReportStateType
from backend.db_report.filters import ReportListFilter
from backend.db_report.register import db_report_maps

# 计入待办的巡检状态：异常 + 预警，与巡检列表页面的统计逻辑保持一致
TODO_REPORT_STATES = [ReportStateType.ABNORMAL, ReportStateType.WARNING]

# 巡检待办提醒使用的时间窗口，与前端巡检页面默认的“最近 24 小时”保持一致
TODO_REPORT_TIME_RANGE = "now -1d"


def _filter_time_range(queryset, time_range: str):
    """按 time_range 过滤创建时间，复用列表面板的时间解析口径；time_range 为空表示不限时间"""
    if not time_range:
        return queryset
    filter_instance = ReportListFilter(data={}, queryset=queryset)
    return filter_instance.filter_time_range(queryset, "time_range", time_range)


def calc_report_count(
    username: str, time_range: str = "", bk_biz_id: int = None
) -> Dict[str, Dict[str, Dict[str, int]]]:
    """按 组件类型 -> 巡检项 统计“待我处理/待我协助”的巡检数量

    get_report_count 接口与每日待办提醒任务共用该口径，避免两处统计结果不一致。
    口径说明：
    - 状态：异常 + 预警
    - 时间：基于 create_at，time_range 为空则不限时间
    - 业务：待我处理取 DBA 首位为用户本人的业务，待我协助取用户在其中但非首位的业务；
      同时排除 DB_REPORT_EXCLUDE_BIZS 中配置的业务，与列表页 filter_queryset 保持一致
    """
    # 与列表页 filter_queryset 保持一致：全局排除不需要展示的业务
    exclude_bk_biz_ids = SystemSettings.get_setting_value(SystemSettingsEnum.DB_REPORT_EXCLUDE_BIZS, default=[])
    report_count_map = defaultdict(lambda: defaultdict(dict))
    for db_type, report_classes in db_report_maps.items():
        manage_bizs, assist_bizs = DBAdministrator.get_manage_bizs(db_type, username)
        for report_cls in report_classes:
            queryset = report_cls.queryset.filter(state__in=TODO_REPORT_STATES)
            queryset = _filter_time_range(queryset, time_range)
            if bk_biz_id:
                queryset = queryset.filter(bk_biz_id=bk_biz_id)
            if exclude_bk_biz_ids:
                queryset = queryset.exclude(bk_biz_id__in=exclude_bk_biz_ids)
            # 一次聚合同时统计待我处理与待我协助，避免两次 count 查询
            counts = queryset.aggregate(
                manage_count=Count("pk", filter=Q(bk_biz_id__in=manage_bizs)),
                assist_count=Count("pk", filter=Q(bk_biz_id__in=assist_bizs)),
            )
            report_count_map[db_type][report_cls.report_type].update(counts)

    return {db_type: dict(report_types) for db_type, report_types in report_count_map.items()}
