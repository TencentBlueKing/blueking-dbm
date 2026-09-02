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

from django.db import transaction
from django.utils.encoding import force_str
from django.utils.translation import gettext as _

from backend.flow.utils.mysql.dts.precheck.base import (
    CheckItem,
    CheckLevel,
    CheckResult,
    all_items,
    collect_error_code,
)
from backend.ticket.models import Flow, FlowSummary

WRITTEN = "written"
SKIPPED_NO_FLOW = "skipped_no_flow"
SKIPPED_EMPTY = "skipped_empty"

MATRIX_TABLE = "dts_precheck_matrix"
DETAIL_TABLE = "dts_precheck_detail"
_TASK_KEY = "task_key"
_DETAIL_KEY = "detail_key"


def item_status(results: list[CheckResult]) -> str:
    """一个大项收成一个格子：有硬失败就是失败，否则有警告就是警告，否则通过。"""
    if any(not result.ok and result.level != CheckLevel.WARN for result in results):
        return _("失败")
    if any(not result.ok for result in results):
        return _("警告")
    return _("通过")


def collect_error_result(item: CheckItem, message: str) -> CheckResult:
    return CheckResult(
        ok=False,
        code=collect_error_code(item.code),
        message=message,
        level=CheckLevel.FAIL,
    )


def task_key(source_cluster: str, target_cluster: str, pair_key: str = "") -> str:
    key = f"{source_cluster}\x1f{target_cluster}"
    if pair_key:
        return f"{key}\x1f{pair_key}"
    return key


def write_precheck_summary(
    root_id: str,
    item: CheckItem,
    results: list[CheckResult],
    source_cluster: str,
    target_cluster: str,
    enabled_codes: list[str] | None = None,
    pair_key: str = "",
    scope_label: str = "",
) -> str:
    """一对源/目标写一行。这一列只更新当前大项，其它大项的格子保持不变。

    未通过的大项另写一张明细表，一行只放这一对集群的这一个大项。通过之后删掉对应明细。
    新检查项只要完成登记并放进检查阶段，列会在下次写入时出现，不用改本文件。
    """
    if not results:
        return SKIPPED_EMPTY
    if not root_id or not Flow.objects.filter(flow_obj_id=root_id).exists():
        return SKIPPED_NO_FLOW

    with transaction.atomic():
        flow_id = Flow.objects.get(flow_obj_id=root_id).id
        summary, __ = FlowSummary.objects.select_for_update().get_or_create(flow_id=flow_id)
        output = list(summary.summary or [])
        _write_matrix(output, item, results, source_cluster, target_cluster, enabled_codes, pair_key, scope_label)
        _write_detail(output, item, results, source_cluster, target_cluster, pair_key, scope_label)
        summary.summary = output
        summary.save(update_fields=["summary"])
    return WRITTEN


def _column_items(enabled_codes: list[str] | None, current_code: str) -> list[CheckItem]:
    # 延迟导入，避免摘要模块和子流程互相引用。登记模块要先加载，列名才找得到。
    import backend.flow.utils.mysql.dts.precheck.items  # noqa: F401
    from backend.flow.engine.bamboo.scene.mysql.dts.precheck.mysql_dts_precheck_subflow import CHECK_STAGES

    by_code = {check.code: check for check in all_items()}
    staged = [code for stage in CHECK_STAGES for code in stage]
    codes = [code for code in staged if code in by_code]
    codes.extend(code for code in by_code if code not in codes)
    if enabled_codes is not None:
        enabled = set(enabled_codes)
        enabled.add(current_code)
        codes = [code for code in codes if code in enabled]
    if current_code not in codes and current_code in by_code:
        codes.append(current_code)
    return [by_code[code] for code in codes]


def _scope_title() -> dict:
    return {"id": "scope_label", "display_name": force_str(_("库表范围")), "type": "text"}


