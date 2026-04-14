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
from datetime import timedelta
from unittest.mock import MagicMock

import pytest
from django.utils import timezone

pytestmark = pytest.mark.django_db

"""
Tests for report_op.py — RedisBackupClusterReport and RedisBackupCheckBatchOps.

Source-module imports are done inside test methods to avoid triggering
the ``local_tasks/__init__.py`` import chain.
"""


def _report_cls():
    from backend.db_periodic_task.local_tasks.redis_backup.report_op import RedisBackupClusterReport

    return RedisBackupClusterReport


def _batch_cls():
    from backend.db_periodic_task.local_tasks.redis_backup.report_op import RedisBackupCheckBatchOps

    return RedisBackupCheckBatchOps


def _report_model():
    from backend.db_report.models import RedisBackupCheckReport

    return RedisBackupCheckReport


def _state():
    from backend.db_report.enums import ReportStateType

    return ReportStateType


def _make_report(subtype="full_backup"):
    cluster = MagicMock()
    cluster.bk_biz_id = 3
    cluster.bk_cloud_id = 0
    cluster.immute_domain = "test.example.db"
    cluster.cluster_type = "TwemproxyTendisSSDInstance"
    return _report_cls()(cluster, subtype)


# ---------------------------------------------------------------------------
# RedisBackupClusterReport
# ---------------------------------------------------------------------------
def test_skip_record_returns_single_normal_row():
    report = _make_report()
    rows = report.make_skip_record("skipped: test")
    assert len(rows) == 1
    assert rows[0].instance == "all"
    assert rows[0].status is True
    assert rows[0].state == _state().NORMAL.value
    assert "skipped" in rows[0].msg


def test_error_record_returns_single_abnormal_row():
    report = _make_report()
    rows = report.make_error_record("something broke")
    assert len(rows) == 1
    assert rows[0].instance == "all"
    assert rows[0].status is False
    assert rows[0].state == _state().ABNORMAL.value


def test_make_records_all_normal_summary():
    ST = _state()
    report = _make_report()
    report.append(ST.NORMAL.value, "3.3.3.1:30000", "ok")
    report.append(ST.NORMAL.value, "3.3.3.1:30001", "ok")
    rows = report.make_records()
    assert len(rows) == 1
    assert rows[0].instance == "all"
    assert rows[0].state == ST.NORMAL.value
    assert "2 instances checked" in rows[0].msg


def test_make_records_mixed_states_per_ip():
    ST = _state()
    report = _make_report()
    report.append(ST.NORMAL.value, "3.3.3.1:30000", "ok")
    report.append(ST.ABNORMAL.value, "3.3.3.1:30001", "failed")
    rows = report.make_records()
    assert len(rows) >= 1
    assert rows[0].state == ST.ABNORMAL.value


def test_make_records_zero_records_abnormal():
    ST = _state()
    report = _make_report()
    rows = report.make_records()
    assert len(rows) == 1
    assert rows[0].state == ST.ABNORMAL.value
    assert "no instance to check" in rows[0].msg


def test_make_records_worst_state_first():
    ST = _state()
    report = _make_report()
    report.append(ST.NORMAL.value, "3.3.3.1:30000", "ok")
    report.append(ST.WARNING.value, "3.3.3.2:30000", "warn")
    report.append(ST.ABNORMAL.value, "3.3.3.3:30000", "fail")
    rows = report.make_records()
    assert rows[0].state == ST.ABNORMAL.value


# ---------------------------------------------------------------------------
# RedisBackupCheckBatchOps
# ---------------------------------------------------------------------------
def test_batch_ops_continuous_key_format():
    row = MagicMock()
    row.cluster = "test.db"
    row.instance = "3.3.3.1"
    row.state = "abnormal"
    assert _batch_cls()._continuous_key(row) == "test.db:3.3.3.1:abnormal"


