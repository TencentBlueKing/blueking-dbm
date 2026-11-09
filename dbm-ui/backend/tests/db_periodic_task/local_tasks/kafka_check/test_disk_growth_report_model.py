# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed on the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from datetime import date
from importlib import import_module

import pytest
from django.db import IntegrityError, transaction
from django.test import TestCase

from backend.db_report.models import KafkaDiskGrowthReport

SLOT_FIELDS = ["domain", "ip", "mount_point", "check_day", "run_kind"]


def row_kwargs(**overrides):
    kwargs = dict(
        bk_biz_id=1,
        bk_cloud_id=0,
        state="warning",
        cluster_type="kafka",
        msg="",
        domain="a.test.db",
        app="test",
        dba=[],
        failed_days=1,
        ip="127.0.0.1",
        mount_point="/data",
        check_day=date(2026, 11, 4),
        run_kind="morning",
        rule="continuous_new_high",
    )
    kwargs.update(overrides)
    return kwargs


class TestSlotUniquenessStructure:
    def test_model_declares_unique_constraint(self):
        constraints = [c for c in KafkaDiskGrowthReport._meta.constraints if getattr(c, "fields", None)]
        assert [list(c.fields) for c in constraints] == [SLOT_FIELDS]

    def test_migration_creates_the_same_constraint(self):
        from importlib import import_module

        migration = import_module("backend.db_report.migrations.0059_kafka_disk_growth_report").Migration
        create = [op for op in migration.operations if op.name == "KafkaDiskGrowthReport"][0]
        constraints = create.options["constraints"]
        assert [list(c.fields) for c in constraints] == [SLOT_FIELDS]
        assert constraints[0].name == KafkaDiskGrowthReport._meta.constraints[0].name


class TestSlotUniquenessDatabase(TestCase):
    # KafkaDiskGrowthReport 由 ReportRouter 路由到 report_db，必须声明这个库才会在事务里回滚
    databases = {"default", "report_db"}

    def test_database_rejects_duplicate_slot(self):
        KafkaDiskGrowthReport.objects.create(**row_kwargs())
        with self.assertRaises(IntegrityError), transaction.atomic(using="report_db"):
            KafkaDiskGrowthReport.objects.create(**row_kwargs())

    def test_different_slot_is_allowed(self):
        for other in (
            {"run_kind": "afternoon"},
            {"mount_point": "/data1"},
            {"ip": "127.0.0.2"},
            {"check_day": date(2026, 11, 3)},
        ):
            with self.subTest(other=other):
                KafkaDiskGrowthReport.objects.all().delete()
                KafkaDiskGrowthReport.objects.create(**row_kwargs())
                KafkaDiskGrowthReport.objects.create(**row_kwargs(**other))
                self.assertEqual(KafkaDiskGrowthReport.objects.count(), 2)

    def test_update_or_create_twice_keeps_one_row(self):
        lookup = {k: row_kwargs()[k] for k in SLOT_FIELDS}
        defaults = {k: v for k, v in row_kwargs().items() if k not in SLOT_FIELDS}
        for peak in (60.0, 61.0):
            KafkaDiskGrowthReport.objects.update_or_create(**lookup, defaults={**defaults, "peak": peak})
        self.assertEqual(KafkaDiskGrowthReport.objects.count(), 1)
        self.assertEqual(KafkaDiskGrowthReport.objects.get().peak, 61.0)


@pytest.mark.usefixtures("check_mod")  # 导入 local_tasks 会注册周期任务，走 conftest 里的惰性导入
class TestPreviousFailedDays(TestCase):
    databases = {"default", "report_db"}
    CHECK_DAY = date(2026, 11, 5)

    def previous(self, domains=("a.test.db",)):
        module = import_module("backend.db_periodic_task.local_tasks.kafka_check.kafka_disk_growth_check")
        return module._previous_failed_days(list(domains), self.CHECK_DAY)

    def create(self, **overrides):
        return KafkaDiskGrowthReport.objects.create(**row_kwargs(**overrides))

    def test_only_previous_day_counts(self):
        self.create(check_day=date(2026, 11, 4), failed_days=2)
        self.create(check_day=date(2026, 11, 3), mount_point="/data1", failed_days=5)  # 隔了一天，不连续
        self.create(check_day=self.CHECK_DAY, mount_point="/data2", failed_days=9)  # 同一天不算前一天
        assert self.previous() == {("a.test.db", "127.0.0.1", "/data"): 2}

    def test_same_day_morning_and_afternoon_takes_the_later_row(self):
        self.create(check_day=date(2026, 11, 4), run_kind="morning", failed_days=2)
        self.create(check_day=date(2026, 11, 4), run_kind="afternoon", failed_days=3)
        assert self.previous() == {("a.test.db", "127.0.0.1", "/data"): 3}

    def test_only_requested_domains(self):
        self.create(check_day=date(2026, 11, 4), domain="a.test.db")
        self.create(check_day=date(2026, 11, 4), domain="b.test.db")
        assert list(self.previous(("a.test.db",))) == [("a.test.db", "127.0.0.1", "/data")]

    def test_no_history(self):
        assert self.previous() == {}

    def test_single_query(self):
        for index in range(5):
            self.create(check_day=date(2026, 11, 4), mount_point=f"/data{index}")
        with self.assertNumQueries(1, using="report_db"):
            self.previous()
