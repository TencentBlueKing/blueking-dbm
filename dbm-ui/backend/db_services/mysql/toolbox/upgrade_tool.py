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
from typing import Dict, List

from django.utils.translation import gettext as _

from backend.configuration.constants import DBType
from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster, ProxyInstance
from backend.db_package.models import Package
from backend.db_services.cmdb.biz import list_modules_by_biz
from backend.flow.consts import MediumEnum
from backend.flow.utils.mysql.common.mysql_cluster_info import get_version_and_charset
from backend.flow.utils.mysql.mysql_bk_config import get_mysql_version_and_charset
from backend.flow.utils.mysql.mysql_version_parse import (
    proxy_version_parse,
    spider_major_version_parse,
    tspider_version_parse,
)
from backend.flow.utils.spider.spider_bk_config import get_spider_version_and_charset

logger = logging.getLogger("root")


def _get_current_cluster_info(cluster_id: int) -> tuple:
    """
    获取当前集群的基本信息

    @param cluster_id: 集群ID
    @return: (cluster, current_spider_versions, current_db_version, current_charset)
    """
    cluster = Cluster.objects.get(id=cluster_id)

    # 获取当前集群的spider实例
    spiders = ProxyInstance.objects.filter(cluster=cluster)
    if not spiders.exists():
        logger.warning(_("集群 {} 没有找到spider实例").format(cluster_id))
        return None, [], None, None

    # 获取当前集群的spider版本
    current_spider_versions = []
    for spider in spiders:
        if spider.version:
            current_spider_versions.append(spider.version)

    if not current_spider_versions:
        logger.warning(_("集群 {} 的spider实例没有版本信息").format(cluster_id))
        return cluster, [], None, None

    # 获取当前集群的db版本和字符集
    try:
        current_charset, current_db_version = get_version_and_charset(
            cluster.bk_biz_id, cluster.db_module_id, cluster.cluster_type
        )
        logger.info(_("集群 {} 当前db版本: {}, 字符集: {}").format(cluster_id, current_db_version, current_charset))
    except Exception as e:
        logger.warning(_("获取集群 {} 的db版本失败: {}").format(cluster_id, e))
        try:
            # 尝试使用mysql_bk_config中的函数获取版本信息
            current_charset, current_db_version = get_mysql_version_and_charset(
                cluster.bk_biz_id, cluster.db_module_id, cluster.cluster_type
            )
            logger.info(
                _("从mysql_bk_config获取集群 {} 当前db版本: {}, 字符集: {}").format(
                    cluster_id, current_db_version, current_charset
                )
            )
        except Exception as e2:
            logger.warning(_("从mysql_bk_config获取集群 {} 的db版本失败: {}").format(cluster_id, e2))
            try:
                # 最后尝试从spider配置获取字符集
                current_charset, spider_version = get_spider_version_and_charset(
                    cluster.bk_biz_id, cluster.db_module_id
                )
                logger.info(
                    _("从spider配置获取集群 {} spider版本: {}, 字符集: {}").format(cluster_id, spider_version, current_charset)
                )
                # 由于无法获取db版本，设置为None
                current_db_version = None
            except Exception as e3:
                logger.error(_("无法获取集群 {} 的版本信息: {}").format(cluster_id, e3))
                return cluster, current_spider_versions, None, None

    return cluster, current_spider_versions, current_db_version, current_charset


def _parse_spider_version_to_num(spider_version: str) -> int:
    """
    解析spider版本号

    @param spider_version: spider版本字符串
    @return: 版本号数值
    """
    if spider_version.startswith("Spider-"):
        version_num = spider_version.replace("Spider-", "")
        # 根据版本号判断主版本
        version_mapping = {
            "1": "tspider-1.0.0",
            "3": "tspider-3.0.0",
            "3.5": "tspider-3.5.0",
            "3.6": "tspider-3.6.0",
            "3.7": "tspider-3.7.0",
            "3.8": "tspider-3.8.0",
            "4": "tspider-4.0.0",
        }

        if version_num in version_mapping:
            return tspider_version_parse(version_mapping[version_num])
        else:
            logger.warning(_("未知的spider版本格式: {}").format(spider_version))
            return 0
    else:
        # 如果是其他格式，尝试直接解析
        return tspider_version_parse(spider_version)


