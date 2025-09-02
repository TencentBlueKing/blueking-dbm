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
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple, Union

from django.utils.translation import gettext as _

from backend.flow.consts import SYSTEM_DBS
from backend.flow.utils.mysql.mysql_version_parse import tspider_version_parse
from backend.flow.utils.spider.spider_check_constants import (
    COLUMN_CHECK,
    ROUTINE_CHECK,
    TABLE_CHECK,
    TRIGGER_CHECK,
    VIEW_CHECK,
)
from backend.flow.utils.spider.spider_keywords_constants import (
    MARIADB_10_3_7_NEW_RESERVED_KEYWORDS,
    MARIADB_11_4_2_NEW_RESERVED_KEYWORDS,
    is_mariadb_keyword,
    is_reserved_keyword,
)

logger = logging.getLogger("flow")

"""
Spider跨版本升级关键字检查组件

本组件用于检查Spider数据库跨版本升级时可能出现的关键字冲突问题。
支持从tspider1.x到tspider3.x，以及从tspider3.x到tspider4.x的升级检查。

版本映射:
- tspider1.x: percona-server 5.5.24 (5.5.24-tspider-1.15-log)
- tspider3.x: MariaDB 10.3.7 (10.3.7-MariaDB-tspider-3.7.11-log)
- tspider4.x: MariaDB 11.4.2 (11.4.2-MariaDB-tspider-4.0.3-log)
"""


class SpiderVersion(Enum):
    """Spider版本枚举."""

    TSPIDER_1X = "1.x"
    TSPIDER_3X = "3.x"
    TSPIDER_4X = "4.x"


@dataclass
class VersionInfo:
    """版本信息数据类."""

    version: SpiderVersion
    base_version: str
    example_version: str
    description: str


@dataclass
class KeywordCheckResult:
    """关键字检查结果数据类."""

    schema_name: str
    object_name: str
    object_type: str
    column_name: Optional[str] = None
    conflict_keyword: str = ""
    suggested_fix: str = ""


