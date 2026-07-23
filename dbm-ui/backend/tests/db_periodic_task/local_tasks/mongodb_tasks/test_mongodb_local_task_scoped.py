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
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.django_db


class TestRecordBatchOpsScopedDelete:
    def test_delete_today_record_for_clusters_empty(self, report_op_module):
        ops = report_op_module.RecordBatchOps("full_backup", 20260716)
        assert ops.delete_today_record_for_clusters([]) == 0

    def test_delete_today_record_for_clusters_filters(self, report_op_module):
        ops = report_op_module.RecordBatchOps("full_backup", 20260716)
        qs = MagicMock()
        qs.delete.return_value = (3, {})
        with patch.object(report_op_module.MongodbBackupCheckReport.objects, "filter", return_value=qs) as flt:
            assert ops.delete_today_record_for_clusters([1, 2]) == 3
        flt.assert_called_once_with(report_day=20260716, subtype="full_backup", cluster_id__in=[1, 2])


def _mock_cluster_qs(ids):
    clusters = [SimpleNamespace(id=i) for i in ids]
    qs = MagicMock()
    qs.__iter__ = lambda self: iter(clusters)
    return qs


class TestCheckTaskScopedStart:
    def test_backup_scoped_skips_global_delete(self, check_backup_module):
        task = check_backup_module.CheckMongoBackupRecordTask()
        record_ops = MagicMock()
        record_ops.delete_today_record_for_clusters.return_value = 1
        with patch.object(check_backup_module, "RecordBatchOps", return_value=record_ops), patch.object(
            check_backup_module.Cluster.objects, "filter", return_value=_mock_cluster_qs([11])
        ), patch.object(check_backup_module.MongoRepository, "fetch_one_cluster") as fetch, patch.object(
            task, "check_cluster", return_value=[SimpleNamespace(state="normal")]
        ):
            fetch.return_value = SimpleNamespace()
            task.start(report_day=20260716, cluster_domain="mongo.example.db", batch_size=20)

        record_ops.delete_old_record.assert_not_called()
        record_ops.delete_today_record.assert_not_called()
        record_ops.delete_today_record_for_clusters.assert_called_once_with([11])

    def test_backup_full_uses_global_delete(self, check_backup_module):
        task = check_backup_module.CheckMongoBackupRecordTask()
        record_ops = MagicMock()
        record_ops.delete_old_record.return_value = 0
        record_ops.delete_today_record.return_value = 0
        with patch.object(check_backup_module, "RecordBatchOps", return_value=record_ops), patch.object(
            check_backup_module.Cluster.objects, "filter", return_value=_mock_cluster_qs([])
        ):
            task.start(report_day=20260716, batch_size=20)

        record_ops.delete_old_record.assert_called_once_with(360)
        record_ops.delete_today_record.assert_called_once()
        record_ops.delete_today_record_for_clusters.assert_not_called()

    def test_backup_mutual_exclusive_scope(self, check_backup_module):
        with pytest.raises(ValueError, match="mutually exclusive"):
            check_backup_module.CheckMongoBackupRecordTask().start(cluster_domain="mongo.example.db", bk_biz_id=1)

    def test_metric_scoped_skips_global_delete(self, check_exporter_module):
        task = check_exporter_module.CheckMongodbUpMetricTask()
        record_ops = MagicMock()
        record_ops.delete_today_record_for_clusters.return_value = 0
        with patch.object(check_exporter_module, "RecordBatchOps", return_value=record_ops), patch.object(
            check_exporter_module.Cluster.objects, "filter", return_value=_mock_cluster_qs([21])
        ), patch.object(check_exporter_module.MongoRepository, "fetch_one_cluster") as fetch, patch.object(
            task, "check_cluster", return_value=[]
        ):
            fetch.return_value = SimpleNamespace()
            task.start(report_day=20260716, bk_biz_id=100, batch_size=20)

        record_ops.delete_old_record.assert_not_called()
        record_ops.delete_today_record.assert_not_called()
        record_ops.delete_today_record_for_clusters.assert_called_once_with([21])

    def test_affinity_scoped_skips_global_delete(self, check_affinity_module):
        task = check_affinity_module.CheckMongodbAffinityTask()
        record_ops = MagicMock()
        record_ops.delete_today_record_for_clusters.return_value = 0
        with patch.object(check_affinity_module, "RecordBatchOps", return_value=record_ops), patch.object(
            check_affinity_module.Cluster.objects, "filter", return_value=_mock_cluster_qs([31])
        ), patch.object(check_affinity_module.MongoRepository, "fetch_one_cluster") as fetch, patch.object(
            task, "check_cluster", return_value=[]
        ):
            fetch.return_value = SimpleNamespace()
            task.start(report_day=20260716, cluster_domain="mongo.example.db", batch_size=20)

        record_ops.delete_old_record.assert_not_called()
        record_ops.delete_today_record.assert_not_called()
        record_ops.delete_today_record_for_clusters.assert_called_once_with([31])