def _compose_matrix_titles(
    columns: list[CheckItem], item: CheckItem, scope_needed: bool, previous: list[dict]
) -> list[dict]:
    titles = [
        {"id": "source_cluster", "display_name": force_str(_("源集群")), "type": "text"},
        {"id": "target_cluster", "display_name": force_str(_("目标集群")), "type": "text"},
    ]
    if scope_needed:
        titles.append(_scope_title())
    titles.extend({"id": column.code, "display_name": force_str(column.name), "type": "text"} for column in columns)
    known = {title["id"] for title in titles}
    if item.code not in known:
        titles.append({"id": item.code, "display_name": force_str(item.name), "type": "text"})
        known.add(item.code)
    for title in previous or []:
        if title.get("id") not in known and title.get("id") != _TASK_KEY:
            titles.append(title)
            known.add(title["id"])
    return titles


def _detail_titles(scope_needed: bool) -> list[dict]:
    titles = [
        {"id": "source_cluster", "display_name": force_str(_("源集群")), "type": "text"},
        {"id": "target_cluster", "display_name": force_str(_("目标集群")), "type": "text"},
    ]
    if scope_needed:
        titles.append(_scope_title())
    titles.extend(
        [
            {"id": "item_name", "display_name": force_str(_("检查项")), "type": "text"},
            {"id": "status", "display_name": force_str(_("结果")), "type": "text"},
            {"id": "message", "display_name": force_str(_("说明")), "type": "text"},
        ]
    )
    return titles


def _write_matrix(output, item, results, source_cluster, target_cluster, enabled_codes, pair_key, scope_label) -> None:
    columns = _column_items(enabled_codes, item.code)
    existing = _find_table(output, MATRIX_TABLE)
    previous_titles = list(existing["titles"]) if existing else []
    scope_needed = bool(scope_label) or any(row.get("scope_label") for row in (existing["values"] if existing else []))
    titles = _compose_matrix_titles(columns, item, scope_needed, previous_titles)
    _ensure_table(
        output,
        MATRIX_TABLE,
        force_str(_("DTS 预检查结果")),
        titles,
        _TASK_KEY,
    )
    table = _find_table(output, MATRIX_TABLE)
    key = task_key(source_cluster, target_cluster, pair_key)
    row = _find_row(table["values"], _TASK_KEY, key)
    payload = {
        _TASK_KEY: key,
        "source_cluster": source_cluster,
        "target_cluster": target_cluster,
        item.code: item_status(results),
    }
    if scope_label:
        payload["scope_label"] = scope_label
    row.update(payload)


def _write_detail(output, item, results, source_cluster, target_cluster, pair_key, scope_label) -> None:
    key = f"{task_key(source_cluster, target_cluster, pair_key)}\x1f{item.code}"
    table = _find_table(output, DETAIL_TABLE)
    failed = [result for result in results if not result.ok]
    if not failed:
        if table is not None:
            table["values"] = [row for row in table["values"] if row.get(_DETAIL_KEY) != key]
            if not table["values"]:
                output.remove(table)
        return

    scope_needed = bool(scope_label)
    if table is None:
        table = _ensure_table(
            output,
            DETAIL_TABLE,
            force_str(_("未通过明细")),
            _detail_titles(scope_needed),
            _DETAIL_KEY,
        )
    elif scope_needed or any(row.get("scope_label") for row in table["values"]):
        table["titles"] = _detail_titles(True)
    row = _find_row(table["values"], _DETAIL_KEY, key)
    payload = {
        _DETAIL_KEY: key,
        "source_cluster": source_cluster,
        "target_cluster": target_cluster,
        "item_name": force_str(item.name),
        "status": item_status(results),
        "message": "；".join(result.message for result in failed if result.message),
    }
    if scope_label:
        payload["scope_label"] = scope_label
    row.update(payload)


def _ensure_table(output, table_name, display_name, titles, primary_key) -> dict:
    table = _find_table(output, table_name)
    if table is None:
        table = {
            "table_name": table_name,
            "table_display_name": display_name,
            "table_primary_key": primary_key,
            "remark": "",
            "titles": titles,
            "values": [],
            "hidden": False,
        }
        output.append(table)
    else:
        table["titles"] = titles
        table["table_display_name"] = display_name
    return table


def _find_table(output, table_name) -> dict | None:
    for table in output:
        if table.get("table_name") == table_name:
            return table
    return None


def _find_row(values: list[dict], key_name: str, key: str) -> dict:
    for row in values:
        if row.get(key_name) == key:
            return row
    row = {key_name: key}
    values.append(row)
    return row
