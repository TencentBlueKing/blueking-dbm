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
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.django_db


def _mock_cluster_qs(cluster_ids):
    qs = MagicMock()
    qs.prefetch_related.return_value = [MagicMock(id=cid, tags=MagicMock(all=lambda: [])) for cid in cluster_ids]
    return qs


class TestRedisLocalTaskScoped:
    def test_delete_today_record_for_clusters_empty(self, redis_report_op_module):
        ops = redis_report_op_module.RedisCheckReportBatchOps("exporter", 20260101)
        assert ops.delete_today_record_for_clusters([]) == 0

    def test_exporter_scoped_skips_global_delete(self, check_exporter):
        task = check_exporter.CheckRedisUpMetricTask()
        record_ops = MagicMock()
        with patch.object(check_exporter, "RedisCheckReportBatchOps", return_value=record_ops), patch.object(
            check_exporter.Cluster.objects, "filter", return_value=_mock_cluster_qs([21])
        ), patch.object(task, "check_cluster", return_value=[]):
            task.start(cluster_domain="redis.example.db", batch_size=10)

        record_ops.delete_today_record_for_clusters.assert_called_once_with([21])
        record_ops.delete_old_record.assert_not_called()
        record_ops.delete_today_record.assert_not_called()

    def test_exporter_full_scope_uses_global_delete(self, check_exporter):
        task = check_exporter.CheckRedisUpMetricTask()
        record_ops = MagicMock()
        with patch.object(check_exporter, "RedisCheckReportBatchOps", return_value=record_ops), patch.object(
            check_exporter.Cluster.objects, "filter", return_value=_mock_cluster_qs([31])
        ), patch.object(task, "check_cluster", return_value=[]):
            task.start(batch_size=10)

        record_ops.delete_old_record.assert_called_once_with(360)
        record_ops.delete_today_record.assert_called_once()
        record_ops.delete_today_record_for_clusters.assert_not_called()