def _check_module_version_compatibility(module: Dict, current_db_version: str, current_charset: str) -> tuple:
    """
    检查模块版本兼容性

    @param module: 模块信息
    @param current_db_version: 当前db版本
    @param current_charset: 当前字符集
    @return: (spider_version, db_version, charset, is_compatible)
    """
    module_id = module.get("db_module_id")
    module_name = module.get("name", "")

    # 从模块配置中获取spider版本、db版本和字符集
    db_module_info = module.get("db_module_info", {})
    conf_items = db_module_info.get("conf_items", [])

    spider_version = None
    db_version = None
    charset = None

    for conf_item in conf_items:
        if conf_item.get("conf_name") == "spider_version":
            spider_version = conf_item.get("conf_value")
        elif conf_item.get("conf_name") == "db_version":
            db_version = conf_item.get("conf_value")
        elif conf_item.get("conf_name") == "charset":
            charset = conf_item.get("conf_value")

    if not spider_version:
        logger.debug(_("模块 {} ({}) 没有spider_version配置").format(module_id, module_name))
        return None, None, None, False

    if not db_version:
        logger.debug(_("模块 {} ({}) 没有db_version配置").format(module_id, module_name))
        return None, None, None, False

    # 检查db_version是否与当前集群一致
    if db_version != current_db_version:
        logger.debug(
            _("模块 {} ({}) db_version不匹配: 当前={}, 模块={}").format(module_id, module_name, current_db_version, db_version)
        )
        return spider_version, db_version, charset, False

    # 检查charset是否与当前集群一致
    if charset != current_charset:
        logger.debug(_("模块 {} ({}) charset不匹配: 当前={}, 模块={}").format(module_id, module_name, current_charset, charset))
        return spider_version, db_version, charset, False

    return spider_version, db_version, charset, True


def find_spider_packages_by_version_strategy(
    current_major_version: int,
    current_min_version: int,
    higher_major_version: bool = False,
    higher_sub_version: bool = False,
) -> List[Dict]:
    """
    根据版本策略查找spider包（新方法）

    @param current_major_version: 当前主版本号
    @param current_min_version: 当前最低版本号
    @param higher_major_version: 是否查找更高主版本的包，默认为False
    @param higher_sub_version: 是否查找同大版本但子版本更高的包，默认为False
    @return: 符合条件的包列表
    """
    try:
        # 获取所有可用的spider包
        packages = Package.objects.filter(pkg_type=MediumEnum.Spider, db_type=DBType.MySQL, enable=True).order_by(
            "-create_at"
        )

        if not packages.exists():
            logger.warning(_("没有找到可用的spider包"))
            return []

        available_packages = []

        for pkg in packages:
            # 使用现有的版本解析方法
            pkg_major_version_num, pkg_sub_version_num = spider_major_version_parse(pkg.name, has_prefix=True)

            if pkg_major_version_num == 0:
                logger.debug(_("无法解析包 {} 的版本信息").format(pkg.name))
                continue

            # 根据策略过滤包
            if higher_major_version:
                # 查找更高主版本的包
                if pkg_major_version_num > current_major_version:
                    available_packages.append(
                        {
                            "pkg_id": pkg.id,
                            "pkg_name": pkg.name,
                            "major_version": pkg_major_version_num,
                            "sub_version": pkg_sub_version_num,
                            "full_version": pkg_major_version_num + pkg_sub_version_num,
                        }
                    )
            elif higher_sub_version:
                # 查找同大版本但子版本更高的包
                if pkg_major_version_num == current_major_version and pkg_sub_version_num > current_min_version:
                    available_packages.append(
                        {
                            "pkg_id": pkg.id,
                            "pkg_name": pkg.name,
                            "major_version": pkg_major_version_num,
                            "sub_version": pkg_sub_version_num,
                            "full_version": pkg_major_version_num + pkg_sub_version_num,
                        }
                    )

        # 按版本号排序，版本高的在前
        available_packages.sort(key=lambda x: x["full_version"], reverse=True)

        logger.info(_("找到 {} 个符合条件的spider包").format(len(available_packages)))
        return available_packages

    except Exception as e:
        logger.error(_("查找spider包失败: {}").format(e))
        return []


