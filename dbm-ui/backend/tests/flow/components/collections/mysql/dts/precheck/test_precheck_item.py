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
from unittest import TestCase
from unittest.mock import MagicMock, patch
from uuid import uuid4

from backend.flow.plugins.components.collections.mysql.dts.precheck.precheck_item import MysqlDtsPrecheckItemService
from backend.flow.utils.mysql.dts.precheck.base import _REGISTRY, CheckItem, CheckLevel, CheckResult, register
from backend.flow.utils.mysql.dts.precheck.collector import PrecheckCollectError
from backend.flow.utils.mysql.dts.precheck.summary import SKIPPED_NO_FLOW, WRITTEN, collect_error_result

SERVICE_MOD = "backend.flow.plugins.components.collections.mysql.dts.precheck.precheck_item"


class FakeData:
    def __init__(self, kwargs):
        self.kwargs = kwargs

    def get_one_of_inputs(self, key):
        if key == "kwargs":
            return self.kwargs
        return {}


def _context():
    endpoint = SimpleNamespace(cluster_id=1, address="127.0.0.1:3306")
    side = SimpleNamespace(endpoint=endpoint)
    return SimpleNamespace(source=side, target=side)


def _service() -> MysqlDtsPrecheckItemService:
    service = MysqlDtsPrecheckItemService()
    service._runtime_attrs = {"root_pipeline_id": "root-1"}
    service.log_info = MagicMock()
    service.log_warning = MagicMock()
    service.log_error = MagicMock()
    return service


class PrecheckItemSummaryTest(TestCase):
    def test_failure_is_still_written_before_the_node_fails(self):
        item = CheckItem(code="version", name="版本检查", run=lambda _ctx: [])
        failed = CheckResult(ok=False, code="version.dest_ge_source", message="目标版本更低")
        service = _service()
        data = FakeData({"item_code": "version", "source_cluster_domain": "src", "target_cluster_domain": "dst"})

        with (
            patch(f"{SERVICE_MOD}.get_item", return_value=item),
            patch(f"{SERVICE_MOD}.build_context", return_value=_context()),
            patch(f"{SERVICE_MOD}.run_item", return_value=[failed]),
            patch(f"{SERVICE_MOD}.write_precheck_summary", return_value=WRITTEN) as write_summary,
        ):
            self.assertFalse(service._execute(data, None))

        write_summary.assert_called_once_with("root-1", item, [failed], "src", "dst", None)

    def test_warning_passes_the_node_and_is_written(self):
        item = CheckItem(code="warnings", name="警告项检查", run=lambda _ctx: [])
        warned = CheckResult(ok=False, code="warnings.sql_mode", message="sql_mode 不一致", level=CheckLevel.WARN)
        service = _service()
        data = FakeData({"item_code": "warnings", "source_cluster_domain": "src", "target_cluster_domain": "dst"})

        with (
            patch(f"{SERVICE_MOD}.get_item", return_value=item),
            patch(f"{SERVICE_MOD}.build_context", return_value=_context()),
            patch(f"{SERVICE_MOD}.run_item", return_value=[warned]),
            patch(f"{SERVICE_MOD}.write_precheck_summary", return_value=WRITTEN) as write_summary,
        ):
            self.assertTrue(service._execute(data, None))

        write_summary.assert_called_once_with("root-1", item, [warned], "src", "dst", None)

    def test_context_collect_error_writes_one_failure_row(self):
        item = CheckItem(code="binlog", name="binlog检查", run=lambda _ctx: [])
        service = _service()
        data = FakeData({"item_code": "binlog"})

        with (
            patch(f"{SERVICE_MOD}.get_item", return_value=item),
            patch(f"{SERVICE_MOD}.build_context", side_effect=PrecheckCollectError("连不上")),
            patch(f"{SERVICE_MOD}.run_item") as run_item,
            patch(f"{SERVICE_MOD}.write_precheck_summary", return_value=WRITTEN) as write_summary,
        ):
            self.assertFalse(service._execute(data, None))

        run_item.assert_not_called()
        write_summary.assert_called_once_with(
            "root-1",
            item,
            [collect_error_result(item, "连不上")],
            "",
            "",
            None,
        )

    def test_missing_ticket_flow_does_not_fail_a_passed_check(self):
        item = CheckItem(code="version", name="版本检查", run=lambda _ctx: [])
        passed = CheckResult(ok=True, code="version.in_range", message="版本在范围内")
        service = _service()
        data = FakeData({"item_code": "version", "source_cluster_domain": "src", "target_cluster_domain": "dst"})

        with (
            patch(f"{SERVICE_MOD}.get_item", return_value=item),
            patch(f"{SERVICE_MOD}.build_context", return_value=_context()),
            patch(f"{SERVICE_MOD}.run_item", return_value=[passed]),
            patch(f"{SERVICE_MOD}.write_precheck_summary", return_value=SKIPPED_NO_FLOW),
        ):
            self.assertTrue(service._execute(data, None))

        service.log_info.assert_any_call("当前流程[root-1]未关联单据Flow记录，跳过写入执行摘要")

    def test_newly_registered_item_is_summarized_without_its_own_writer(self):
        code = f"test_{uuid4().hex}"

        @register(code, "新检查")
        def run(_ctx):
            return [CheckResult(ok=True, code=f"{code}.ok", message="通过了")]

        try:
            item = CheckItem(code=code, name="新检查", run=run)
            produced = run(None)
            service = _service()
            data = FakeData({"item_code": code, "source_cluster_domain": "src", "target_cluster_domain": "dst"})
            with (
                patch(f"{SERVICE_MOD}.get_item", return_value=item),
                patch(f"{SERVICE_MOD}.build_context", return_value=_context()),
                patch(f"{SERVICE_MOD}.run_item", return_value=produced),
                patch(f"{SERVICE_MOD}.write_precheck_summary", return_value=WRITTEN) as write_summary,
            ):
                self.assertTrue(service._execute(data, None))
            write_summary.assert_called_once_with("root-1", item, produced, "src", "dst", None)
        finally:
            _REGISTRY.pop(code, None)
