#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Spider跨版本升级关键字检查组件测试

本文件包含对Spider版本升级检查器的单元测试和使用示例。
"""

import unittest

from django.test import TestCase
from django.utils.translation import gettext as _

from backend.flow.utils.spider.spider_check_constants import (
    COLUMN_CHECK,
    ROUTINE_CHECK,
    TABLE_CHECK,
    TRIGGER_CHECK,
    VIEW_CHECK,
)

from .spider_version_upgrade_checker import (
    KeywordCheckResult,
    SpiderVersion,
    check_specific_keywords_conflict,
    check_spider_upgrade_keywords,
    create_spider_upgrade_checker,
    generate_upgrade_check_sqls,
    get_version_specific_keywords,
)


class TestSpiderVersionUpgradeChecker(TestCase):
    """Spider版本升级检查器测试类"""

    def setUp(self):
        """测试初始化"""
        self.checker = create_spider_upgrade_checker()

    def test_version_parsing(self):
        """测试版本字符串解析"""
        test_cases = [
            ("5.5.24-tspider-1.15-log", SpiderVersion.TSPIDER_1X),
            ("10.3.7-MariaDB-tspider-3.7.11-log", SpiderVersion.TSPIDER_3X),
            ("11.4.2-MariaDB-tspider-4.0.3-log", SpiderVersion.TSPIDER_4X),
            ("invalid-version", None),
            ("", None),
        ]

        for version_str, expected in test_cases:
            with self.subTest(version_str=version_str):
                result = self.checker.parse_version_string(version_str)
                self.assertEqual(result, expected)

    def test_get_upgrade_keywords(self):
        """测试获取升级关键字"""
        # 测试1.x -> 3.x升级
        keywords_1x_3x = self.checker.get_upgrade_keywords(SpiderVersion.TSPIDER_1X, SpiderVersion.TSPIDER_3X)
        self.assertIsInstance(keywords_1x_3x, list)
        self.assertTrue(len(keywords_1x_3x) > 0)

        # 测试3.x -> 4.x升级
        keywords_3x_4x = self.checker.get_upgrade_keywords(SpiderVersion.TSPIDER_3X, SpiderVersion.TSPIDER_4X)
        self.assertIsInstance(keywords_3x_4x, list)
        self.assertTrue(len(keywords_3x_4x) > 0)

        # 测试1.x -> 4.x升级（跨版本）
        keywords_1x_4x = self.checker.get_upgrade_keywords(SpiderVersion.TSPIDER_1X, SpiderVersion.TSPIDER_4X)
        # 跨版本升级应该包含更多关键字
        self.assertTrue(len(keywords_1x_4x) >= len(keywords_1x_3x))
        self.assertTrue(len(keywords_1x_4x) >= len(keywords_3x_4x))

    def test_unsupported_upgrade_path(self):
        """测试不支持的升级路径"""
        with self.assertRaises(ValueError):
            self.checker.get_upgrade_keywords(SpiderVersion.TSPIDER_3X, SpiderVersion.TSPIDER_1X)  # 不支持降级

    def test_sql_generation(self):
        """测试SQL生成"""
        keywords = ["EXCEPT", "OVER", "RECURSIVE"]

        # 测试表名检查SQL
        table_sql = self.checker.generate_table_check_sql(keywords)
        self.assertIn("information_schema.tables", table_sql)
        self.assertIn("EXCEPT", table_sql)
        self.assertIn("TABLE_SCHEMA", table_sql)

        # 测试列名检查SQL
        column_sql = self.checker.generate_column_check_sql(keywords)
        self.assertIn("information_schema.columns", column_sql)
        self.assertIn("COLUMN_NAME", column_sql)

        # 测试带schema过滤的SQL
        table_sql_with_schema = self.checker.generate_table_check_sql(keywords, schemas=["test_db", "prod_db"])
        self.assertIn("TABLE_SCHEMA IN", table_sql_with_schema)
        self.assertIn("test_db", table_sql_with_schema)

    def test_all_check_sqls_generation(self):
        """测试生成所有检查SQL语句"""
        check_sqls = self.checker.generate_all_check_sqls(SpiderVersion.TSPIDER_1X, SpiderVersion.TSPIDER_3X)
        expected_keys = [TABLE_CHECK, COLUMN_CHECK, ROUTINE_CHECK, TRIGGER_CHECK, VIEW_CHECK]

        for key in expected_keys:
            self.assertIn(key, check_sqls)
            self.assertIsInstance(check_sqls[key], str)
            self.assertTrue(len(check_sqls[key]) > 0)

    def test_compatibility_check(self):
        """测试兼容性检查"""
        # 测试支持的升级路径
        result = self.checker.check_upgrade_compatibility(SpiderVersion.TSPIDER_1X, SpiderVersion.TSPIDER_3X)
        self.assertTrue(result["compatible"])
        self.assertTrue(result["keywords_count"] > 0)
        self.assertIsInstance(result["keywords_to_check"], list)

        # 测试不支持的升级路径
        try:
            result = self.checker.check_upgrade_compatibility(SpiderVersion.TSPIDER_4X, SpiderVersion.TSPIDER_1X)
            self.assertFalse(result["compatible"])
        except ValueError:
            pass  # 预期的异常

    def test_suggest_fix_for_conflict(self):
        """测试冲突修复建议"""
        suggestions = [
            ("test_table", _("表名"), "TEST_TABLE"),
            ("test_column", _("列名"), "TEST_COLUMN"),
            ("test_func", _("函数/存储过程名"), "TEST_FUNC"),
        ]

        for object_name, object_type, conflict_keyword in suggestions:
            suggestion = self.checker.suggest_fix_for_conflict(object_name, object_type, conflict_keyword)
            self.assertIsInstance(suggestion, str)
            self.assertTrue(len(suggestion) > 0)
            self.assertIn(object_name, suggestion)

    def test_format_check_results(self):
        """测试检查结果格式化"""
        mock_results = [
            ("test_db", "except_table", "BASE TABLE", None),
            ("test_db", "user_table", "BASE TABLE", "over_column"),
        ]

        formatted = self.checker.format_check_results(mock_results, _("表名"))

        self.assertEqual(len(formatted), 2)
        self.assertIsInstance(formatted[0], KeywordCheckResult)
        self.assertEqual(formatted[0].schema_name, "test_db")
        self.assertEqual(formatted[0].object_name, "except_table")

    def test_check_keyword_conflict_type(self):
        """测试关键字冲突类型检查"""
        # 测试保留关键字
        result = self.checker.check_keyword_conflict_type("SELECT")
        self.assertTrue(result["is_reserved"])
        self.assertEqual(result["conflict_level"], "high")

        # 测试非关键字
        result = self.checker.check_keyword_conflict_type("custom_name")
        self.assertEqual(result["conflict_level"], "none")

    def test_generate_upgrade_check_report(self):
        """测试升级检查报告生成"""
        # 模拟检查结果
        mock_results = {
            TABLE_CHECK: [
                KeywordCheckResult(
                    schema_name="test_db",
                    object_name="except_table",
                    object_type="BASE TABLE",
                    conflict_keyword="except_table",
                    suggested_fix=_("重命名表"),
                )
            ],
            COLUMN_CHECK: [],
        }

        report = self.checker.generate_upgrade_check_report(
            SpiderVersion.TSPIDER_1X, SpiderVersion.TSPIDER_3X, mock_results
        )

        self.assertIn("upgrade_path", report)
        self.assertIn("keywords_info", report)
        self.assertIn("conflict_summary", report)
        self.assertIn("recommendations", report)
        self.assertEqual(report["conflict_summary"]["total_conflicts"], 1)


class TestConvenienceFunctions(TestCase):
    """便捷函数测试类"""

    def test_check_spider_upgrade_keywords(self):
        """测试关键字检查便捷函数"""
        # 测试有效版本
        result = check_spider_upgrade_keywords("5.5.24-tspider-1.15-log", "10.3.7-MariaDB-tspider-3.7.11-log")
        self.assertTrue(result["compatible"])
        self.assertTrue(result["keywords_count"] > 0)

        # 测试无效源版本
        result = check_spider_upgrade_keywords("invalid-version", "10.3.7-MariaDB-tspider-3.7.11-log")
        self.assertFalse(result["compatible"])
        self.assertIn(_("无法识别源版本"), result["message"])

        # 测试无效目标版本
        result = check_spider_upgrade_keywords("5.5.24-tspider-1.15-log", "invalid-version")
        self.assertFalse(result["compatible"])
        self.assertIn(_("无法识别目标版本"), result["message"])

    def test_generate_upgrade_check_sqls(self):
        """测试SQL语句生成便捷函数"""
        # 测试有效版本
        check_sqls = generate_upgrade_check_sqls(
            "5.5.24-tspider-1.15-log", "10.3.7-MariaDB-tspider-3.7.11-log", schemas=["test_db"]
        )

        self.assertIn(TABLE_CHECK, check_sqls)
        self.assertIn(COLUMN_CHECK, check_sqls)
        self.assertIn("test_db", check_sqls[TABLE_CHECK])

        # 测试无效版本
        with self.assertRaises(ValueError):
            generate_upgrade_check_sqls("invalid-version", "10.3.7-MariaDB-tspider-3.7.11-log")

    def test_check_specific_keywords_conflict(self):
        """测试特定关键字冲突检查便捷函数"""
        keywords = ["SELECT", "custom_name", "EXCEPT"]
        result = check_specific_keywords_conflict(keywords)

        self.assertEqual(len(result), 3)
        self.assertIn("SELECT", result)
        self.assertIn("custom_name", result)
        self.assertIn("EXCEPT", result)

        # 检查结果结构
        for keyword, info in result.items():
            self.assertIn("keyword", info)
            self.assertIn("is_mariadb_keyword", info)
            self.assertIn("is_reserved", info)
            self.assertIn("conflict_level", info)

    def test_get_version_specific_keywords(self):
        """测试获取版本特定关键字便捷函数"""
        # 测试有效版本
        result = get_version_specific_keywords("10.3.7-MariaDB-tspider-3.7.11-log")
        self.assertTrue(result["success"])
        self.assertEqual(result["version"], "3.x")
        self.assertIsInstance(result["keywords"], list)

        # 测试无效版本
        result = get_version_specific_keywords("invalid-version")
        self.assertFalse(result["success"])
        self.assertIn(_("无法识别版本"), result["message"])


class SpiderUpgradeCheckerUsageExample:
    """Spider升级检查器使用示例"""

    @staticmethod
    def example_basic_usage():
        """基本使用示例"""
        print(_("=== Spider版本升级检查器基本使用示例 ==="))

        # 创建检查器
        checker = create_spider_upgrade_checker()

        # 解析版本
        from_version_str = "5.5.24-tspider-1.15-log"
        to_version_str = "10.3.7-MariaDB-tspider-3.7.11-log"

        from_version = checker.parse_version_string(from_version_str)
        to_version = checker.parse_version_string(to_version_str)

        print(f"{_('源版本')}: {from_version_str} -> {from_version.value}")
        print(f"{_('目标版本')}: {to_version_str} -> {to_version.value}")

        # 检查兼容性
        compatibility = checker.check_upgrade_compatibility(from_version, to_version)
        print(f"{_('兼容性检查')}: {compatibility}")

        # 获取需要检查的关键字
        keywords = checker.get_upgrade_keywords(from_version, to_version)
        print(f"{_('需要检查的关键字')} ({len(keywords)}): {keywords}")

    @staticmethod
    def example_sql_generation():
        """SQL生成示例"""
        print(f"\n{_('=== SQL生成示例 ===')}")

        checker = create_spider_upgrade_checker()

        # 生成所有检查SQL语句
        check_sqls = checker.generate_all_check_sqls(
            SpiderVersion.TSPIDER_3X, SpiderVersion.TSPIDER_4X, schemas=["business_db", "config_db"]
        )

        for check_type, sql in check_sqls.items():
            print(f"\n{_('检查类型')}: {check_type}")
            print(f"SQL: {sql}")

    @staticmethod
    def example_convenience_functions():
        """便捷函数使用示例"""
        print(f"\n{_('=== 便捷函数使用示例 ===')}")

        # 使用便捷函数检查兼容性
        result = check_spider_upgrade_keywords("10.3.7-MariaDB-tspider-3.7.11-log", "11.4.2-MariaDB-tspider-4.0.3-log")
        print(f"{_('便捷函数兼容性检查')}: {result}")

        # 使用便捷函数生成SQL语句
        try:
            check_sqls = generate_upgrade_check_sqls(
                "10.3.7-MariaDB-tspider-3.7.11-log", "11.4.2-MariaDB-tspider-4.0.3-log", schemas=["test_db"]
            )
            print(f"{_('生成的SQL数量')}: {len(check_sqls)}")
        except ValueError as e:
            print(f"{_('错误')}: {e}")

    @staticmethod
    def example_mock_database_check():
        """模拟数据库检查示例"""
        print(f"\n{_('=== 模拟数据库检查示例 ===')}")

        checker = create_spider_upgrade_checker()

        # 模拟数据库查询结果
        mock_table_results = [("business_db", "except", "BASE TABLE", None), ("config_db", "over", "BASE TABLE", None)]

        mock_column_results = [
            ("business_db", "user_table", "BASE TABLE", "recursive"),
            ("business_db", "order_table", "BASE TABLE", "returning"),
        ]

        # 格式化结果
        table_conflicts = checker.format_check_results(mock_table_results, _("表名"))
        column_conflicts = checker.format_check_results(mock_column_results, _("列名"))

        print(f"{_('表名冲突')} ({len(table_conflicts)}):")
        for conflict in table_conflicts:
            print(f"  - {conflict.schema_name}.{conflict.object_name}: {conflict.suggested_fix}")

        print(f"{_('列名冲突')} ({len(column_conflicts)}):")
        for conflict in column_conflicts:
            print(
                f"  - {conflict.schema_name}.{conflict.object_name}.{conflict.column_name}: {conflict.suggested_fix}"
            )


if __name__ == "__main__":
    # 运行使用示例
    example = SpiderUpgradeCheckerUsageExample()
    example.example_basic_usage()
    example.example_sql_generation()
    example.example_convenience_functions()
    example.example_mock_database_check()

    # 运行单元测试
    print(f"\n{_('=== 运行单元测试 ===')}")
    unittest.main(verbosity=2)