class SpiderVersionUpgradeChecker:
    """Spider跨版本升级关键字检查器."""

    # 版本映射信息
    VERSION_MAPPING: Dict[SpiderVersion, VersionInfo] = {
        SpiderVersion.TSPIDER_1X: VersionInfo(
            version=SpiderVersion.TSPIDER_1X,
            base_version="percona-server 5.5.24",
            example_version="5.5.24-tspider-1.15-log",
            description="TSpider 1.x based on Percona Server 5.5",
        ),
        SpiderVersion.TSPIDER_3X: VersionInfo(
            version=SpiderVersion.TSPIDER_3X,
            base_version="MariaDB 10.3.7",
            example_version="10.3.7-MariaDB-tspider-3.7.11-log",
            description="TSpider 3.x based on MariaDB 10.3.7",
        ),
        SpiderVersion.TSPIDER_4X: VersionInfo(
            version=SpiderVersion.TSPIDER_4X,
            base_version="MariaDB 11.4.2",
            example_version="11.4.2-MariaDB-tspider-4.0.3-log",
            description="TSpider 4.x based on MariaDB 11.4.2",
        ),
    }

    # 1.x -> 3.x 升级时新增的关键字 (使用现有常量)
    @property
    def KEYWORDS_1X_TO_3X(self) -> List[str]:
        """从tspider1.x升级到3.x时需要检查的关键字."""
        return MARIADB_10_3_7_NEW_RESERVED_KEYWORDS

    # 3.x -> 4.x 升级时新增的关键字 (使用现有常量)
    @property
    def KEYWORDS_3X_TO_4X(self) -> List[str]:
        """从tspider3.x升级到4.x时需要检查的关键字."""
        return MARIADB_11_4_2_NEW_RESERVED_KEYWORDS

    def __init__(self):
        """初始化检查器."""
        # 构建版本升级路径与对应关键字的映射关系
        # 支持的升级路径:
        # - 1.x -> 3.x: 检查MariaDB 10.3.7新增的关键字
        # - 3.x -> 4.x: 检查MariaDB 11.4.2新增的关键字
        # - 1.x -> 4.x: 检查两个版本累计新增的所有关键字
        self._version_keywords_map = {
            (SpiderVersion.TSPIDER_1X, SpiderVersion.TSPIDER_3X): self.KEYWORDS_1X_TO_3X,
            (SpiderVersion.TSPIDER_3X, SpiderVersion.TSPIDER_4X): self.KEYWORDS_3X_TO_4X,
            (SpiderVersion.TSPIDER_1X, SpiderVersion.TSPIDER_4X): (self.KEYWORDS_1X_TO_3X + self.KEYWORDS_3X_TO_4X),
        }

    def get_version_info(self, version: SpiderVersion) -> VersionInfo:
        """
        获取版本信息.

        Args:
            version: Spider版本

        Returns:
            VersionInfo: 版本信息对象
        """
        return self.VERSION_MAPPING[version]

    def get_upgrade_keywords(self, from_version: SpiderVersion, to_version: SpiderVersion) -> List[str]:
        """
        获取升级时需要检查的关键字列表.

        Args:
            from_version: 源版本
            to_version: 目标版本

        Returns:
            List[str]: 需要检查的关键字列表

        Raises:
            ValueError: 不支持的版本升级路径
        """
        upgrade_path = (from_version, to_version)
        if upgrade_path not in self._version_keywords_map:
            raise ValueError(_("不支持的升级路径: {} -> {}").format(from_version.value, to_version.value))

        return self._version_keywords_map[upgrade_path]

    def parse_version_string(self, version_string: str) -> Optional[SpiderVersion]:
        """
        解析版本字符串，识别Spider版本.

        复用现有的版本解析方法

        Args:
            version_string: 版本字符串，如 "5.5.24-tspider-1.15-log"

        Returns:
            Optional[SpiderVersion]: 识别的版本，无法识别时返回None
        """
        logger.info(_("开始解析Spider版本字符串: {}").format(version_string))

        try:
            # 使用现有的tspider版本解析方法，将版本字符串转换为数字
            # 例如: "3.7.11" -> 3007011
            tspider_version_num = tspider_version_parse(version_string)
            if tspider_version_num == 0:
                logger.warning(_("无法解析TSpider版本号: {}").format(version_string))
                return None

            # 根据主版本号判断Spider版本
            # 版本号格式: MAJOR * 1000000 + MINOR * 1000 + PATCH
            if tspider_version_num >= 4000000:  # 4.x.x (4000000及以上)
                return SpiderVersion.TSPIDER_4X
            elif tspider_version_num >= 3000000:  # 3.x.x (3000000-3999999)
                return SpiderVersion.TSPIDER_3X
            elif tspider_version_num >= 1000000:  # 1.x.x (1000000-2999999)
                return SpiderVersion.TSPIDER_1X
            else:
                logger.warning(_("未知的Spider主版本号: {}").format(tspider_version_num))
                return None

        except Exception as e:
            logger.error(_("解析Spider版本字符串时发生异常: {}").format(str(e)))
            return None

    def generate_table_check_sql(self, keywords: List[str], schemas: Optional[List[str]] = None) -> str:
        """
        生成检查表名的SQL语句.

        Args:
            keywords: 要检查的关键字列表
            schemas: 要检查的schema列表，为None时检查所有schema

        Returns:
            str: 检查表名的SQL语句
        """
        # 将关键字列表转换为SQL IN子句格式
        keywords_str = "', '".join(keywords)
        # 排除系统数据库，避免检查系统表
        system_dbs_str = "', '".join(SYSTEM_DBS)

        # 构建基础SQL查询，检查表名是否与关键字冲突
        # 使用UPPER()函数进行大小写不敏感的比较
        base_sql = f"""
        SELECT
            TABLE_SCHEMA,
            TABLE_NAME,
            TABLE_TYPE,
            '{_("表名")}' as CONFLICT_TYPE
        FROM information_schema.tables
        WHERE UPPER(table_name) IN ('{keywords_str}')
        AND TABLE_SCHEMA NOT IN ('{system_dbs_str}')
        """

        # 如果指定了特定的schema，添加过滤条件
        if schemas:
            schemas_str = "', '".join(schemas)
            base_sql += f" AND TABLE_SCHEMA IN ('{schemas_str}')"

        return base_sql.strip()

    def generate_column_check_sql(self, keywords: List[str], schemas: Optional[List[str]] = None) -> str:
        """
        生成检查列名的SQL语句.

        Args:
            keywords: 要检查的关键字列表
            schemas: 要检查的schema列表，为None时检查所有schema

        Returns:
            str: 检查列名的SQL语句
        """
        keywords_str = "', '".join(keywords)
        system_dbs_str = "', '".join(SYSTEM_DBS)
        base_sql = f"""
        SELECT
            TABLE_SCHEMA,
            TABLE_NAME,
            COLUMN_NAME,
            '{_("列名")}' as CONFLICT_TYPE
        FROM information_schema.columns
        WHERE UPPER(column_name) IN ('{keywords_str}')
        AND TABLE_SCHEMA NOT IN ('{system_dbs_str}')
        """

        if schemas:
            schemas_str = "', '".join(schemas)
            base_sql += f" AND TABLE_SCHEMA IN ('{schemas_str}')"

        return base_sql.strip()

    def generate_routine_check_sql(self, keywords: List[str], schemas: Optional[List[str]] = None) -> str:
        """
        生成检查函数/存储过程名的SQL语句.

        Args:
            keywords: 要检查的关键字列表
            schemas: 要检查的schema列表，为None时检查所有schema

        Returns:
            str: 检查函数/存储过程名的SQL语句
        """
        keywords_str = "', '".join(keywords)
        system_dbs_str = "', '".join(SYSTEM_DBS)
        base_sql = f"""
        SELECT
            ROUTINE_SCHEMA,
            ROUTINE_NAME,
            ROUTINE_TYPE,
            '{_("函数/存储过程名")}' as CONFLICT_TYPE
        FROM information_schema.routines
        WHERE UPPER(routine_name) IN ('{keywords_str}')
        AND ROUTINE_SCHEMA NOT IN ('{system_dbs_str}')
        """

        if schemas:
            schemas_str = "', '".join(schemas)
            base_sql += f" AND ROUTINE_SCHEMA IN ('{schemas_str}')"

        return base_sql.strip()

    def generate_trigger_check_sql(self, keywords: List[str], schemas: Optional[List[str]] = None) -> str:
        """
        生成检查触发器名的SQL语句.

        Args:
            keywords: 要检查的关键字列表
            schemas: 要检查的schema列表，为None时检查所有schema

        Returns:
            str: 检查触发器名的SQL语句
        """
        keywords_str = "', '".join(keywords)
        system_dbs_str = "', '".join(SYSTEM_DBS)
        base_sql = f"""
        SELECT
            TRIGGER_SCHEMA,
            TRIGGER_NAME,
            '{_("触发器")}' as TABLE_TYPE,
            '{_("触发器名")}' as CONFLICT_TYPE
        FROM information_schema.triggers
        WHERE UPPER(TRIGGER_NAME) IN ('{keywords_str}')
        AND TRIGGER_SCHEMA NOT IN ('{system_dbs_str}')
        """

        if schemas:
            schemas_str = "', '".join(schemas)
            base_sql += f" AND TRIGGER_SCHEMA IN ('{schemas_str}')"

        return base_sql.strip()

    def generate_view_check_sql(self, keywords: List[str], schemas: Optional[List[str]] = None) -> str:
        """
        生成检查视图名的SQL语句.

        Args:
            keywords: 要检查的关键字列表
            schemas: 要检查的schema列表，为None时检查所有schema

        Returns:
            str: 检查视图名的SQL语句
        """
        keywords_str = "', '".join(keywords)
        system_dbs_str = "', '".join(SYSTEM_DBS)
        base_sql = f"""
        SELECT
            TABLE_SCHEMA,
            TABLE_NAME,
            DEFINER,
            '{_("视图名")}' as CONFLICT_TYPE
        FROM information_schema.VIEWS
        WHERE UPPER(TABLE_NAME) IN ('{keywords_str}')
        AND TABLE_SCHEMA NOT IN ('{system_dbs_str}')
        """

        if schemas:
            schemas_str = "', '".join(schemas)
            base_sql += f" AND TABLE_SCHEMA IN ('{schemas_str}')"

        return base_sql.strip()

    def generate_all_check_sqls(
        self, from_version: SpiderVersion, to_version: SpiderVersion, schemas: Optional[List[str]] = None
    ) -> Dict[str, str]:
        """
        生成所有检查SQL语句.

        Args:
            from_version: 源版本
            to_version: 目标版本
            schemas: 要检查的schema列表，为None时检查所有schema

        Returns:
            Dict[str, str]: 包含所有检查SQL的字典
        """
        keywords = self.get_upgrade_keywords(from_version, to_version)

        return {
            TABLE_CHECK: self.generate_table_check_sql(keywords, schemas),
            COLUMN_CHECK: self.generate_column_check_sql(keywords, schemas),
            ROUTINE_CHECK: self.generate_routine_check_sql(keywords, schemas),
            TRIGGER_CHECK: self.generate_trigger_check_sql(keywords, schemas),
            VIEW_CHECK: self.generate_view_check_sql(keywords, schemas),
        }

    def check_keyword_conflict_type(self, keyword: str) -> Dict[str, Union[bool, str]]:
        """
        检查关键字的冲突类型.

        Args:
            keyword: 要检查的关键字

        Returns:
            Dict: 包含冲突类型信息的字典
        """
        logger.info(_("检查关键字冲突类型: {}").format(keyword))

        # 初始化结果字典，包含关键字基本信息
        result = {
            "keyword": keyword,
            "is_mariadb_keyword": is_mariadb_keyword(keyword),
            "is_reserved": is_reserved_keyword(keyword),
            "conflict_level": "none",
            "description": "",
        }

        # 根据关键字类型确定冲突级别和处理建议
        # 优先级: 保留关键字 > MariaDB关键字 > 非关键字
        if is_reserved_keyword(keyword):
            # 保留关键字: 最高优先级，必须处理
            result["conflict_level"] = "high"
            result["description"] = _("保留关键字，必须使用反引号包裹")
        elif is_mariadb_keyword(keyword):
            # MariaDB关键字: 中等优先级，建议处理
            result["conflict_level"] = "medium"
            result["description"] = _("MariaDB关键字，建议使用反引号包裹")
        else:
            # 非关键字: 无冲突
            result["conflict_level"] = "none"
            result["description"] = _("非关键字，无冲突")

        return result

    def suggest_fix_for_conflict(self, object_name: str, object_type: str, conflict_keyword: str) -> str:
        """
        为关键字冲突提供修复建议.

        Args:
            object_name: 对象名称
            object_type: 对象类型
            conflict_keyword: 冲突的关键字

        Returns:
            str: 修复建议
        """
        logger.info(_("为关键字冲突提供修复建议: {} (类型: {})").format(conflict_keyword, object_type))

        # 检查关键字冲突类型，获取冲突级别
        conflict_info = self.check_keyword_conflict_type(conflict_keyword)
        # 生成反引号包裹的对象名，用于SQL中的安全引用
        escaped_name = f"`{object_name}`"

        # 根据冲突级别设置优先级标识
        # 高优先级: 保留关键字，必须处理
        # 中优先级: MariaDB关键字，建议处理
        # 低优先级: 其他情况
        if conflict_info["conflict_level"] == "high":
            priority_msg = _("【高优先级】")
        elif conflict_info["conflict_level"] == "medium":
            priority_msg = _("【中优先级】")
        else:
            priority_msg = _("【低优先级】")

        # 针对不同对象类型提供具体的修复建议
        # 每种对象类型都提供两种解决方案:
        # 1) 重命名对象（推荐，彻底解决冲突）
        # 2) 使用反引号包裹（临时方案，需要修改所有引用）
        suggestions = {
            _("表名"): _("{} 表名 '{}' 与关键字冲突。建议: 1) 重命名为 '{}'; 2) 使用反引号: {}").format(
                priority_msg, object_name, f"{object_name}_table", escaped_name
            ),
            _("列名"): _("{} 列名 '{}' 与关键字冲突。建议: 1) 重命名为 '{}'; 2) 使用反引号: {}").format(
                priority_msg, object_name, f"{object_name}_col", escaped_name
            ),
            _("函数/存储过程名"): _("{} 函数/存储过程名 '{}' 与关键字冲突。建议: 1) 重命名为 '{}'; 2) 使用反引号: {}").format(
                priority_msg, object_name, f"{object_name}_func", escaped_name
            ),
            _("触发器名"): _("{} 触发器名 '{}' 与关键字冲突。建议: 1) 重命名为 '{}'; 2) 使用反引号: {}").format(
                priority_msg, object_name, f"{object_name}_trigger", escaped_name
            ),
            _("视图名"): _("{} 视图名 '{}' 与关键字冲突。建议: 1) 重命名为 '{}'; 2) 使用反引号: {}").format(
                priority_msg, object_name, f"{object_name}_view", escaped_name
            ),
        }

        # 返回对应对象类型的建议，如果类型未匹配则返回通用建议
        return suggestions.get(object_type, _("{} 使用反引号包裹对象名: {}").format(priority_msg, escaped_name))

    def check_upgrade_compatibility(
        self, from_version: SpiderVersion, to_version: SpiderVersion
    ) -> Dict[str, Union[bool, str, List[str]]]:
        """
        检查版本升级兼容性.

        Args:
            from_version: 源版本
            to_version: 目标版本

        Returns:
            Dict: 兼容性检查结果
        """
        try:
            keywords = self.get_upgrade_keywords(from_version, to_version)
            from_info = self.get_version_info(from_version)
            to_info = self.get_version_info(to_version)

            return {
                "compatible": True,
                "from_version": from_info.description,
                "to_version": to_info.description,
                "keywords_to_check": keywords,
                "keywords_count": len(keywords),
                "message": _("版本升级路径支持，需要检查 {} 个关键字冲突").format(len(keywords)),
            }
        except ValueError as e:
            return {
                "compatible": False,
                "message": str(e),
                "keywords_to_check": [],
                "keywords_count": 0,
            }

    def format_check_results(
        self, results: List[Tuple[str, str, str, Optional[str]]], conflict_type: str
    ) -> List[KeywordCheckResult]:
        """
        格式化检查结果.

        Args:
            results: 数据库查询结果
            conflict_type: 冲突类型

        Returns:
            List[KeywordCheckResult]: 格式化后的检查结果
        """
        logger.info(_("格式化检查结果，冲突类型: {}，结果数量: {}").format(conflict_type, len(results)))

        formatted_results = []

        for result in results:
            if len(result) >= 3:
                schema_name = result[0]
                object_name = result[1]
                object_type = result[2]
                column_name = result[3] if len(result) > 3 else None

                # 确定冲突的关键字
                conflict_keyword = object_name if not column_name else column_name

                # 生成修复建议
                suggested_fix = self.suggest_fix_for_conflict(conflict_keyword, conflict_type, conflict_keyword)

                formatted_results.append(
                    KeywordCheckResult(
                        schema_name=schema_name,
                        object_name=object_name,
                        object_type=object_type,
                        column_name=column_name,
                        conflict_keyword=conflict_keyword,
                        suggested_fix=suggested_fix,
                    )
                )

        logger.info(_("格式化完成，生成 {} 个检查结果").format(len(formatted_results)))
        return formatted_results

    def generate_upgrade_check_report(
        self,
        from_version: SpiderVersion,
        to_version: SpiderVersion,
        check_results: Dict[str, List[KeywordCheckResult]],
    ) -> Dict[str, Union[str, int, List, Dict]]:
        """
        生成升级检查报告.

        Args:
            from_version: 源版本
            to_version: 目标版本
            check_results: 检查结果字典

        Returns:
            Dict: 升级检查报告
        """
        logger.info(_("生成升级检查报告: {} -> {}").format(from_version.value, to_version.value))

        # 获取版本信息和需要检查的关键字
        from_info = self.get_version_info(from_version)
        to_info = self.get_version_info(to_version)
        keywords = self.get_upgrade_keywords(from_version, to_version)

        # 统计各类冲突的数量
        # total_conflicts: 总冲突数
        # high_priority_conflicts: 高优先级冲突数（保留关键字）
        # medium_priority_conflicts: 中优先级冲突数（MariaDB关键字）
        total_conflicts = sum(len(results) for results in check_results.values())
        high_priority_conflicts = 0
        medium_priority_conflicts = 0

        # 按检查类型统计冲突数量，并计算优先级分布
        conflict_summary = {}
        for check_type, results in check_results.items():
            conflict_summary[check_type] = len(results)
            # 遍历每个冲突结果，统计优先级分布
            for result in results:
                conflict_info = self.check_keyword_conflict_type(result.conflict_keyword)
                if conflict_info["conflict_level"] == "high":
                    high_priority_conflicts += 1
                elif conflict_info["conflict_level"] == "medium":
                    medium_priority_conflicts += 1

        # 生成报告
        report = {
            "upgrade_path": {
                "from_version": from_info.description,
                "to_version": to_info.description,
                "from_example": from_info.example_version,
                "to_example": to_info.example_version,
            },
            "keywords_info": {"total_keywords_checked": len(keywords), "keywords_list": keywords},
            "conflict_summary": {
                "total_conflicts": total_conflicts,
                "high_priority_conflicts": high_priority_conflicts,
                "medium_priority_conflicts": medium_priority_conflicts,
                "low_priority_conflicts": total_conflicts - high_priority_conflicts - medium_priority_conflicts,
                "by_type": conflict_summary,
            },
            "detailed_results": check_results,
            "recommendations": self._generate_upgrade_recommendations(
                total_conflicts, high_priority_conflicts, medium_priority_conflicts
            ),
            "generated_at": _("报告生成时间"),
            "status": "completed" if total_conflicts == 0 else "conflicts_found",
        }

        logger.info(_("升级检查报告生成完成，发现 {} 个冲突").format(total_conflicts))
        return report

    def _generate_upgrade_recommendations(
        self, total_conflicts: int, high_priority: int, medium_priority: int
    ) -> List[str]:
        """
        生成升级建议.

        Args:
            total_conflicts: 总冲突数
            high_priority: 高优先级冲突数
            medium_priority: 中优先级冲突数

        Returns:
            List[str]: 升级建议列表
        """
        recommendations = []

        if total_conflicts == 0:
            recommendations.append(_("✅ 未发现关键字冲突，可以安全升级"))
        else:
            if high_priority > 0:
                recommendations.append(_("🔴 发现 {} 个高优先级冲突，必须在升级前解决").format(high_priority))
                recommendations.append(_("   - 高优先级冲突涉及保留关键字，会导致升级失败"))
                recommendations.append(_("   - 建议重命名相关对象或使用反引号包裹"))

            if medium_priority > 0:
                recommendations.append(_("🟡 发现 {} 个中优先级冲突，建议在升级前解决").format(medium_priority))
                recommendations.append(_("   - 中优先级冲突可能影响某些功能"))
                recommendations.append(_("   - 建议使用反引号包裹相关对象名"))

            recommendations.append(_("📋 升级前检查清单:"))
            recommendations.append(_("   1. 备份所有相关数据库"))
            recommendations.append(_("   2. 在测试环境中验证修复方案"))
            recommendations.append(_("   3. 准备回滚计划"))
            recommendations.append(_("   4. 通知相关应用程序开发团队"))

        return recommendations