def find_higher_spider_version_modules(cluster_id: int, module_list: List[Dict]) -> List[Dict]:
    """
    找出比当前集群spider版本更高的模块（同时保持db_version一致）

    @param cluster_id: 当前集群ID
    @param module_list: 模块列表，格式如list_modules_by_biz返回的数据
    @return: 比当前集群spider版本更高的模块列表
    """
    try:
        # 获取当前集群信息
        cluster, current_spider_versions, current_db_version, current_charset = _get_current_cluster_info(cluster_id)
        if not current_spider_versions:
            return []

        # 解析当前spider版本，取最高版本作为参考
        current_version_nums = []
        current_major_versions = []
        current_sub_versions = []
        for version in current_spider_versions:
            version_num = proxy_version_parse(version)
            if version_num > 0:
                current_version_nums.append(version_num)
                # 解析主版本号和子版本号
                major_version, sub_version = spider_major_version_parse(version, has_prefix=False)
                current_major_versions.append(major_version)
                current_sub_versions.append(sub_version)

        if not current_version_nums:
            logger.warning(_("集群 {} 的spider版本解析失败").format(cluster_id))
            return []

        # 取当前最低版本作为比较基准
        current_min_version = min(current_version_nums)
        current_major_version = min(current_major_versions)
        current_min_sub_version = min(current_sub_versions)
        logger.info(
            _("集群 {} 当前最低spider版本号: {}, 主版本号: {}, 最低子版本号: {}").format(
                cluster_id, current_min_version, current_major_version, current_min_sub_version
            )
        )

        # 遍历模块列表，找出spider版本更高的模块
        higher_version_modules = []

        for module in module_list:
            module_id = module.get("db_module_id")
            module_name = module.get("name", "")
            module_alias_name = module.get("alias_name", "")

            # 跳过当前集群所在的模块
            if module_id == cluster.db_module_id:
                continue

            # 检查模块版本兼容性
            spider_version, db_version, charset, is_compatible = _check_module_version_compatibility(
                module, current_db_version, current_charset
            )
            if not is_compatible:
                continue

            # 解析模块的spider版本
            try:
                module_version_num = _parse_spider_version_to_num(spider_version)
                if module_version_num == 0:
                    continue

                if module_version_num > current_min_version:
                    logger.info(
                        _("找到更高版本模块: {} (spider版本: {}, db版本: {}, 版本号: {})").format(
                            module_name, spider_version, db_version, module_version_num
                        )
                    )

                    # 获取模块主版本号
                    if spider_version.startswith("Spider-"):
                        version_num = spider_version.replace("Spider-", "")
                        version_major_mapping = {
                            "1": 1000000,
                            "3": 3000000,
                            "3.5": 3000000,  # 3.x系列
                            "3.6": 3000000,  # 3.x系列
                            "3.7": 3000000,  # 3.x系列
                            "3.8": 3000000,  # 3.x系列
                            "4": 4000000,
                        }
                        module_major_version = version_major_mapping.get(version_num, 0)
                    else:
                        module_major_version, *unused = spider_major_version_parse(spider_version, has_prefix=False)

                    # 根据模块的版本来过滤包（查找更高主版本的包）
                    module_pkg_list = _filter_packages_by_module_version_higher_major(
                        module_major_version,
                        current_major_version,
                        current_min_sub_version,
                        spider_version,
                        higher_major_version=True,
                        higher_sub_version=False,
                    )

                    higher_version_modules.append(
                        {
                            "db_module_id": module_id,
                            "db_module_name": module_name,
                            "module_alias_name": module_alias_name,
                            "charset": charset,
                            "spider_version": spider_version,
                            "db_version": db_version,
                            "spider_version_num": module_version_num,
                            "pkg_list": module_pkg_list,
                        }
                    )
                else:
                    logger.debug(
                        _("模块 {} spider版本 {} (版本号: {}) 不高于当前版本 {}").format(
                            module_name, spider_version, module_version_num, current_min_version
                        )
                    )

            except Exception as e:
                logger.warning(_("解析模块 {} 的spider版本失败: {}").format(module_id, e))
                continue

        # 按版本号排序，版本高的在前
        higher_version_modules.sort(key=lambda x: x["spider_version_num"], reverse=True)

        logger.info(_("找到 {} 个比当前集群spider版本更高的模块").format(len(higher_version_modules)))
        return higher_version_modules

    except Cluster.DoesNotExist:
        logger.error(_("集群 {} 不存在").format(cluster_id))
        return []
    except Exception as e:
        logger.error(_("查找更高版本模块时发生错误: {}").format(e))
        return []


