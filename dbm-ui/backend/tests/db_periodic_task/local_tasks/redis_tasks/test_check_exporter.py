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

from backend.db_report.enums import ReportStateType


def test_check_cluster_retry_uses_fresh_cluster_report(monkeypatch, db):
    from backend.db_periodic_task.local_tasks.redis_tasks.check_exporter import CheckRedisUpMetricTask

    task = CheckRedisUpMetricTask()
    cluster = SimpleNamespace(
        bk_biz_id=1,
        bk_cloud_id=0,
        immute_domain="redis.test.db",
        id=100,
        cluster_type="RedisCluster",
    )
    report_day = 20260323
    call_count = {"times": 0}

    def mock_check_cluster_inner(cluster_report, _cluster):
        call_count["times"] += 1
        cluster_report.append(
            ReportStateType.ABNORMAL.value,
            "storage",
            "-",
            "redis_master_exporter_down:1.1.1.1:10000",
        )
        if call_count["times"] == 1:
            raise RuntimeError("transient metric query failure")
        return cluster_report.make_records()

    monkeypatch.setattr(task, "check_cluster_inner", mock_check_cluster_inner)
    monkeypatch.setattr("backend.db_periodic_task.local_tasks.redis_tasks.check_exporter.time.sleep", lambda *_: None)

    rows = task.check_cluster(cluster, report_day)

    detail_rows = [row for row in rows if row.shard != "all"]
    assert len(detail_rows) == 1
    assert detail_rows[0].msg == "redis_master_exporter_down:1.1.1.1:10000"
    assert ", abnormal: 1" in rows[0].msg