def create_spider_upgrade_checker() -> SpiderVersionUpgradeChecker:
    """
    创建Spider版本升级检查器实例.

    Returns:
        SpiderVersionUpgradeChecker: 检查器实例
    """
    return SpiderVersionUpgradeChecker()


# 便捷函数
def check_spider_upgrade_keywords(
    from_version_str: str, to_version_str: str
) -> Dict[str, Union[bool, str, List[str]]]:
    """
    检查Spider版本升级关键字兼容性的便捷函数.

    这是一个高级封装函数，用于简化版本升级兼容性检查的调用过程。
    它会自动解析版本字符串，并返回详细的兼容性检查结果。

    Args:
        from_version_str: 源版本字符串，如 "5.5.24-tspider-1.15-log"
        to_version_str: 目标版本字符串，如 "10.3.7-MariaDB-tspider-3.7.11-log"

    Returns:
        Dict: 兼容性检查结果，包含以下字段:
            - compatible: 是否兼容
            - message: 检查结果消息
            - keywords_to_check: 需要检查的关键字列表
            - keywords_count: 关键字数量
    """
    logger.info(_("开始检查Spider版本升级兼容性: {} -> {}").format(from_version_str, to_version_str))

    # 创建检查器实例
    checker = create_spider_upgrade_checker()

    # 解析源版本和目标版本字符串
    from_version = checker.parse_version_string(from_version_str)
    to_version = checker.parse_version_string(to_version_str)

    # 验证源版本解析结果
    if not from_version:
        logger.error(_("无法识别源版本: {}").format(from_version_str))
        return {
            "compatible": False,
            "message": _("无法识别源版本: {}").format(from_version_str),
            "keywords_to_check": [],
            "keywords_count": 0,
        }

    # 验证目标版本解析结果
    if not to_version:
        logger.error(_("无法识别目标版本: {}").format(to_version_str))
        return {
            "compatible": False,
            "message": _("无法识别目标版本: {}").format(to_version_str),
            "keywords_to_check": [],
            "keywords_count": 0,
        }

    # 执行兼容性检查并返回结果
    result = checker.check_upgrade_compatibility(from_version, to_version)
    logger.info(_("版本升级兼容性检查完成: {}").format(result.get("message", "")))
    return result