def _filter_packages_by_module_version_higher_major(
    module_major_version: int,
    current_major_version: int,
    current_min_sub_version: int,
    spider_version: str,
    higher_major_version: bool = True,
    higher_sub_version: bool = False,
) -> List[Dict]:
    """
    根据模块的版本来过滤包

    @param module_major_version: 模块主版本号
    @param current_major_version: 当前集群主版本号
    @param current_min_sub_version: 当前集群最低子版本号
    @param spider_version: spider版本字符串
    @param higher_major_version: 是否查找更高主版本的包，默认为True
    @param higher_sub_version: 是否查找同大版本但子版本更高的包，默认为False
    @return: 符合条件的包列表
    """
    try:
        # 获取所有可用的spider包
        packages = Package.objects.filter(
            pkg_type=MediumEnum.Spider, db_type=DBType.MySQL, version=spider_version, enable=True
        ).order_by("-create_at")

        if not packages.exists():
            logger.warning(_("没有找到可用的spider包"))
            return []

        filtered_packages = []

        for pkg in packages:
            # 使用现有的版本解析方法
            pkg_major_version_num, pkg_sub_version_num = spider_major_version_parse(pkg.name, has_prefix=True)

            if pkg_major_version_num == 0:
                logger.debug(_("无法解析包 {} 的版本信息").format(pkg.name))
                continue

            # 根据策略过滤包
            is_version_match = False

            if higher_major_version:
                # 查找更高主版本的包
                if pkg_major_version_num > current_major_version:
                    is_version_match = True
            elif higher_sub_version:
                # 查找同大版本但子版本更高的包
                if pkg_major_version_num == current_major_version and pkg_sub_version_num > current_min_sub_version:
                    is_version_match = True

            if is_version_match:
                filtered_packages.append(
                    {
                        "pkg_id": pkg.id,
                        "pkg_name": pkg.name,
                        "major_version": pkg_major_version_num,
                        "sub_version": pkg_sub_version_num,
                        "full_version": pkg_major_version_num + pkg_sub_version_num,
                    }
                )

        # 按版本号排序，版本高的在前
        filtered_packages.sort(key=lambda x: x["full_version"], reverse=True)

        strategy_name = _("更高主版本") if higher_major_version else _("同大版本更高子版本")
        logger.info(_("为模块版本 {} 找到 {} 个符合条件的{}包").format(spider_version, len(filtered_packages), strategy_name))
        return filtered_packages

    except Exception as e:
        logger.error(_("过滤包失败: {}").format(e))
        return []


