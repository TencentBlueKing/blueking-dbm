#!/usr/bin/env python3
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

import logging
from typing import Any, Dict, List

from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component

from backend.components import DRSApi
from backend.db_meta.models import Cluster
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.spider.spider_check_constants import (
    CHECK_TYPE_DESCRIPTIONS,
    COLUMN_CHECK,
    INDEX_CHECK,
    TABLE_CHECK,
    TRIGGER_CHECK,
    VIEW_CHECK,
)
from backend.flow.utils.spider.spider_version_upgrade_checker import (
    SpiderVersionUpgradeChecker,
    generate_upgrade_check_sqls,
)

logger = logging.getLogger("flow")


class UpgradeKeyWordCheckService(BaseService):
    """
    Spider跨版本升级关键字检查服务

    用于检查Spider数据库跨版本升级时可能出现的关键字冲突问题。
    支持从tspider1.x到tspider3.x，以及从tspider3.x到tspider4.x的升级检查。

    私有变量的主要结构体kwargs：
    {
        "cluster_id": int,  # 待检查的集群ID
        "to_version": str,  # 目标版本，如 "10.3.7-MariaDB-tspider-3.7.11-log"
        "from_version_map": Dict[str, List[str]],  # 源版本到地址的映射，如 {"5.5.24-tspider-1.15-log": ["192.168.1.100:25000"]}
        "schemas": List[str],  # 可选，指定要检查的数据库列表，默认检查所有业务数据库
        "check_types": List[str],  # 可选，指定检查类型，默认检查所有类型
        "fail_on_conflict": bool,  # 可选，是否在发现冲突时失败，默认True
    }

    功能特性：
    - 按版本聚合检查：调用侧传入版本到地址的映射，每个版本只检查指定节点
    - 版本对比报告：生成不同版本间的冲突对比分析
    - 详细的版本分布日志：显示每个版本的实例数量和地址信息
    """

    checker = SpiderVersionUpgradeChecker()

    def _execute_check_sqls(
        self,
        addresses: List[str],
        check_sqls: Dict[str, str],
        bk_cloud_id: int,
        version: str = None,
    ) -> Dict[str, Any]:
        """
        执行关键字检查SQL

        Args:
            addresses: 要检查的实例地址列表
            check_sqls: 检查SQL字典，key为检查类型，value为SQL语句
            bk_cloud_id: 云区域ID
            version: 当前检查的版本（可选）

        Returns:
            Dict[str, Any]: 检查结果
        """
        results = {}

        for check_type, sql in check_sqls.items():
            version_info = f" [{_('版本')}: {version}]" if version else ""
            self.log_info(_("执行{}检查{}: {}").format(check_type, version_info, sql))

            try:
                # 使用DRSApi.rpc执行SQL
                response = DRSApi.rpc(
                    {
                        "addresses": addresses,
                        "cmds": [sql],
                        "force": False,
                        "bk_cloud_id": bk_cloud_id,
                    }
                )

                # 处理响应结果
                check_result = {
                    "check_type": check_type,
                    "sql": sql,
                    "results": [],
                    "has_conflicts": False,
                    "total_conflicts": 0,
                }

                for addr_result in response:
                    address = addr_result.get("address", "")
                    error_msg = addr_result.get("error_msg", "")

                    if error_msg:
                        self.log_error(_("地址[{}]执行{}检查失败: {}").format(address, check_type, error_msg))
                        check_result["results"].append(
                            {
                                "address": address,
                                "error": error_msg,
                                "conflicts": [],
                            }
                        )
                        continue

                    # 解析检查结果
                    cmd_results = addr_result.get("cmd_results", [])
                    if cmd_results:
                        cmd_result = cmd_results[0]
                        table_data = cmd_result.get("table_data", [])

                        # 转换为标准格式供format_check_results使用
                        raw_results = []
                        for row in table_data:
                            if check_type in [
                                TABLE_CHECK,
                                VIEW_CHECK,
                                TRIGGER_CHECK,
                                "procedure_check",
                                "function_check",
                            ]:
                                # 对象名检查
                                object_name = (
                                    row.get("TABLE_NAME") or row.get("ROUTINE_NAME") or row.get("TRIGGER_NAME")
                                )
                                schema_name = (
                                    row.get("TABLE_SCHEMA") or row.get("ROUTINE_SCHEMA") or row.get("TRIGGER_SCHEMA")
                                )
                                object_type = row.get("TABLE_TYPE") or row.get("ROUTINE_TYPE") or _("触发器")
                                if object_name:
                                    raw_results.append((schema_name, object_name, object_type, None))
                            elif check_type == COLUMN_CHECK:
                                # 列名检查
                                column_name = row.get("COLUMN_NAME")
                                table_name = row.get("TABLE_NAME")
                                schema_name = row.get("TABLE_SCHEMA")
                                if column_name:
                                    raw_results.append((schema_name, table_name, _("列名"), column_name))
                            elif check_type == INDEX_CHECK:
                                # 索引名检查
                                index_name = row.get("INDEX_NAME")
                                table_name = row.get("TABLE_NAME")
                                schema_name = row.get("TABLE_SCHEMA")
                                if index_name:
                                    raw_results.append((schema_name, table_name, _("索引名"), index_name))

                        # 使用checker的format_check_results方法格式化结果
                        conflict_type_map = {
                            TABLE_CHECK: _("表名"),
                            COLUMN_CHECK: _("列名"),
                            INDEX_CHECK: _("索引名"),
                            VIEW_CHECK: _("视图名"),
                            TRIGGER_CHECK: _("触发器名"),
                            "procedure_check": _("函数/存储过程名"),
                            "function_check": _("函数/存储过程名"),
                        }
                        # 使用常量中的描述映射，回退到本地映射
                        conflict_type_desc = CHECK_TYPE_DESCRIPTIONS.get(
                            check_type, conflict_type_map.get(check_type, _("对象名"))
                        )

                        formatted_conflicts = self.checker.format_check_results(raw_results, conflict_type_desc)

                        # 转换为更友好的格式
                        conflicts = []
                        for conflict in formatted_conflicts:
                            conflict_info = {
                                "schema_name": conflict.schema_name,
                                "object_name": conflict.object_name,
                                "object_type": conflict.object_type,
                                "column_name": conflict.column_name,
                                "conflict_keyword": conflict.conflict_keyword,
                                "suggested_fix": conflict.suggested_fix,
                                "priority": self._get_conflict_priority(conflict.conflict_keyword),
                            }
                            conflicts.append(conflict_info)

                        check_result["results"].append(
                            {
                                "address": address,
                                "conflicts": conflicts,
                                "conflict_count": len(conflicts),
                                "formatted_conflicts": formatted_conflicts,  # 保留原始格式化结果
                            }
                        )

                        if conflicts:
                            check_result["has_conflicts"] = True
                            check_result["total_conflicts"] += len(conflicts)

                results[check_type] = check_result

                if check_result["has_conflicts"]:
                    self.log_warning(_("{}检查发现{}个冲突").format(check_type, check_result["total_conflicts"]))
                else:
                    self.log_info(_("✅{}检查通过，无冲突").format(check_type))

            except Exception as e:
                self.log_error(_("执行{}检查时发生异常: {}").format(check_type, str(e)))
                results[check_type] = {
                    "check_type": check_type,
                    "sql": sql,
                    "error": str(e),
                    "has_conflicts": False,
                    "total_conflicts": 0,
                }

        return results

    def _get_conflict_priority(self, keyword: str) -> str:
        """
        获取关键字冲突的优先级

        Args:
            keyword: 关键字

        Returns:
            str: 优先级 (high/medium/low)
        """
        try:
            conflict_info = self.checker.check_keyword_conflict_type(keyword)
            return conflict_info.get("conflict_level", "low")
        except Exception:
            return "low"

    def _generate_detailed_conflict_summary(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成详细的冲突摘要

        Args:
            results: 检查结果

        Returns:
            Dict[str, Any]: 详细冲突摘要
        """
        conflict_by_priority = {"high": [], "medium": [], "low": []}
        conflict_by_type = {}
        conflict_by_version = {}
        total_instances_affected = set()

        for check_type, result in results.items():
            if result.get("has_conflicts"):
                conflict_by_type[check_type] = {
                    "count": result.get("total_conflicts", 0),
                    "instances": [],
                    "versions": {},
                }

                # 处理版本特定的结果
                version_results = result.get("version_results", {})
                for version, version_result in version_results.items():
                    if version not in conflict_by_version:
                        conflict_by_version[version] = {
                            "total_conflicts": 0,
                            "check_types": {},
                            "instances": set(),
                        }

                    if version_result.get("has_conflicts"):
                        version_conflicts = version_result.get("total_conflicts", 0)
                        conflict_by_version[version]["total_conflicts"] += version_conflicts
                        conflict_by_version[version]["check_types"][check_type] = version_conflicts

                        # 记录版本的实例信息
                        for instance_result in version_result.get("results", []):
                            address = instance_result.get("address")
                            conflicts = instance_result.get("conflicts", [])

                            if conflicts:
                                conflict_by_version[version]["instances"].add(address)

                        conflict_by_type[check_type]["versions"][version] = {
                            "count": version_conflicts,
                            "instances": len([r for r in version_result.get("results", []) if r.get("conflicts")]),
                        }

                for instance_result in result.get("results", []):
                    address = instance_result.get("address")
                    conflicts = instance_result.get("conflicts", [])

                    if conflicts:
                        total_instances_affected.add(address)
                        conflict_by_type[check_type]["instances"].append(
                            {
                                "address": address,
                                "conflict_count": len(conflicts),
                            }
                        )

                        # 按优先级分类冲突
                        for conflict in conflicts:
                            priority = conflict.get("priority", "low")
                            conflict_by_priority[priority].append(
                                {
                                    "check_type": check_type,
                                    "address": address,
                                    "conflict": conflict,
                                }
                            )

        # 转换版本信息中的set为list
        for version_info in conflict_by_version.values():
            version_info["instances"] = list(version_info["instances"])

        return {
            "by_priority": {
                "high": len(conflict_by_priority["high"]),
                "medium": len(conflict_by_priority["medium"]),
                "low": len(conflict_by_priority["low"]),
                "details": conflict_by_priority,
            },
            "by_type": conflict_by_type,
            "by_version": conflict_by_version,
            "instances_affected": {
                "count": len(total_instances_affected),
                "addresses": list(total_instances_affected),
            },
        }

    def _generate_recommendations(self, detailed_summary: Dict[str, Any]) -> List[str]:
        """
        生成修复建议

        Args:
            detailed_summary: 详细冲突摘要

        Returns:
            List[str]: 修复建议列表
        """
        recommendations = []

        high_priority = detailed_summary["by_priority"]["high"]
        medium_priority = detailed_summary["by_priority"]["medium"]
        low_priority = detailed_summary["by_priority"]["low"]

        if high_priority > 0:
            recommendations.append(_("🔴 发现 {} 个高优先级冲突，必须在升级前解决").format(high_priority))
            recommendations.append(_("   建议：立即处理这些冲突，否则升级可能失败"))

        if medium_priority > 0:
            recommendations.append(_("🟡 发现 {} 个中优先级冲突，建议在升级前解决").format(medium_priority))
            recommendations.append(_("   建议：评估影响并在升级前处理"))

        if low_priority > 0:
            recommendations.append(_("🟢 发现 {} 个低优先级冲突，可在升级后处理").format(low_priority))

        if high_priority == 0 and medium_priority == 0 and low_priority == 0:
            recommendations.append(_("✅ 未发现关键字冲突，可以安全升级"))

        # 添加具体的修复建议
        if detailed_summary["by_type"]:
            recommendations.append(_("\n📋 具体修复建议："))
            for check_type, type_info in detailed_summary["by_type"].items():
                recommendations.append(
                    _("   {} 类型冲突 {} 个，影响 {} 个实例").format(check_type, type_info["count"], len(type_info["instances"]))
                )

        return recommendations

    def _generate_version_comparison_report(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成版本对比报告

        Args:
            results: 检查结果

        Returns:
            Dict[str, Any]: 版本对比报告
        """
        version_comparison = {}

        for check_type, result in results.items():
            version_results = result.get("version_results", {})
            if len(version_results) > 1:  # 只有多版本时才生成对比
                comparison = {
                    "check_type": check_type,
                    "versions": {},
                    "differences": [],
                }

                for version, version_result in version_results.items():
                    comparison["versions"][version] = {
                        "has_conflicts": version_result.get("has_conflicts", False),
                        "total_conflicts": version_result.get("total_conflicts", 0),
                        "instance_count": version_result.get("instance_count", 0),
                        "conflict_rate": (
                            version_result.get("total_conflicts", 0) / max(version_result.get("instance_count", 1), 1)
                        ),
                    }

                # 分析版本间的差异
                versions = list(version_results.keys())
                for i, version1 in enumerate(versions):
                    for version2 in versions[i + 1 :]:
                        v1_conflicts = comparison["versions"][version1]["total_conflicts"]
                        v2_conflicts = comparison["versions"][version2]["total_conflicts"]

                        if v1_conflicts != v2_conflicts:
                            comparison["differences"].append(
                                {
                                    "version1": version1,
                                    "version2": version2,
                                    "conflicts1": v1_conflicts,
                                    "conflicts2": v2_conflicts,
                                    "difference": abs(v1_conflicts - v2_conflicts),
                                }
                            )

                version_comparison[check_type] = comparison

        return version_comparison

    def _generate_check_report(self, results: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成检查报告

        Args:
            results: 检查结果

        Returns:
            Dict[str, Any]: 检查报告
        """
        total_conflicts = 0
        has_any_conflicts = False
        failed_checks = []

        for check_type, result in results.items():
            if result.get("error"):
                failed_checks.append(check_type)
            elif result.get("has_conflicts"):
                has_any_conflicts = True
                total_conflicts += result.get("total_conflicts", 0)

        # 生成详细的冲突摘要
        detailed_summary = self._generate_detailed_conflict_summary(results)

        # 生成版本对比报告
        version_comparison = self._generate_version_comparison_report(results)

        report = {
            "summary": {
                "total_checks": len(results),
                "failed_checks": len(failed_checks),
                "has_conflicts": has_any_conflicts,
                "total_conflicts": total_conflicts,
                "check_passed": not has_any_conflicts and not failed_checks,
                "priority_breakdown": {
                    "high_priority": detailed_summary["by_priority"]["high"],
                    "medium_priority": detailed_summary["by_priority"]["medium"],
                    "low_priority": detailed_summary["by_priority"]["low"],
                },
                "instances_affected": detailed_summary["instances_affected"]["count"],
                "versions_detected": len(detailed_summary.get("by_version", {})),
            },
            "details": results,
            "failed_checks": failed_checks,
            "conflict_analysis": detailed_summary,
            "version_comparison": version_comparison,
            "recommendations": self._generate_recommendations(detailed_summary),
        }

        return report

    def _log_detailed_conflicts(self, report: Dict[str, Any]) -> None:
        """
        记录详细的冲突信息

        Args:
            report: 检查报告
        """
        summary = report["summary"]
        conflict_analysis = report.get("conflict_analysis", {})

        # 记录总体情况
        self.log_warning(
            _("⚠️  关键字检查发现 {} 个冲突，影响 {} 个实例").format(summary["total_conflicts"], summary["instances_affected"])
        )

        # 记录版本分布的冲突
        by_version = conflict_analysis.get("by_version", {})
        if by_version:
            self.log_info(_("📋 按版本分布的冲突："))
            for version, version_info in by_version.items():
                if version_info["total_conflicts"] > 0:
                    self.log_warning(
                        _("   版本[{}]: {} 个冲突，影响 {} 个实例").format(
                            version, version_info["total_conflicts"], len(version_info["instances"])
                        )
                    )
                    # 显示该版本的检查类型分布
                    for check_type, count in version_info["check_types"].items():
                        self.log_info(_("     - {}: {} 个冲突").format(check_type, count))

        # 记录优先级分布
        priority_breakdown = summary.get("priority_breakdown", {})
        if priority_breakdown.get("high_priority", 0) > 0:
            self.log_error(_("   🔴 高优先级冲突: {} 个（必须处理）").format(priority_breakdown["high_priority"]))
        if priority_breakdown.get("medium_priority", 0) > 0:
            self.log_warning(_("   🟡 中优先级冲突: {} 个（建议处理）").format(priority_breakdown["medium_priority"]))
        if priority_breakdown.get("low_priority", 0) > 0:
            self.log_info(_("   🟢 低优先级冲突: {} 个（可延后处理）").format(priority_breakdown["low_priority"]))

        # 记录按类型分布的冲突
        by_type = conflict_analysis.get("by_type", {})
        if by_type:
            self.log_info(_("📊 冲突类型分布："))
            for check_type, type_info in by_type.items():
                self.log_info(_("   {} : {} 个冲突").format(check_type, type_info["count"]))
                # 显示该类型在各版本的分布
                versions = type_info.get("versions", {})
                if len(versions) > 1:  # 只有多版本时才显示版本分布
                    for version, version_count in versions.items():
                        if version_count["count"] > 0:
                            self.log_info(_("     版本[{}]: {} 个冲突").format(version, version_count["count"]))

        # 记录所有冲突详情
        self._log_conflict_examples(report)

    def _log_conflict_examples(self, report: Dict[str, Any]) -> None:
        """
        记录所有冲突详情

        Args:
            report: 检查报告
        """
        details = report.get("details", {})
        total_conflicts = 0

        self.log_info(_("🔍 所有冲突详情："))

        for check_type, result in details.items():
            if result.get("has_conflicts"):
                self.log_info(_("📋 {} 检查结果：").format(check_type))

                for instance_result in result.get("results", []):
                    address = instance_result.get("address")
                    conflicts = instance_result.get("conflicts", [])

                    if conflicts:
                        self.log_info(_("   实例地址: {}").format(address))

                        for conflict in conflicts:
                            priority_icon = {
                                "high": "🔴",
                                "medium": "🟡",
                                "low": "🟢",
                            }.get(conflict.get("priority", "low"), "🟢")

                            # 输出完整的修复建议，不截断
                            suggested_fix = conflict.get("suggested_fix", _("使用反引号包裹"))

                            self.log_warning(
                                _("      {} {}.{} - {}").format(
                                    priority_icon,
                                    conflict.get("schema_name", "N/A"),
                                    conflict.get("object_name", "N/A"),
                                    suggested_fix,
                                )
                            )
                            total_conflicts += 1

                        self.log_info(_("   该实例共发现 {} 个冲突").format(len(conflicts)))
                        self.log_info("")  # 空行分隔

        if total_conflicts == 0:
            self.log_info(_("   （无具体冲突详情）"))
        else:
            self.log_info(_("📊 总计发现 {} 个冲突").format(total_conflicts))

    def _execute(self, data, parent_data) -> bool:
        """
        执行关键字检查

        Args:
            data: 输入数据
            parent_data: 父级数据

        Returns:
            bool: 执行是否成功
        """
        kwargs = data.get_one_of_inputs("kwargs")

        # 获取必要参数
        cluster_id = kwargs.get("cluster_id")
        to_version = kwargs.get("to_version")
        from_version_map = kwargs.get("from_version_map", {})

        if not all([cluster_id, to_version, from_version_map]):
            self.log_error(_("缺少必要参数: cluster_id, to_version, from_version_map"))
            return False

        # 获取集群信息
        try:
            cluster = Cluster.objects.get(id=cluster_id)
        except Cluster.DoesNotExist:
            self.log_error(_("集群[{}]不存在").format(cluster_id))
            return False

        self.log_info(_("开始对集群[{}]进行关键字检查").format(cluster.immute_domain))
        self.log_info(_("目标版本: {}").format(to_version))

        # 记录版本分布情况
        self.log_info(_("集群[{}]版本分布:").format(cluster.immute_domain))
        for version, addresses in from_version_map.items():
            self.log_info(_("  版本[{}]: 检查节点 - {}").format(version, ", ".join(addresses)))

        # 获取要检查的数据库列表
        schemas = kwargs.get("schemas")

        # 执行检查 - 按版本分组执行
        all_results = {}

        for version, addresses in from_version_map.items():
            self.log_info(_("开始检查版本[{}]的{}个实例").format(version, len(addresses)))

            # 为每个版本生成检查SQL
            try:
                check_sqls = generate_upgrade_check_sqls(version, to_version, schemas)
            except Exception as e:
                self.log_error(_("生成检查SQL失败: {}").format(str(e)))
                return False

            if not check_sqls:
                self.log_warning(_("版本[{}]未生成任何检查SQL").format(version))
                continue

            # 过滤检查类型
            check_types = kwargs.get("check_types")
            if check_types:
                filtered_sqls = {k: v for k, v in check_sqls.items() if k in check_types}
                check_sqls = filtered_sqls
                self.log_info(_("版本[{}]过滤后剩余{}个检查SQL").format(version, len(check_sqls)))

            # 为每个版本执行检查
            version_results = self._execute_check_sqls(addresses, check_sqls, cluster.bk_cloud_id, version)

            # 将版本信息添加到结果中
            for check_type, result in version_results.items():
                result["version"] = version
                result["instance_count"] = len(addresses)

                # 合并到总结果中
                if check_type not in all_results:
                    all_results[check_type] = {
                        "check_type": check_type,
                        "sql": result["sql"],
                        "results": [],
                        "has_conflicts": False,
                        "total_conflicts": 0,
                        "version_results": {},
                    }

                # 添加版本特定的结果
                all_results[check_type]["version_results"][version] = result
                all_results[check_type]["results"].extend(result.get("results", []))

                if result.get("has_conflicts"):
                    all_results[check_type]["has_conflicts"] = True
                    all_results[check_type]["total_conflicts"] += result.get("total_conflicts", 0)

        results = all_results

        # 生成报告
        report = self._generate_check_report(results)
        self.log_info(_("检查报告生成完成"))
        # 输出结果
        data.outputs.check_report = report
        data.outputs.ext_result = report

        # 记录检查结果
        if report["summary"]["check_passed"]:
            self.log_info(_("✅ 关键字检查通过，无冲突"))
        else:
            if report["summary"]["has_conflicts"]:
                self._log_detailed_conflicts(report)
            if report["failed_checks"]:
                self.log_error(_("❌ 以下检查执行失败: {}").format(", ".join(report["failed_checks"])))

        # 输出建议
        for recommendation in report.get("recommendations", []):
            if "🔴" in recommendation:
                self.log_error(recommendation)
            elif "🟡" in recommendation:
                self.log_warning(recommendation)
            else:
                self.log_info(recommendation)

        # 根据配置决定是否因为冲突而失败
        fail_on_conflict = kwargs.get("fail_on_conflict", True)
        has_issues = report["summary"]["has_conflicts"] or report["failed_checks"]
        if fail_on_conflict and has_issues:
            self.log_error(_("关键字检查未通过，流程终止"))
            return False

        return True


class UpgradeKeyWordCheckComponent(Component):
    """
    Spider跨版本升级关键字检查组件
    """

    name = __name__
    code = "upgrade_key_word_check"
    bound_service = UpgradeKeyWordCheckService