def check_specific_keywords_conflict(keywords: List[str]) -> Dict[str, Dict[str, Union[bool, str]]]:
    """
    检查特定关键字的冲突情况.

    Args:
        keywords: 要检查的关键字列表

    Returns:
        Dict: 每个关键字的冲突检查结果
    """
    logger.info(_("开始检查特定关键字冲突，关键字数量: {}").format(len(keywords)))

    checker = create_spider_upgrade_checker()
    results = {}

    for keyword in keywords:
        results[keyword] = checker.check_keyword_conflict_type(keyword)

    logger.info(_("特定关键字冲突检查完成"))
    return results


def get_version_specific_keywords(version_str: str) -> Dict[str, Union[bool, str, List[str]]]:
    """
    获取特定版本的关键字信息.

    Args:
        version_str: 版本字符串

    Returns:
        Dict: 版本关键字信息
    """
    logger.info(_("获取版本特定关键字信息: {}").format(version_str))

    checker = create_spider_upgrade_checker()
    version = checker.parse_version_string(version_str)

    if not version:
        logger.error(_("无法识别版本: {}").format(version_str))
        return {
            "success": False,
            "message": _("无法识别版本: {}").format(version_str),
            "keywords": [],
        }

    version_info = checker.get_version_info(version)

    # 根据版本获取相关关键字
    if version == SpiderVersion.TSPIDER_3X:
        keywords = checker.KEYWORDS_1X_TO_3X
    elif version == SpiderVersion.TSPIDER_4X:
        keywords = checker.KEYWORDS_3X_TO_4X
    else:
        keywords = []

    result = {
        "success": True,
        "version": version.value,
        "description": version_info.description,
        "example_version": version_info.example_version,
        "keywords": keywords,
        "keywords_count": len(keywords),
    }

    logger.info(_("版本关键字信息获取完成，关键字数量: {}").format(len(keywords)))
    return result


def generate_upgrade_check_sqls(
    from_version_str: str, to_version_str: str, schemas: Optional[List[str]] = None
) -> Dict[str, str]:
    """
    生成版本升级检查SQL的便捷函数.

    Args:
        from_version_str: 源版本字符串
        to_version_str: 目标版本字符串
        schemas: 要检查的schema列表

    Returns:
        Dict[str, str]: 包含所有检查SQL的字典

    Raises:
        ValueError: 版本解析失败或不支持的升级路径
    """
    checker = create_spider_upgrade_checker()

    from_version = checker.parse_version_string(from_version_str)
    to_version = checker.parse_version_string(to_version_str)

    if not from_version:
        raise ValueError(_("无法识别源版本: {}").format(from_version_str))

    if not to_version:
        raise ValueError(_("无法识别目标版本: {}").format(to_version_str))

    return checker.generate_all_check_sqls(from_version, to_version, schemas)