def find_same_major_version_higher_sub_version_modules(cluster_id: int, module_list: List[Dict]) -> List[Dict]:
    """
    找出与源集群同大版本的模块（只比较大版本，不比较子版本）

    @param cluster_id: 当前集群ID
    @param module_list: 模块列表，格式如list_modules_by_biz返回的数据
    @return: 同大版本的模块列表
    """
    try:
        # 获取当前集群信息
        logger.info(_("开始获取集群 {} 的当前spider版本信息").format(cluster_id))
        cluster, current_spider_versions, current_db_version, current_charset = _get_current_cluster_info(cluster_id)
        logger.debug(
            _("集群 {} 获取到的spider版本列表: {}，db_version: {}，charset: {}").format(
                cluster_id, current_spider_versions, current_db_version, current_charset
            )
        )
        if not current_spider_versions:
            logger.warning(_("集群 {} 没有获取到spider版本，无法继续").format(cluster_id))
            return []

        # 解析当前spider版本，取最低版本作为参考
        current_version_nums = []
        current_major_versions = []
        current_sub_versions = []
        for version in current_spider_versions:
            version_num = proxy_version_parse(version)
            logger.debug(_("解析spider版本 {} 得到的数值: {}").format(version, version_num))
            if version_num > 0:
                current_version_nums.append(version_num)
                # 解析主版本号和子版本号
                major_version, sub_version = spider_major_version_parse(version, has_prefix=False)
                logger.debug(_("spider版本 {} 解析得到主版本号: {}, 子版本号: {}").format(version, major_version, sub_version))
                current_major_versions.append(major_version)
                current_sub_versions.append(sub_version)
            else:
                logger.warning(_("spider版本 {} 解析失败，跳过").format(version))

        if not current_version_nums:
            logger.warning(_("集群 {} 的spider版本解析失败，current_version_nums为空").format(cluster_id))
            return []

        # 取当前最低版本作为比较基准
        current_min_version = min(current_version_nums)
        current_major_version = min(current_major_versions)
        current_min_sub_version = min(current_sub_versions)
        logger.info(
            _("集群 {} 当前最低spider版本号: {}, 主版本号: {}, 最低子版本号: {}").format(
                cluster_id, current_min_version, current_major_version, current_min_sub_version
            )
        )

        # 遍历模块列表，找出同大版本的模块
        same_major_version_modules = []

        for module in module_list:
            module_id = module.get("db_module_id")
            module_name = module.get("name", "")
            module_alias_name = module.get("alias_name", "")
            # 检查模块版本兼容性
            spider_version, db_version, charset, is_compatible = _check_module_version_compatibility(
                module, current_db_version, current_charset
            )
            if not is_compatible:
                continue

            # 解析模块的spider版本
            try:
                module_version_num = _parse_spider_version_to_num(spider_version)
                if module_version_num == 0:
                    continue

                # 获取模块主版本号
                if spider_version.startswith("Spider-"):
                    version_num = spider_version.replace("Spider-", "")
                    version_major_mapping = {
                        "1": 1000000,
                        "3": 3000000,
                        "3.5": 3000000,  # 3.x系列
                        "3.6": 3000000,  # 3.x系列
                        "3.7": 3000000,  # 3.x系列
                        "3.8": 3000000,  # 3.x系列
                        "4": 4000000,
                    }
                    module_major_version = version_major_mapping.get(version_num, 0)
                else:
                    module_major_version, *unused = spider_major_version_parse(spider_version, has_prefix=False)

                # 检查是否同大版本（不比较子版本）
                if module_major_version == current_major_version:
                    logger.info(
                        _("找到同大版本模块: {} (spider版本: {}, db版本: {}, 字符集: {}, 版本号: {})").format(
                            module_name, spider_version, db_version, charset, module_version_num
                        )
                    )

                    # 根据模块的主版本和当前集群的子版本来过滤包
                    module_pkg_list = _filter_packages_by_module_version(
                        module_major_version, current_min_sub_version, spider_version
                    )

                    same_major_version_modules.append(
                        {
                            "db_module_id": module_id,
                            "db_module_name": module_name,
                            "module_alias_name": module_alias_name,
                            "spider_version": spider_version,
                            "db_version": db_version,
                            "charset": charset,
                            "spider_version_num": module_version_num,
                            "pkg_list": module_pkg_list,
                        }
                    )
                else:
                    logger.debug(
                        _("模块 {} 主版本不匹配: 当前={}, 模块={}").format(
                            module_name, current_major_version, module_major_version
                        )
                    )

            except Exception as e:
                logger.warning(_("解析模块 {} 的spider版本失败: {}").format(module_id, e))
                continue

        # 按版本号排序，版本高的在前
        same_major_version_modules.sort(key=lambda x: x["spider_version_num"], reverse=True)

        logger.info(_("找到 {} 个同大版本的模块").format(len(same_major_version_modules)))
        return same_major_version_modules

    except Cluster.DoesNotExist:
        logger.error(_("集群 {} 不存在").format(cluster_id))
        return []
    except Exception as e:
        logger.error(_("查找同大版本模块时发生错误: {}").format(e))
        return []


