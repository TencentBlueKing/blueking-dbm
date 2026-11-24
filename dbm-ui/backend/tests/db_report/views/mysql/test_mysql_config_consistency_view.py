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
import unittest
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from django.utils import timezone

from backend.configuration.constants import DBType
from backend.db_report.enums import MysqlConfigConsistencySubType, ReportType
from backend.db_report.filters import apply_min_time_range_filter
from backend.db_report.register import db_report_maps, register_all_reports
from backend.db_report.report_baseview import ReportBaseViewSet
from backend.db_report.views.mysql.mysql_config_consistency_view import (
    DEFAULT_WEEKLY_LOOKBACK_DAYS,
    MYSQL_CONFIG_CONSISTENCY_TITLE,
    TENDBCLUSTER_CONFIG_CONSISTENCY_TITLE,
    MysqlConfigConsistencyReportSerializer,
    MysqlConfigConsistencyReportViewSet,
)
from backend.db_report.views.tendbcluster.tendbcluster_config_consistency_view import (
    TendbClusterConfigConsistencyReportViewSet,
)


class TestMysqlConfigConsistencyViewConfig(unittest.TestCase):
    def test_report_registered_under_mysql_and_tendbcluster(self):
        register_all_reports()
        mysql_types = [cls.report_type for cls in db_report_maps[DBType.MySQL]]
        tc_types = [cls.report_type for cls in db_report_maps[DBType.TenDBCluster]]
        self.assertIn(ReportType.CONFIG_CONSISTENCY_CHECK, mysql_types)
        self.assertIn(ReportType.CONFIG_CONSISTENCY_CHECK, tc_types)

    def test_titles_distinguish_mysql_and_tendbcluster(self):
        mysql_cols = [col["name"] for col in MYSQL_CONFIG_CONSISTENCY_TITLE]
        tc_cols = [col["name"] for col in TENDBCLUSTER_CONFIG_CONSISTENCY_TITLE]
        self.assertNotIn("subtype_display", mysql_cols)
        self.assertIn("subtype_display", tc_cols)
        self.assertIn("diff_variables", mysql_cols)
        self.assertIn("diff_variables", tc_cols)
        self.assertEqual(
            TendbClusterConfigConsistencyReportViewSet.report_title, TENDBCLUSTER_CONFIG_CONSISTENCY_TITLE
        )

    def test_serializer_subtype_display(self):
        serializer = MysqlConfigConsistencyReportSerializer()
        spider_obj = SimpleNamespace(subtype=MysqlConfigConsistencySubType.SPIDER_CONFIG.value)
        shard_obj = SimpleNamespace(subtype=MysqlConfigConsistencySubType.STORAGE_SHARD.value)
        self.assertEqual(
            serializer.get_subtype_display(spider_obj),
            str(MysqlConfigConsistencySubType.get_choice_label(MysqlConfigConsistencySubType.SPIDER_CONFIG.value)),
        )
        self.assertEqual(
            serializer.get_subtype_display(shard_obj),
            str(MysqlConfigConsistencySubType.get_choice_label(MysqlConfigConsistencySubType.STORAGE_SHARD.value)),
        )

    def test_min_time_range_widens_default_1d_to_7d_and_preserves_longer_or_unlimited(self):
        now = timezone.now()
        with patch("backend.db_report.filters.timezone.now", return_value=now):
            # 前端默认 now -1d 自动放宽为 7 天
            qs_1d = MagicMock()
            apply_min_time_range_filter(qs_1d, "now -1d", min_days=DEFAULT_WEEKLY_LOOKBACK_DAYS)
            qs_1d.filter.assert_called_once_with(create_at__gte=now - timedelta(days=7))

            # 空 time_range 自动放宽为 7 天
            qs_empty = MagicMock()
            apply_min_time_range_filter(qs_empty, "", min_days=DEFAULT_WEEKLY_LOOKBACK_DAYS)
            qs_empty.filter.assert_called_once_with(create_at__gte=now - timedelta(days=7))

            # 更长区间 now -30d 保持 30 天
            qs_30d = MagicMock()
            apply_min_time_range_filter(qs_30d, "now -30d", min_days=DEFAULT_WEEKLY_LOOKBACK_DAYS)
            qs_30d.filter.assert_called_once_with(create_at__gte=now - timedelta(days=30))

            # 全量 now -0d 不加限制
            qs_all = MagicMock()
            res = apply_min_time_range_filter(qs_all, "now -0d", min_days=DEFAULT_WEEKLY_LOOKBACK_DAYS)
            self.assertIs(res, qs_all)
            qs_all.filter.assert_not_called()

            # 日频视图 min_days=None 保持 24h
            qs_daily = MagicMock()
            apply_min_time_range_filter(qs_daily, "now -1d", min_days=None)
            qs_daily.filter.assert_called_once_with(create_at__gte=now - timedelta(days=1))

    def test_viewset_and_daily_base_time_range_isolation(self):
        now = timezone.now()
        view = MysqlConfigConsistencyReportViewSet()
        view.request = SimpleNamespace(query_params={"time_range": "now -1d"})
        fake_qs = MagicMock()
        fake_qs.filter.return_value = fake_qs

        with patch("backend.db_report.filters.timezone.now", return_value=now):
            view._filter_time_range(fake_qs)
        fake_qs.filter.assert_called_once_with(create_at__gte=now - timedelta(days=7))

        # 精确 create_at__gte 不被 7 天兜底改写
        view_exact = MysqlConfigConsistencyReportViewSet()
        view_exact.request = SimpleNamespace(query_params={"create_at__gte": "2026-11-23 00:00:00"})
        qs_exact = MagicMock()
        qs_exact.filter.return_value = qs_exact
        view_exact._filter_time_range(qs_exact)
        called_gte = qs_exact.filter.call_args.kwargs["create_at__gte"]
        self.assertEqual(called_gte.year, 2026)
        self.assertEqual(called_gte.day, 23)

        # 基类默认不启用 min_time_range_days，不影响其他日频报表
        self.assertIsNone(ReportBaseViewSet.min_time_range_days)
        self.assertEqual(MysqlConfigConsistencyReportViewSet.min_time_range_days, 7)
        self.assertEqual(TendbClusterConfigConsistencyReportViewSet.min_time_range_days, 7)
