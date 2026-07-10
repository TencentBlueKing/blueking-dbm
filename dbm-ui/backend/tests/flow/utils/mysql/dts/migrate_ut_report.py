# -*- coding: utf-8 -*-
"""DTS 迁移验收报告收集与落盘（Markdown + JSON）。"""
from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class ScenarioResult:
    scenario_id: str
    title: str
    sync_scope: dict[str, Any] = field(default_factory=dict)
    rules: list[dict[str, Any]] = field(default_factory=list)
    seed_summary: str = ""
    api_logs: list[str] = field(default_factory=list)
    check_summary: str = ""
    result: str = "PENDING"  # PASS / FAIL / SKIP
    detail: str = ""
    l1_ok: bool | None = None
    l2_ok: bool | None = None


class MigrateUtReport:
    def __init__(self, *, env_info: dict[str, str] | None = None):
        self.env_info = env_info or {}
        self.scenarios: list[ScenarioResult] = []
        self.started_at = datetime.now()

    def add(self, item: ScenarioResult) -> None:
        self.scenarios.append(item)

    def write(self, report_dir: str | None = None) -> tuple[str, str]:
        report_dir = report_dir or os.environ.get(
            "DTS_UT_REPORT_DIR",
            os.path.join(os.path.dirname(__file__), "reports"),
        )
        os.makedirs(report_dir, exist_ok=True)
        stamp = self.started_at.strftime("%Y%m%d_%H%M%S")
        md_path = os.path.join(report_dir, f"dts_migrate_ut_{stamp}.md")
        json_path = os.path.join(report_dir, f"dts_migrate_ut_{stamp}.json")
        with open(md_path, "w", encoding="utf-8") as fp:
            fp.write(self._render_markdown())
        with open(json_path, "w", encoding="utf-8") as fp:
            json.dump(self._to_dict(), fp, ensure_ascii=False, indent=2)
        print(f"[DTS-UT] REPORT md={md_path}")
        print(f"[DTS-UT] REPORT json={json_path}")
        return md_path, json_path

    def overview_table(self) -> str:
        lines = [
            "| ID | 场景 | L1 | L2 | 结果 | 说明 |",
            "|----|------|----|----|------|------|",
        ]
        for s in self.scenarios:
            l1 = _tri(s.l1_ok)
            l2 = _tri(s.l2_ok)
            lines.append(f"| {s.scenario_id} | {s.title} | {l1} | {l2} | {s.result} | {s.detail} |")
        return "\n".join(lines)

    def _to_dict(self) -> dict[str, Any]:
        return {
            "started_at": self.started_at.isoformat(timespec="seconds"),
            "finished_at": datetime.now().isoformat(timespec="seconds"),
            "env": self.env_info,
            "scenarios": [asdict(s) for s in self.scenarios],
        }

    def _render_markdown(self) -> str:
        parts = [
            "# DTS 迁移代码验收报告",
            "",
            "## 环境",
            f"- 时间: {self.started_at.isoformat(timespec='seconds')}",
        ]
        for key, value in self.env_info.items():
            parts.append(f"- {key}: {value}")
        parts.extend(["", "## 总览", self.overview_table(), "", "## 分场景详情", ""])
        for s in self.scenarios:
            parts.extend(
                [
                    f"### {s.scenario_id} {s.title}",
                    f"- 结论: **{s.result}** — {s.detail}",
                    f"- sync_scope: `{json.dumps(s.sync_scope, ensure_ascii=False)}`",
                    f"- table_migrate_rule: `{json.dumps(s.rules, ensure_ascii=False)}`",
                    f"- 源数据: {s.seed_summary or '-'}",
                    f"- 目标校验: {s.check_summary or '-'}",
                    "- API 过程:",
                ]
            )
            if s.api_logs:
                for line in s.api_logs:
                    parts.append(f"  - {line}")
            else:
                parts.append("  - (无)")
            parts.append("")
        return "\n".join(parts)


def _tri(value: bool | None) -> str:
    if value is True:
        return "OK"
    if value is False:
        return "FAIL"
    return "-"