def _filter_packages_by_module_version(
    module_major_version: int, current_min_sub_version: int, spider_version: str
) -> List[Dict]:
    """
    根据模块的主版本和当前集群的子版本来过滤包

    @param module_major_version: 模块主版本号
    @param current_min_sub_version: 当前集群最低子版本号
    @param spider_version: spider版本字符串
    @return: 符合条件的包列表
    """
    logger.info(
        _("开始过滤包 - 模块主版本: {}, 当前最低子版本: {}, spider版本: {}").format(
            module_major_version, current_min_sub_version, spider_version
        )
    )
    try:
        # 获取所有可用的spider包
        packages = Package.objects.filter(pkg_type=MediumEnum.Spider, db_type=DBType.MySQL, enable=True).order_by(
            "-priority", "-create_at"
        )

        if not packages.exists():
            logger.warning(_("没有找到可用的spider包"))
            return []

        logger.info(_("找到 {} 个可用的spider包，开始逐个检查").format(packages.count()))
        filtered_packages = []

        for pkg in packages:
            # 使用现有的版本解析方法
            pkg_major_version_num, pkg_sub_version_num = spider_major_version_parse(pkg.name, has_prefix=True)

            if pkg_major_version_num == 0:
                logger.debug(_("无法解析包 {} 的版本信息").format(pkg.name))
                continue

            # 过滤条件：
            # 1. 包的主版本必须与模块主版本一致
            # 2. 包的子版本必须高于当前集群的最低子版本
            logger.debug(
                _("检查包 {} - 主版本匹配: {} == {} -> {}, 子版本比较: {} > {} -> {}").format(
                    pkg.name,
                    pkg_major_version_num,
                    module_major_version,
                    pkg_major_version_num == module_major_version,
                    pkg_sub_version_num,
                    current_min_sub_version,
                    pkg_sub_version_num > current_min_sub_version,
                )
            )

            if pkg_major_version_num == module_major_version and pkg_sub_version_num > current_min_sub_version:
                logger.debug(_("包 {} 版本条件满足，开始检查名称匹配").format(pkg.name))

                # 额外检查：包的名称是否与spider版本匹配
                if spider_version.startswith("Spider-"):
                    version_num = spider_version.replace("Spider-", "")
                    logger.debug(_("Spider版本格式: Spider-{}, 检查包名 {} 匹配").format(version_num, pkg.name))

                    # 构建包名模式进行匹配
                    if version_num == "1" and "tspider-1" in pkg.name:
                        is_match = True
                        logger.debug(_("匹配Spider-1版本包: {}").format(pkg.name))
                    elif version_num == "3" and "tspider-3" in pkg.name:
                        is_match = True
                        logger.debug(_("匹配Spider-3版本包: {}").format(pkg.name))
                    elif version_num in ["3.5", "3.6", "3.7", "3.8"] and f"tspider-{version_num}" in pkg.name:
                        is_match = True
                        logger.debug(_("匹配Spider-{}版本包: {}").format(version_num, pkg.name))
                    elif version_num == "4" and "tspider-4" in pkg.name:
                        is_match = True
                        logger.debug(_("匹配Spider-4版本包: {}").format(pkg.name))
                    else:
                        is_match = False
                        logger.debug(_("Spider版本 {} 与包名 {} 不匹配").format(version_num, pkg.name))
                else:
                    # 如果不是Spider-格式，直接检查包名是否包含spider版本
                    is_match = spider_version in pkg.name
                    logger.debug(_("非Spider-格式版本检查: {} in {} -> {}").format(spider_version, pkg.name, is_match))

                if is_match:
                    logger.info(
                        _("找到匹配的包: {} (版本: {}.{})").format(pkg.name, pkg_major_version_num, pkg_sub_version_num)
                    )
                    filtered_packages.append(
                        {
                            "pkg_id": pkg.id,
                            "pkg_name": pkg.name,
                            "major_version": pkg_major_version_num,
                            "sub_version": pkg_sub_version_num,
                            "full_version": pkg_major_version_num + pkg_sub_version_num,
                        }
                    )
                else:
                    logger.debug(_("包 {} 名称匹配失败，跳过").format(pkg.name))
            else:
                logger.debug(_("包 {} 版本条件不满足，跳过").format(pkg.name))

        # 按版本号排序，版本高的在前
        filtered_packages.sort(key=lambda x: x["full_version"], reverse=True)

        logger.info(_("为模块版本 {} 找到 {} 个符合条件的包").format(spider_version, len(filtered_packages)))
        return filtered_packages

    except Exception as e:
        logger.error(_("过滤包失败: {}").format(e))
        return []


