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

        migration = import_module("backend.db_report.migrations.0058_kafka_disk_growth_report").Migration
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
