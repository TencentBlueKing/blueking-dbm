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

from contextlib import nullcontext
from unittest import TestCase
from unittest.mock import MagicMock, patch

from backend.flow.utils.mysql.dts.precheck.base import CheckItem, CheckLevel, CheckResult
from backend.flow.utils.mysql.dts.precheck.summary import (
    DETAIL_TABLE,
    MATRIX_TABLE,
    SKIPPED_EMPTY,
    SKIPPED_NO_FLOW,
    WRITTEN,
    item_status,
    write_precheck_summary,
)


def _item(code="version", name="版本检查") -> CheckItem:
    return CheckItem(code=code, name=name, run=lambda _ctx: [])


class ItemStatusTest(TestCase):
    def test_worst_result_wins(self):
        passed = CheckResult(ok=True, code="version.in_range", message="范围内")
        warned = CheckResult(ok=False, code="version.notice", message="提示", level=CheckLevel.WARN)
        failed = CheckResult(ok=False, code="version.dest_ge_source", message="目标更低")
        self.assertEqual(item_status([passed]), "通过")
        self.assertEqual(item_status([passed, warned]), "警告")
        self.assertEqual(item_status([warned, failed]), "失败")


class _SummaryBox:
    def __init__(self):
        self.summary = []
        self.save = MagicMock()


class WriteMatrixTest(TestCase):
    def setUp(self):
        self.box = _SummaryBox()
        flow_patch = patch("backend.flow.utils.mysql.dts.precheck.summary.Flow")
        summary_patch = patch("backend.flow.utils.mysql.dts.precheck.summary.FlowSummary")
        atomic_patch = patch("backend.flow.utils.mysql.dts.precheck.summary.transaction.atomic", lambda: nullcontext())
        self.flow_model = flow_patch.start()
        self.summary_model = summary_patch.start()
        self.atomic = atomic_patch.start()
        self.addCleanup(flow_patch.stop)
        self.addCleanup(summary_patch.stop)
        self.addCleanup(atomic_patch.stop)
        self.flow_model.objects.filter.return_value.exists.return_value = True
        self.flow_model.objects.get.return_value = MagicMock(id=7)
        self.summary_model.objects.select_for_update.return_value.get_or_create.return_value = (self.box, False)

    def _write(self, item, results, source="src.db", target="dst.db"):
        return write_precheck_summary("root-1", item, results, source, target, enabled_codes=["version", "binlog"])

    def _table(self, name):
        return next(table for table in self.box.summary if table["table_name"] == name)

    def test_missing_flow_skips(self):
        self.flow_model.objects.filter.return_value.exists.return_value = False
        outcome = self._write(_item(), [CheckResult(ok=True, code="version.in_range", message="")])
        self.assertEqual(outcome, SKIPPED_NO_FLOW)
        self.assertEqual(self.box.summary, [])

    def test_empty_results_do_not_write(self):
        self.assertEqual(self._write(_item(), []), SKIPPED_EMPTY)

    def test_one_row_per_task_and_one_column_per_major_item(self):
        version = _item("version", "版本检查")
        binlog = _item("binlog", "binlog参数检查")
        self._write(version, [CheckResult(ok=False, code="version.dest_ge_source", message="目标版本更低")])
        self._write(
            binlog,
            [CheckResult(ok=True, code="binlog.log_bin", message="已开启")],
            source="src.db",
            target="dst.db",
        )
        self._write(
            version,
            [CheckResult(ok=True, code="version.in_range", message="范围内")],
            source="other.db",
            target="dst2.db",
        )

        matrix = self._table(MATRIX_TABLE)
        title_ids = [title["id"] for title in matrix["titles"]]
        self.assertEqual(title_ids[:2], ["source_cluster", "target_cluster"])
        self.assertNotIn("task_key", title_ids)
        self.assertIn("version", title_ids)
        self.assertIn("binlog", title_ids)

        by_source = {row["source_cluster"]: row for row in matrix["values"]}
        self.assertEqual(by_source["src.db"]["target_cluster"], "dst.db")
        self.assertEqual(by_source["src.db"]["version"], "失败")
        self.assertEqual(by_source["src.db"]["binlog"], "通过")
        self.assertEqual(by_source["other.db"]["version"], "通过")
        self.assertNotIn("binlog", by_source["other.db"])

    def test_failure_detail_is_one_row_per_major_item_and_goes_away_when_passed(self):
        version = _item()
        failed = CheckResult(ok=False, code="version.dest_ge_source", message="目标版本更低")
        warned = CheckResult(ok=False, code="version.notice", message="小版本不同", level=CheckLevel.WARN)
        self._write(version, [failed, warned])

        detail = self._table(DETAIL_TABLE)
        self.assertEqual(len(detail["values"]), 1)
        self.assertEqual(detail["values"][0]["item_name"], "版本检查")
        self.assertEqual(detail["values"][0]["status"], "失败")
        self.assertEqual(detail["values"][0]["message"], "目标版本更低；小版本不同")
        self.assertNotIn("detail_key", [title["id"] for title in detail["titles"]])

        self.assertEqual(self._write(version, [CheckResult(ok=True, code="version.in_range", message="范围内")]), WRITTEN)
        self.assertFalse(any(table["table_name"] == DETAIL_TABLE for table in self.box.summary))
        self.assertEqual(self._table(MATRIX_TABLE)["values"][0]["version"], "通过")