def example_usage_find_higher_spider_modules():
    """
    使用示例：如何找出比当前集群spider版本更高的模块
    """
    # 假设我们有一个集群ID和模块列表
    cluster_id = 123  # 当前集群ID
    bk_biz_id = 20  # 业务ID
    cluster_type = "tendbcluster"  # 集群类型

    # 获取业务下的所有模块
    module_list = list_modules_by_biz(bk_biz_id, cluster_type)

    # 找出比当前集群spider版本更高的模块
    higher_modules = find_higher_spider_version_modules(cluster_id, module_list)

    # 打印结果
    if higher_modules:
        print(_("找到 {} 个更高版本的模块:").format(len(higher_modules)))
        for module in higher_modules:
            print(_("  模块ID: {}").format(module["db_module_id"]))
            print(_("  模块名称: {}").format(module["db_module_name"]))
            print(_("  Spider版本: {}").format(module["spider_version"]))
            print(_("  DB版本: {}").format(module["db_version"]))
            print(_("  包ID: {}").format(module["pkg_list"][0]["pkg_id"]))  # 假设包列表不为空
            print(_("  包名称: {}").format(module["pkg_list"][0]["pkg_name"]))  # 假设包列表不为空
            print("  ---")
    else:
        print(_("没有找到更高版本的模块"))

    return higher_modules


def example_usage_find_same_major_version_modules():
    """
    使用示例：如何找出与源集群同大版本但子版本更高的模块
    """
    # 假设我们有一个集群ID和模块列表
    cluster_id = 123  # 当前集群ID
    bk_biz_id = 20  # 业务ID
    cluster_type = "tendbcluster"  # 集群类型

    # 获取业务下的所有模块
    module_list = list_modules_by_biz(bk_biz_id, cluster_type)

    # 找出同大版本但子版本更高的模块
    higher_sub_version_modules = find_same_major_version_higher_sub_version_modules(cluster_id, module_list)

    # 打印结果
    if higher_sub_version_modules:
        print(_("找到 {} 个同大版本更高子版本的模块:").format(len(higher_sub_version_modules)))
        for module in higher_sub_version_modules:
            print(_("  模块ID: {}").format(module["db_module_id"]))
            print(_("  模块名称: {}").format(module["db_module_name"]))
            print(_("  Spider版本: {}").format(module["spider_version"]))
            print(_("  DB版本: {}").format(module["db_version"]))
            print(_("  字符集: {}").format(module["charset"]))
            print(_("  包ID: {}").format(module["pkg_list"][0]["pkg_id"]))  # 假设包列表不为空
            print(_("  包名称: {}").format(module["pkg_list"][0]["pkg_name"]))  # 假设包列表不为空
            print("  ---")
    else:
        print(_("没有找到同大版本更高子版本的模块"))

    return higher_sub_version_modules


