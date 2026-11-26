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
import json
import re
from typing import Optional, Tuple

from django.utils.translation import gettext as _

from backend.db_meta.enums import ClusterType

RULE_VERSION = "config_check_v1"
REQUIRED_CHECKS = ("config_rationality", "config_consistency", "version_compatibility")
CHECK_STATUSES = ("completed", "not_applicable", "insufficient_data")
CATEGORIES = ("durability", "resource", "consistency", "version_compatibility", "performance")
SEVERITY_DEDUCTIONS = {"high": 15, "medium": 5, "low": 1}
HIGH_SCORE_CAP = 60
_ISSUE_KEY_RE = re.compile(r"[a-z0-9][a-z0-9_.:+-]*")


def _has_text(value) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _has_strings(value) -> bool:
    return isinstance(value, list) and bool(value) and all(_has_text(item) for item in value)


def _validate_checks(checks, cluster_type: str) -> list:
    if not isinstance(checks, list):
        return [_("缺少有效的核心检查列表")]
    errors = []
    seen = set()
    for check in checks:
        if not isinstance(check, dict):
            errors.append(_("核心检查项必须为对象"))
            continue
        code = check.get("code")
        if not isinstance(code, str) or code not in REQUIRED_CHECKS:
            errors.append(_("未知的核心检查项"))
            continue
        if code in seen:
            errors.append(_("核心检查项重复: {}").format(code))
        seen.add(code)
        status = check.get("status")
        if status not in CHECK_STATUSES:
            errors.append(_("核心检查状态无效: {}").format(code))
        elif not _has_text(check.get("reason")):
            errors.append(_("核心检查缺少依据或原因: {}").format(code))
        elif status == "insufficient_data":
            errors.append(_("核心检查数据不足: {}").format(code))
        elif status == "not_applicable" and not (
            code == "config_consistency" and cluster_type == ClusterType.TenDBSingle.value
        ):
            errors.append(_("当前集群不允许跳过该核心检查: {}").format(code))
    for code in REQUIRED_CHECKS:
        if code not in seen:
            errors.append(_("缺少核心检查项: {}").format(code))
    return errors


def _normalize_finding(finding) -> dict:
    if not isinstance(finding, dict):
        raise ValueError(_("问题项必须为对象"))
    for field in ("issue_key", "category", "severity", "evidence", "impact"):
        if not _has_text(finding.get(field)):
            raise ValueError(_("问题项缺少有效字段: {}").format(field))
    issue_key = finding["issue_key"].strip().lower()
    if not _ISSUE_KEY_RE.fullmatch(issue_key):
        raise ValueError(_("问题标识格式无效"))
    if finding["category"] not in CATEGORIES:
        raise ValueError(_("问题类别无效"))
    severity = finding["severity"]
    if severity not in SEVERITY_DEDUCTIONS:
        raise ValueError(_("问题严重度无效"))
    if not _has_strings(finding.get("parameters")):
        raise ValueError(_("问题参数列表无效"))
    scope = finding.get("scope")
    if not isinstance(scope, dict) or not _has_text(scope.get("role")) or not _has_strings(scope.get("instances")):
        raise ValueError(_("问题影响范围无效"))
    return {
        "issue_key": issue_key,
        "category": finding["category"],
        "parameters": sorted({param.strip().lower() for param in finding["parameters"]}),
        "scope": {
            "role": scope["role"].strip().lower(),
            "instances": sorted({instance.strip() for instance in scope["instances"]}),
        },
        "severity": severity,
        "deduction": SEVERITY_DEDUCTIONS[severity],
    }


def _deduplicate_findings(findings) -> Tuple[list, list]:
    if not isinstance(findings, list):
        return [], [_("缺少有效的问题列表")]
    unique = {}
    errors = []
    for index, finding in enumerate(findings):
        try:
            item = _normalize_finding(finding)
        except ValueError as exc:
            errors.append(_("问题项 {} 无效: {}").format(index, exc))
            continue
        key = (item["issue_key"], item["scope"]["role"])
        if key not in unique:
            item["source_indices"] = [index]
            unique[key] = item
            continue
        previous = unique[key]
        if previous["category"] != item["category"] or previous["parameters"] != item["parameters"]:
            errors.append(_("同一问题标识的类别或参数组冲突: {}").format(item["issue_key"]))
            continue
        previous["source_indices"].append(index)
        previous["scope"]["instances"] = sorted(set(previous["scope"]["instances"] + item["scope"]["instances"]))
        if item["deduction"] > previous["deduction"]:
            previous["severity"] = item["severity"]
            previous["deduction"] = item["deduction"]
    return list(unique.values()), errors


def calculate_config_score(parsed: dict, cluster_type: str) -> Tuple[Optional[float], dict]:
    """评分不可用时返回 None，独立于报告是否成功；保留输入和规则供追溯、复算。"""
    detail = {
        "rule_version": RULE_VERSION,
        "cluster_type": cluster_type,
        "status": "unavailable",
        "checks": parsed.get("checks"),
        "findings": parsed.get("findings"),
        "errors": [],
    }
    try:
        json.dumps(detail, allow_nan=False)
    except (ValueError, TypeError):
        detail.update(checks=None, findings=None, errors=[_("评分数据不是有效的 JSON 数据")])
        return None, detail
    detail["errors"] = _validate_checks(detail["checks"], cluster_type)
    deductions, finding_errors = _deduplicate_findings(detail["findings"])
    detail["errors"].extend(finding_errors)
    if detail["errors"]:
        return None, detail

    counts = {severity: 0 for severity in SEVERITY_DEDUCTIONS}
    for item in deductions:
        counts[item["severity"]] += 1
    total_deduction = sum(item["deduction"] for item in deductions)
    base_score = max(0, 100 - total_deduction)
    score = min(base_score, HIGH_SCORE_CAP) if counts["high"] else base_score
    detail.update(
        status="scored",
        counts=counts,
        deductions=deductions,
        total_deduction=total_deduction,
        base_score=base_score,
        high_risk_cap=HIGH_SCORE_CAP if counts["high"] else None,
        cap_applied=score < base_score,
        score=score,
    )
    return float(score), detail