def test_batch_ops_failed_days_increments():
    Model = _report_model()
    ST = _state()
    Model.objects.filter(cluster="faildays.test.db", subtype="full_backup").delete()

    local_now = timezone.localtime()
    yesterday_noon = local_now.replace(hour=12, minute=0, second=0, microsecond=0) - timedelta(days=1)
    obj = Model.objects.create(
        subtype="full_backup",
        bk_biz_id=3,
        bk_cloud_id=0,
        cluster="faildays.test.db",
        cluster_type="TwemproxyTendisSSDInstance",
        instance="3.3.3.1",
        status=False,
        state=ST.ABNORMAL.value,
        msg="old failure",
        failed_days=5,
    )
    Model.objects.filter(pk=obj.pk).update(create_at=yesterday_noon)

    ops = _batch_cls()("full_backup")
    row = Model(
        subtype="full_backup",
        bk_biz_id=3,
        bk_cloud_id=0,
        cluster="faildays.test.db",
        cluster_type="TwemproxyTendisSSDInstance",
        instance="3.3.3.1",
        status=False,
        state=ST.ABNORMAL.value,
        msg="new failure",
        failed_days=0,
    )
    ops.append(row)
    ops.bulk_create()

    created = Model.objects.filter(cluster="faildays.test.db", msg="new failure").first()
    assert created is not None
    assert created.failed_days == 6

    Model.objects.filter(cluster="faildays.test.db", subtype="full_backup").delete()


def test_batch_ops_failed_days_resets_for_normal():
    Model = _report_model()
    ST = _state()
    Model.objects.filter(cluster="reset.test.db", subtype="full_backup").delete()

    ops = _batch_cls()("full_backup")
    row = Model(
        subtype="full_backup",
        bk_biz_id=3,
        bk_cloud_id=0,
        cluster="reset.test.db",
        cluster_type="TwemproxyTendisSSDInstance",
        instance="3.3.3.1",
        status=True,
        state=ST.NORMAL.value,
        msg="reset_ok",
        failed_days=0,
    )
    ops.append(row)
    ops.bulk_create()

    created = Model.objects.filter(cluster="reset.test.db", msg="reset_ok").first()
    assert created is not None
    assert created.failed_days == 0

    Model.objects.filter(cluster="reset.test.db", subtype="full_backup").delete()


def test_batch_ops_bulk_create_persists_and_clears():
    Model = _report_model()
    ST = _state()
    Model.objects.filter(cluster="persist.test.db", subtype="full_backup").delete()

    ops = _batch_cls()("full_backup")
    row = Model(
        subtype="full_backup",
        bk_biz_id=3,
        bk_cloud_id=0,
        cluster="persist.test.db",
        cluster_type="TwemproxyTendisSSDInstance",
        instance="3.3.3.1",
        status=True,
        state=ST.NORMAL.value,
        msg="persisted",
        failed_days=0,
    )
    ops.append(row)
    ops.bulk_create()
    assert ops.records == []
    assert Model.objects.filter(cluster="persist.test.db", msg="persisted").exists()

    Model.objects.filter(cluster="persist.test.db", subtype="full_backup").delete()


def test_batch_ops_delete_old_records():
    Model = _report_model()
    ST = _state()
    Model.objects.filter(cluster="delold.test.db", subtype="full_backup").delete()

    obj = Model.objects.create(
        subtype="full_backup",
        bk_biz_id=3,
        bk_cloud_id=0,
        cluster="delold.test.db",
        cluster_type="TwemproxyTendisSSDInstance",
        instance="3.3.3.1",
        status=True,
        state=ST.NORMAL.value,
        msg="old",
        failed_days=0,
    )
    Model.objects.filter(pk=obj.pk).update(create_at=timezone.now() - timedelta(days=400))
    ops = _batch_cls()("full_backup")
    count = ops.delete_old_records(360)
    assert count >= 1

    Model.objects.filter(cluster="delold.test.db", subtype="full_backup").delete()


def test_batch_ops_delete_today_records():
    Model = _report_model()
    ST = _state()
    Model.objects.filter(subtype="full_backup", cluster="deltoday.test.db").delete()

    Model.objects.create(
        subtype="full_backup",
        bk_biz_id=3,
        bk_cloud_id=0,
        cluster="deltoday.test.db",
        cluster_type="TwemproxyTendisSSDInstance",
        instance="3.3.3.1",
        status=True,
        state=ST.NORMAL.value,
        msg="today_del_test",
        failed_days=0,
    )

    before_count = Model.objects.filter(subtype="full_backup", cluster="deltoday.test.db").count()
    assert before_count == 1
    ops = _batch_cls()("full_backup")
    ops.delete_today_records()
    after_count = Model.objects.filter(subtype="full_backup", cluster="deltoday.test.db").count()
    assert after_count == 0

    Model.objects.filter(cluster="deltoday.test.db", subtype="full_backup").delete()