def get_higher_spider_version_modules_api(cluster_id: int, bk_biz_id: int, cluster_type: str = "tendbcluster") -> Dict:
    """
    API接口：获取比指定集群spider版本更高的模块列表（同时保持db_version一致）

    @param cluster_id: 当前集群ID
    @param bk_biz_id: 业务ID
    @param cluster_type: 集群类型，默认为tendbcluster
    @return: 标准API响应格式，data字段包含模块列表，格式为:
        [
            {
                "db_module_id": 11,
                "db_module_name": "xx",
                "module_alias_name": "xx",
                "spider_version": "xx",
                "db_version": "xx",
                "pkg": {
                    "pkg_id": 111,
                    "pkg_name": "xxx"
                }
            }
        ]
    """
    try:
        # 获取业务下的所有模块
        module_list = list_modules_by_biz(bk_biz_id, cluster_type)

        # 找出比当前集群spider版本更高的模块
        higher_modules = find_higher_spider_version_modules(cluster_id, module_list)

        return {"code": 0, "result": True, "message": "OK", "data": higher_modules}

    except Exception as e:
        logger.error(_("获取更高版本模块失败: {}").format(e))
        return {"code": 1, "result": False, "message": _("获取更高版本模块失败: {}").format(str(e)), "data": []}


def get_same_major_version_higher_sub_version_modules_api(
    cluster_id: int, bk_biz_id: int, cluster_type: str = "tendbcluster"
) -> Dict:
    """
    API接口：获取与源集群同大版本但子版本更高的模块列表

    @param cluster_id: 当前集群ID
    @param bk_biz_id: 业务ID
    @param cluster_type: 集群类型，默认为tendbcluster
    @return: 标准API响应格式，data字段包含模块列表，格式为:
        [
            {
                "db_module_id": 11,
                "db_module_name": "xx",
                "spider_version": "xx",
                "db_version": "xx",
                "charset": "xx",
                "pkg": {
                    "pkg_id": 111,
                    "pkg_name": "xxx"
                }
            }
        ]
    """
    try:
        # 获取业务下的所有模块
        module_list = list_modules_by_biz(bk_biz_id, cluster_type)

        # 找出同大版本但子版本更高的模块
        higher_sub_version_modules = find_same_major_version_higher_sub_version_modules(cluster_id, module_list)

        return {"code": 0, "result": True, "message": "OK", "data": higher_sub_version_modules}

    except Exception as e:
        logger.error(_("获取同大版本更高子版本模块失败: {}").format(e))
        return {"code": 1, "result": False, "message": _("获取同大版本更高子版本模块失败: {}").format(str(e)), "data": []}


def get_spider_version_modules_api(
    cluster_id: int, bk_biz_id: int, higher_major_version: bool = False, higher_sub_version: bool = False
) -> Dict:
    """
    统一的API接口：获取spider版本模块列表

    @param cluster_id: 当前集群ID
    @param bk_biz_id: 业务ID
    @param cluster_type: 集群类型，默认为tendbcluster
    @param higher_major_version: 是否查找更高主版本的模块，默认为False
    @param higher_sub_version: 是否查找同大版本但子版本更高的模块，默认为False
    @return: 标准API响应格式，data字段包含模块列表，格式为:
        [
            {
                "db_module_id": 11,
                "db_module_name": "xx",
                "spider_version": "xx",
                "db_version": "xx",
                "charset": "xx",  # 仅在同大版本更高子版本时返回
                "pkg_list": [{
                    "pkg_id": 111,
                    "pkg_name": "xxx"
                }]
            }
        ]
    """
    cluster_type = ClusterType.TenDBCluster.value
    try:
        # 获取业务下的所有模块
        module_list = list_modules_by_biz(bk_biz_id, cluster_type)

        # 根据参数选择不同的查找策略
        if higher_major_version:
            # 查找比当前集群spider版本更高的模块（同时保持db_version一致）
            result_modules = find_higher_spider_version_modules(cluster_id, module_list)
        elif higher_sub_version:
            # 找出同大版本但子版本更高的模块
            result_modules = find_same_major_version_higher_sub_version_modules(cluster_id, module_list)
        else:
            # 默认行为：如果两个参数都为False，返回空列表
            result_modules = []
            logger.warning(_("higher_major_version 和 higher_sub_version 都为False，返回空列表"))

        return {"code": 0, "result": True, "message": "OK", "data": result_modules}

    except Exception as e:
        logger.error(_("获取spider版本模块失败: {}").format(e))
        return {"code": 1, "result": False, "message": _("获取spider版本模块失败: {}").format(str(e)), "data": []}
