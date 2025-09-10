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
import re
from typing import Dict, List

from django.utils.translation import gettext as _

from backend.configuration.constants import DBType
from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster, StorageInstance
from backend.db_package.models import Package
from backend.db_services.cmdb.biz import list_modules_by_biz
from backend.flow.consts import MediumEnum
from backend.flow.utils.mysql.common.mysql_cluster_info import get_version_and_charset
from backend.flow.utils.mysql.mysql_bk_config import get_mysql_version_and_charset
from backend.flow.utils.mysql.mysql_version_parse import (
    calculate_mysql_version_number,
    calculate_tmysql_version_number,
    get_online_mysql_version,
    module_version_parse,
)
from backend.flow.utils.spider.spider_bk_config import get_spider_version_and_charset

logger = logging.getLogger("root")


def _parse_package_version(pkg_name: str) -> int:
    """
    解析不同类型MySQL包的版本号，返回数值版本用于比较

    支持的包格式：
    1. mysql-8.0.32-linux-glibc2.12-x86_64.tar.xz （标准MySQL）
    2. mysql-txsql-8.0.30-20241001-linux-x86_64.tar.gz （txsql版本）
    3. mysql-5.7.20-linux-x86_64-tmysql-3.4.4-gcs.tar.gz （tmysql版本）
    4. mysql-5.5.24-linux-x86_64-tspider-1.15-gcs.tar.gz （tspider版本）

    @param pkg_name: 包名
    @return: 数值版本号，用于比较（主版本*1000000 + 次版本*1000 + 修订版本）
    """
    try:
        logger.debug(_("开始解析包版本: {}").format(pkg_name))
        # txsql格式：mysql-txsql-8.0.30-20241001-linux-x86_64.tar.gz
        txsql_pattern = r"mysql-txsql-(\d+)\.(\d+)\.(\d+)"
        match = re.match(txsql_pattern, pkg_name)
        if match:
            major, minor, patch = match.groups()
            version_num = calculate_mysql_version_number(int(major), int(minor), int(patch))
            logger.debug(_("TXSQL包 {} 解析版本: {}.{}.{} -> {}").format(pkg_name, major, minor, patch, version_num))
            return version_num

        # tmysql格式：mysql-5.7.20-linux-x86_64-tmysql-3.4.4-gcs.tar.gz
        tmysql_pattern = r"mysql-(\d+)\.(\d+)\.(\d+)-.*-tmysql-(\d+)\.(\d+)\.(\d+)"
        match = re.match(tmysql_pattern, pkg_name)
        if match:
            mysql_major, mysql_minor, mysql_patch, tmysql_major, tmysql_minor, tmysql_patch = match.groups()
            # 对于tmysql，使用MySQL基础版本号 + tmysql子版本号
            version_num = calculate_tmysql_version_number(
                int(mysql_major),
                int(mysql_minor),
                int(mysql_patch),
                int(tmysql_major),
                int(tmysql_minor),
                int(tmysql_patch),
            )
            return version_num

        # tspider格式：mysql-5.5.24-linux-x86_64-tspider-1.15-gcs.tar.gz
        tspider_pattern = r"mysql-(\d+)\.(\d+)\.(\d+)-.*-tspider-(\d+)\.(\d+)"
        match = re.match(tspider_pattern, pkg_name)
        if match:
            mysql_major, mysql_minor, mysql_patch, tspider_major, tspider_minor = match.groups()
            # 对于tspider，使用MySQL基础版本号
            version_num = calculate_mysql_version_number(int(mysql_major), int(mysql_minor), int(mysql_patch))
            logger.debug(
                _("TSpider包 {} 解析版本: {}.{}.{}-tspider-{}.{} -> {}").format(
                    pkg_name, mysql_major, mysql_minor, mysql_patch, tspider_major, tspider_minor, version_num
                )
            )
            return version_num

        # 标准MySQL格式：mysql-8.0.32-linux-glibc2.12-x86_64.tar.xz
        mysql_pattern = r"mysql-(\d+)\.(\d+)\.(\d+)"
        match = re.match(mysql_pattern, pkg_name)
        if match:
            major, minor, patch = match.groups()
            version_num = calculate_mysql_version_number(int(major), int(minor), int(patch))
            logger.debug(_("✓ 标准MySQL包 {} 解析版本: {}.{}.{} -> {}").format(pkg_name, major, minor, patch, version_num))
            return version_num

        # 如果都不匹配，尝试使用原有的module_version_parse
        logger.warning(_("包名 {} 格式不识别，尝试使用默认解析").format(pkg_name))
        return module_version_parse(pkg_name)

    except Exception as e:
        logger.error(_("解析包版本失败: {} - {}").format(pkg_name, e))
        return 0


def _parse_actual_mysql_version(version_string: str) -> int:
    """
    解析实际MySQL版本字符串（来自 select version()）

    示例版本字符串：
    - 5.7.20-tmysql-3.4.2-log
    - 8.0.32
    - 8.0.30-txsql

    @param version_string: MySQL版本字符串
    @return: 数值版本号，用于比较
    """
    try:
        # tmysql格式：5.7.20-tmysql-3.4.2-log
        tmysql_pattern = r"(\d+)\.(\d+)\.(\d+)-tmysql-(\d+)\.(\d+)\.(\d+)"
        match = re.match(tmysql_pattern, version_string)
        if match:
            mysql_major, mysql_minor, mysql_patch, tmysql_major, tmysql_minor, tmysql_patch = match.groups()
            version_num = calculate_tmysql_version_number(
                int(mysql_major),
                int(mysql_minor),
                int(mysql_patch),
                int(tmysql_major),
                int(tmysql_minor),
                int(tmysql_patch),
            )
            logger.debug(_("实际TMySQL版本 {} 解析为: {}").format(version_string, version_num))
            return version_num

        # txsql格式：8.0.30-txsql
        txsql_pattern = r"(\d+)\.(\d+)\.(\d+)-txsql"
        match = re.match(txsql_pattern, version_string)
        if match:
            major, minor, patch = match.groups()
            version_num = calculate_mysql_version_number(int(major), int(minor), int(patch))
            logger.debug(_("实际TXSQL版本 {} 解析为: {}").format(version_string, version_num))
            return version_num

        # 标准MySQL格式：8.0.32
        mysql_pattern = r"(\d+)\.(\d+)\.(\d+)"
        match = re.match(mysql_pattern, version_string)
        if match:
            major, minor, patch = match.groups()
            version_num = calculate_mysql_version_number(int(major), int(minor), int(patch))
            logger.debug(_("实际MySQL版本 {} 解析为: {}").format(version_string, version_num))
            return version_num

        logger.warning(_("无法解析实际MySQL版本: {}").format(version_string))
        return 0

    except Exception as e:
        logger.error(_("解析实际MySQL版本失败: {} - {}").format(version_string, e))
        return 0


def _check_package_type_compatibility(pkg_name: str, actual_version: str) -> bool:
    """
    检查包类型与实际版本的兼容性

    @param pkg_name: 包名
    @param actual_version: 实际MySQL版本字符串
    @return: 是否兼容
    """
    try:
        logger.debug(_("检查包类型兼容性: 包={}, 实际版本={}").format(pkg_name, actual_version))

        # tmysql实际版本只能使用tmysql包
        if "tmysql" in actual_version and "tmysql" in pkg_name:
            logger.debug(_("✓ tmysql包与tmysql实际版本兼容"))
            return True

        # txsql实际版本只能使用txsql包
        if "txsql" in actual_version and "txsql" in pkg_name:
            logger.debug(_("✓ txsql包与txsql实际版本兼容"))
            return True

        # 标准MySQL版本可以使用标准MySQL包
        if "tmysql" not in actual_version and "txsql" not in actual_version:
            if "tmysql" not in pkg_name and "txsql" not in pkg_name and "tspider" not in pkg_name:
                logger.debug(_("✓ 标准MySQL包与标准MySQL实际版本兼容"))
                return True

        # tspider是特殊情况，目前不在升级范围内
        logger.debug(_("✗ 包 {} 与实际版本 {} 类型不兼容").format(pkg_name, actual_version))
        return False

    except Exception as e:
        logger.error(_("检查包类型兼容性失败: {} - {}").format(pkg_name, e))
        return False


def get_storage_version_modules_api(
    cluster_id: int, bk_biz_id: int, higher_major_version: bool = False, higher_sub_version: bool = False
) -> Dict:
    """
    统一的API接口：获取存储层版本模块列表

    重要概念区分：
    1. 模块配置版本：通过 get_version_and_charset() 获取的模块配置中的版本
    2. 集群实际版本：通过 select version() 获取的实际运行版本

    两种升级场景：
    - higher_major_version: 找模块配置版本更高的其他模块，包含该模块的所有可用包
    - higher_sub_version: 找模块配置版本相同的模块，但包版本要高于当前集群实际运行版本

    @param cluster_id: 当前集群ID
    @param bk_biz_id: 业务ID
    @param higher_major_version: 是否查找更高主版本的模块，默认为False
    @param higher_sub_version: 是否查找同大版本但子版本更高的模块，默认为False
    @return: 标准API响应格式，data字段包含模块列表，格式为:
        [
            {
                "db_module_id": 11,
                "db_module_name": "xx",
                "db_version": "xx",
                "charset": "xx",  # 仅在同大版本更高子版本时返回
                "pkg_list": [{
                    "pkg_id": 111,
                    "pkg_name": "xxx"
                }]
            }
        ]
    """
    try:
        logger.info(_("=== 开始获取存储层版本模块列表 ==="))
        logger.info(
            _("请求参数 - cluster_id: {}, bk_biz_id: {}, higher_major_version: {}, higher_sub_version: {}").format(
                cluster_id, bk_biz_id, higher_major_version, higher_sub_version
            )
        )

        # 获取当前集群信息
        cluster = Cluster.objects.get(id=cluster_id)
        cluster_type = cluster.cluster_type
        logger.info(_("当前集群信息 - 类型: {}, 模块ID: {}").format(cluster_type, cluster.db_module_id))

        # 获取业务下的所有模块
        module_list = list_modules_by_biz(bk_biz_id, cluster_type)
        logger.info(_("业务 {} 下共找到 {} 个 {} 类型的模块").format(bk_biz_id, len(module_list), cluster_type))

        # 根据参数选择不同的查找策略
        result_modules = []

        if higher_major_version and higher_sub_version:
            logger.info(_("执行策略: 合并查找存储层版本更高的模块和同大版本但子版本更高的模块"))
            # 获取更高主版本的模块
            major_version_modules = _find_higher_storage_version_modules(cluster_id, module_list, cluster_type)
            # 获取同大版本但子版本更高的模块
            sub_version_modules = _find_same_major_storage_version_higher_sub_version_modules(
                cluster_id, module_list, cluster_type
            )
            # 合并结果
            result_modules = major_version_modules + sub_version_modules
            logger.info(
                _("合并结果: 更高主版本模块 {} 个，更高子版本模块 {} 个，总计 {} 个").format(
                    len(major_version_modules), len(sub_version_modules), len(result_modules)
                )
            )
        elif higher_major_version:
            logger.info(_("执行策略: 查找存储层版本更高的模块"))
            result_modules = _find_higher_storage_version_modules(cluster_id, module_list, cluster_type)
        elif higher_sub_version:
            logger.info(_("执行策略: 查找同大版本但子版本更高的模块"))
            result_modules = _find_same_major_storage_version_higher_sub_version_modules(
                cluster_id, module_list, cluster_type
            )
        else:
            # 默认行为：如果两个参数都为False，返回空列表
            logger.warning(_("higher_major_version 和 higher_sub_version 都为False，返回空列表"))

        logger.info(_("=== 完成获取存储层版本模块列表，共找到 {} 个符合条件的模块 ===").format(len(result_modules)))
        return {"code": 0, "result": True, "message": "OK", "data": result_modules}

    except Exception as e:
        logger.error(_("获取存储层版本模块失败: {}").format(e))
        return {"code": 1, "result": False, "message": _("获取存储层版本模块失败: {}").format(str(e)), "data": []}


def _get_module_storage_version_and_charset(bk_biz_id: int, db_module_id: int, cluster_type: str) -> tuple:
    """
    获取模块的存储层版本和字符集
    """
    return get_mysql_version_and_charset(bk_biz_id, db_module_id, cluster_type)


def _get_module_spider_version_and_charset(bk_biz_id: int, db_module_id: int, cluster_type: str) -> tuple:
    """
    获取模块的spider版本和模块字符集
    """
    return get_spider_version_and_charset(bk_biz_id, db_module_id)


def _get_current_cluster_storage_info(cluster_id: int) -> tuple:
    """
    获取当前集群的存储层信息

    @param cluster_id: 集群ID
    @return: (cluster, current_module_storage_version, current_charset, current_module_spider_version)
    """
    cluster = Cluster.objects.get(id=cluster_id)

    # 获取当前集群模块配置的存储层版本和字符集（注意：这是模块配置版本，不是实际运行版本）
    try:
        current_charset, current_module_storage_version = get_version_and_charset(
            cluster.bk_biz_id, cluster.db_module_id, cluster.cluster_type
        )
        logger.info(
            _("集群 {} 模块配置的存储层版本: {}, 字符集: {}").format(cluster_id, current_module_storage_version, current_charset)
        )
    except Exception as e:
        logger.error(_("获取集群 {} 模块配置的存储层版本和字符集失败: {}").format(cluster_id, e))
        return cluster, None, None, None

    # 如果是tendbcluster，需要获取当前模块的spider版本配置
    current_module_spider_version = None
    if cluster.cluster_type == ClusterType.TenDBCluster.value:
        try:
            # 获取当前集群所属模块的spider版本配置
            current_module_spider_version, *unused = _get_module_spider_version_and_charset(
                cluster.bk_biz_id, cluster.db_module_id, cluster.cluster_type
            )
            if current_module_spider_version:
                logger.info(_("集群 {} 所属模块的spider版本配置: {}").format(cluster_id, current_module_spider_version))
            else:
                logger.warning(_("集群 {} 所属模块的spider版本配置为空").format(cluster_id))
        except Exception as e:
            logger.error(_("获取集群 {} 所属模块spider版本配置失败: {}").format(cluster_id, e))

    return cluster, current_module_storage_version, current_charset, current_module_spider_version


def _find_higher_storage_version_modules(cluster_id: int, module_list: List[Dict], cluster_type: str) -> List[Dict]:
    """
    找出存储层版本更高的模块

    @param cluster_id: 当前集群ID
    @param module_list: 模块列表，格式如list_modules_by_biz返回的数据
    @param cluster_type: 集群类型
    @return: 存储层版本更高的模块列表
    """
    try:
        # 获取当前集群的存储层信息
        (
            cluster,
            current_module_storage_version,
            current_charset,
            current_module_spider_version,
        ) = _get_current_cluster_storage_info(cluster_id)
        if not current_module_storage_version:
            return []

        # 解析当前存储层模块配置版本
        current_module_storage_version_num = module_version_parse(current_module_storage_version)
        if current_module_storage_version_num == 0:
            logger.warning(_("集群 {} 的存储层模块版本解析失败: {}").format(cluster_id, current_module_storage_version))
            return []

        logger.info(
            _("集群 {} 当前存储层模块版本: {}, 版本号: {}").format(
                cluster_id, current_module_storage_version, current_module_storage_version_num
            )
        )

        # 遍历模块列表，找出存储层版本更高的模块
        higher_version_modules = []
        processed_count = 0
        skipped_count = 0
        matched_count = 0

        logger.info(_("开始遍历 {} 个模块，寻找版本更高的模块").format(len(module_list)))

        for module in module_list:
            module_id = module.get("db_module_id")
            module_name = module.get("name", "")
            processed_count += 1

            logger.debug(
                _("处理模块 {}/{}: ID={}, Name={}").format(processed_count, len(module_list), module_id, module_name)
            )

            # 跳过当前集群所在的模块
            if module_id == cluster.db_module_id:
                logger.debug(_("跳过当前集群所在模块: {}").format(module_name))
                skipped_count += 1
                continue

            # 获取模块的存储层版本和字符集
            try:
                module_charset, module_storage_version = _get_module_storage_version_and_charset(
                    cluster.bk_biz_id, module_id, cluster_type
                )

                logger.debug(
                    _("模块 {} 配置信息 - 存储版本: {}, 字符集: {}").format(module_name, module_storage_version, module_charset)
                )

                # 检查字符集是否匹配
                if module_charset != current_charset:
                    logger.debug(_("✗ 模块 {} 字符集不匹配: {} != {}，跳过").format(module_name, module_charset, current_charset))
                    skipped_count += 1
                    continue

                # 如果是tendbcluster，还需要检查模块的spider版本配置是否与当前模块spider版本配置匹配
                if cluster_type == ClusterType.TenDBCluster.value and current_module_spider_version:
                    module_spider_version, *unused = _get_module_spider_version_and_charset(
                        cluster.bk_biz_id, module_id, cluster_type
                    )

                    logger.debug(
                        _("TenDBCluster检查 - 模块spider版本: {}, 当前spider版本: {}").format(
                            module_spider_version, current_module_spider_version
                        )
                    )

                    if module_spider_version != current_module_spider_version:
                        logger.debug(
                            _("✗ 模块 {} spider版本配置不匹配: {} != {}，跳过").format(
                                module_name, module_spider_version, current_module_spider_version
                            )
                        )
                        skipped_count += 1
                        continue

                # 解析模块存储层版本（模块配置版本）
                module_storage_version_num = module_version_parse(module_storage_version)
                if module_storage_version_num == 0:
                    logger.debug(_("✗ 模块 {} 存储层版本解析失败: {}，跳过").format(module_name, module_storage_version))
                    skipped_count += 1
                    continue

                logger.debug(
                    _("版本比较 - 模块 {}: {} ({}) vs 当前: {} ({})").format(
                        module_name,
                        module_storage_version,
                        module_storage_version_num,
                        current_module_storage_version,
                        current_module_storage_version_num,
                    )
                )

                # 检查存储层版本是否更高（比较模块配置版本）
                if module_storage_version_num > current_module_storage_version_num:
                    matched_count += 1
                    logger.info(
                        _("✓ 找到更高存储层版本模块: {} (版本: {} -> {})").format(
                            module_name, module_storage_version, module_storage_version_num
                        )
                    )

                    # 获取对应的包列表
                    pkg_list = _get_storage_packages_for_module(module_storage_version, current_module_storage_version)

                    logger.debug(_("模块 {} 获得 {} 个可用包").format(module_name, len(pkg_list)))

                    higher_version_modules.append(
                        {
                            "db_module_id": module_id,
                            "db_module_name": module_name,
                            "db_version": module_storage_version,
                            "charset": module_charset,
                            "pkg_list": pkg_list,
                        }
                    )
                else:
                    logger.debug(
                        _("✗ 模块 {} 版本不够高: {} <= {}").format(
                            module_name, module_storage_version_num, current_module_storage_version_num
                        )
                    )
                    skipped_count += 1

            except Exception as e:
                logger.warning(_("✗ 处理模块 {} 时发生错误: {}").format(module_id, e))
                skipped_count += 1
                continue

        # 按版本号排序，版本高的在前
        higher_version_modules.sort(key=lambda x: module_version_parse(x["db_version"]), reverse=True)

        logger.info(
            _("模块筛选完成 - 总处理: {}, 跳过: {}, 匹配: {}, 最终结果: {}").format(
                processed_count, skipped_count, matched_count, len(higher_version_modules)
            )
        )

        logger.info(_("找到 {} 个存储层版本更高的模块").format(len(higher_version_modules)))
        return higher_version_modules

    except Cluster.DoesNotExist:
        logger.error(_("集群 {} 不存在").format(cluster_id))
        return []
    except Exception as e:
        logger.error(_("查找更高存储层版本模块时发生错误: {}").format(e))
        return []


def _find_same_major_storage_version_higher_sub_version_modules(
    cluster_id: int, module_list: List[Dict], cluster_type: str
) -> List[Dict]:
    """
    找出当前集群模块的更高子版本包

    @param cluster_id: 当前集群ID
    @param module_list: 模块列表，格式如list_modules_by_biz返回的数据
    @param cluster_type: 集群类型
    @return: 当前模块的更高子版本包列表
    """
    try:
        # 获取当前集群的存储层信息
        (
            cluster,
            current_module_storage_version,
            current_charset,
            current_module_spider_version,
        ) = _get_current_cluster_storage_info(cluster_id)
        if not current_module_storage_version:
            return []

        # 获取集群存储实际运行版本（用于与包版本比较）
        actual_storage_version = get_storage_actual_version(cluster_id)
        if not actual_storage_version:
            logger.warning(_("获取集群 {} 的实际存储层版本失败").format(cluster_id))
            return []

        logger.info(
            _("集群 {} 模块配置版本: {}, 实际运行版本: {}").format(
                cluster_id, current_module_storage_version, actual_storage_version
            )
        )

        # 在模块列表中找到当前集群的模块
        current_module = None
        for module in module_list:
            if module.get("db_module_id") == cluster.db_module_id:
                current_module = module
                break

        if not current_module:
            logger.warning(_("在模块列表中未找到当前集群 {} 的模块 {}").format(cluster_id, cluster.db_module_id))
            return []

        module_name = current_module.get("name", "")
        logger.info(_("找到当前集群模块: {} (模块配置版本: {})").format(module_name, current_module_storage_version))

        # 获取更高子版本的包列表
        pkg_list = _get_higher_sub_version_packages(current_module_storage_version, actual_storage_version)

        # 返回当前模块的信息和可升级包列表
        result = [
            {
                "db_module_id": cluster.db_module_id,
                "db_module_name": module_name,
                "db_version": current_module_storage_version,
                "charset": current_charset,
                "pkg_list": pkg_list,
            }
        ]

        logger.info(_("为当前模块 {} 找到 {} 个可升级的子版本包").format(module_name, len(pkg_list)))
        return result

    except Cluster.DoesNotExist:
        logger.error(_("集群 {} 不存在").format(cluster_id))
        return []
    except Exception as e:
        logger.error(_("查找当前模块更高子版本包时发生错误: {}").format(e))
        return []


def get_storage_actual_version(cluster_id: int) -> str:
    """
    获取存储层的实际版本 select version();
    返回值如下
    #  select version()
    #  tmysql:  select version();==> 5.7.20-tmysql-3.4.2-log
    #  社区版本 mysql:> select version(); 8.0.32
    #  txsql: select version(); 8.0.30-txsql
    """
    cluster = Cluster.objects.get(id=cluster_id)
    instance = StorageInstance.objects.filter(
        cluster=cluster,
    ).first()
    return get_online_mysql_version(instance.machine.ip, instance.port, cluster.bk_cloud_id)


def _get_storage_packages_for_module(module_storage_version: str, current_module_storage_version: str) -> List[Dict]:
    """
    获取模块对应的存储层包列表（更高版本）

    用于 higher_major_version 场景：获取版本 >= 目标模块配置版本的包

    @param module_storage_version: 目标模块的存储层配置版本
    @param current_module_storage_version: 当前集群模块的存储层配置版本
    @return: 包列表
    """
    try:
        # 获取所有可用的MySQL包
        logger.info(
            _("开始查询MySQL存储层包 - 目标模块版本: {}, 当前模块版本: {}").format(module_storage_version, current_module_storage_version)
        )

        packages = Package.objects.filter(
            pkg_type=MediumEnum.MySQL, version=module_storage_version, db_type=DBType.MySQL, enable=True
        ).order_by("-priority", "-create_at")

        logger.info(_("数据库中共找到 {} 个启用的MySQL包").format(packages.count()))

        if not packages.exists():
            logger.warning(_("没有找到可用的MySQL存储层包"))
            return []

        logger.info(_("找到 {} 个可用的MySQL存储层包，开始筛选").format(packages.count()))
        filtered_packages = []

        for idx, pkg in enumerate(packages):
            logger.debug(_("处理包 {}/{}: {}").format(idx + 1, packages.count(), pkg.name))

            # 使用新的包版本解析函数
            pkg_version_num = _parse_package_version(pkg.name)
            module_version_num = module_version_parse(module_storage_version)

            logger.debug(
                _("包版本解析结果 - 包: {} -> {}, 模块: {} -> {}").format(
                    pkg.name, pkg_version_num, module_storage_version, module_version_num
                )
            )

            if pkg_version_num >= module_version_num:
                logger.info(
                    _("✓ 匹配的存储层包: {} (包版本号: {} >= 模块版本号: {})").format(pkg.name, pkg_version_num, module_version_num)
                )
                filtered_packages.append({"pkg_id": pkg.id, "pkg_name": pkg.name, "version_num": pkg_version_num})
            else:
                logger.debug(
                    _("✗ 跳过包: {} (包版本号: {} < 模块版本号: {})").format(pkg.name, pkg_version_num, module_version_num)
                )

        # 按版本号排序，版本高的在前
        filtered_packages.sort(key=lambda x: x["version_num"], reverse=True)

        logger.info(_("为存储层版本 {} 找到 {} 个符合条件的包").format(module_storage_version, len(filtered_packages)))
        return [{"pkg_id": pkg["pkg_id"], "pkg_name": pkg["pkg_name"]} for pkg in filtered_packages]

    except Exception as e:
        logger.error(_("获取存储层包失败: {}").format(e))
        return []


def _get_higher_sub_version_packages(module_storage_version: str, actual_storage_version: str) -> List[Dict]:
    """
    获取同大版本但子版本更高的包列表

    用于 higher_sub_version 场景：
    1. 先找到与模块配置版本相同的模块
    2. 然后找到版本高于集群实际运行版本的包

    @param module_storage_version: 目标模块的存储层配置版本（用于确定包的兼容性）
    @param actual_storage_version: 当前集群的实际运行版本（用于比较包版本）
    @return: 包列表
    """
    try:
        logger.info(_("开始获取子版本更高的包 - 模块配置版本: {}, 实际运行版本: {}").format(module_storage_version, actual_storage_version))

        # 获取所有可用的MySQL包
        packages = Package.objects.filter(
            pkg_type=MediumEnum.MySQL, version=module_storage_version, db_type=DBType.MySQL, enable=True
        ).order_by("-priority", "-create_at")

        logger.info(_("数据库中共找到 {} 个启用的MySQL包").format(packages.count()))

        if not packages.exists():
            logger.warning(_("没有找到可用的MySQL存储层包"))
            return []

        # 解析实际版本号
        actual_version_num = _parse_actual_mysql_version(actual_storage_version)
        if actual_version_num == 0:
            logger.warning(_("实际存储层版本解析失败: {}").format(actual_storage_version))
            return []

        logger.info(_("版本解析完成 - 实际版本: {} -> 版本号: {}").format(actual_storage_version, actual_version_num))
        filtered_packages = []
        compatible_count = 0
        higher_version_count = 0

        for idx, pkg in enumerate(packages):
            logger.debug(_("处理包 {}/{}: {}").format(idx + 1, packages.count(), pkg.name))

            # 使用新的包版本解析函数
            pkg_version_num = _parse_package_version(pkg.name)

            logger.debug(_("包版本解析结果: {} -> {}").format(pkg.name, pkg_version_num))

            # 包版本必须高于实际版本，并且与模块配置版本相兼容
            if pkg_version_num > actual_version_num:
                higher_version_count += 1
                logger.debug(_("包版本更高: {} ({} > {})").format(pkg.name, pkg_version_num, actual_version_num))

                # 检查包类型是否与实际版本匹配（例如tmysql包对应tmysql实际版本）
                is_compatible = _check_package_type_compatibility(pkg.name, actual_storage_version)
                logger.debug(_("包兼容性检查: {} 与 {} -> {}").format(pkg.name, actual_storage_version, is_compatible))

                if is_compatible:
                    compatible_count += 1
                    logger.info(
                        _("✓ 找到子版本更高且兼容的包: {} (版本号: {} > {})").format(pkg.name, pkg_version_num, actual_version_num)
                    )
                    filtered_packages.append({"pkg_id": pkg.id, "pkg_name": pkg.name, "version_num": pkg_version_num})
                else:
                    logger.debug(_("✗ 包类型不兼容: {}").format(pkg.name))
            else:
                logger.debug(_("✗ 包版本不够高: {} ({} <= {})").format(pkg.name, pkg_version_num, actual_version_num))

        # 按版本号排序，版本高的在前
        filtered_packages.sort(key=lambda x: x["version_num"], reverse=True)

        logger.info(
            _("筛选结果汇总 - 总包数: {}, 版本更高: {}, 类型兼容: {}, 最终筛选: {}").format(
                packages.count(), higher_version_count, compatible_count, len(filtered_packages)
            )
        )

        logger.info(_("为存储层版本 {} 找到 {} 个子版本更高的包").format(module_storage_version, len(filtered_packages)))
        return [{"pkg_id": pkg["pkg_id"], "pkg_name": pkg["pkg_name"]} for pkg in filtered_packages]

    except Exception as e:
        logger.error(_("获取子版本更高的包失败: {}").format(e))
        return []


def get_cluster_version_info(cluster_id: int) -> Dict:
    """
    获取集群的版本信息，用于调试和展示两种版本的区别

    @param cluster_id: 集群ID
    @return: 包含两种版本信息的字典
    """
    try:
        cluster = Cluster.objects.get(id=cluster_id)

        # 1. 获取模块配置版本
        module_charset, module_storage_version = get_version_and_charset(
            cluster.bk_biz_id, cluster.db_module_id, cluster.cluster_type
        )

        # 2. 获取实际运行版本
        actual_storage_version = get_storage_actual_version(cluster_id)

        # 3. 如果是tendbcluster，获取spider版本配置
        module_spider_version = None
        if cluster.cluster_type == ClusterType.TenDBCluster.value:
            module_spider_version, *unused = _get_module_spider_version_and_charset(
                cluster.bk_biz_id, cluster.db_module_id, cluster.cluster_type
            )

        return {
            "cluster_id": cluster_id,
            "cluster_type": cluster.cluster_type,
            "module_storage_version": module_storage_version,  # 模块配置的存储版本
            "actual_storage_version": actual_storage_version,  # 实际运行的存储版本
            "module_spider_version": module_spider_version,  # 模块配置的spider版本
            "charset": module_charset,
            "explanation": {
                "module_storage_version": _("通过get_version_and_charset()获取的模块配置版本，用于筛选升级目标模块"),
                "actual_storage_version": _("通过select version()获取的实际运行版本，用于与包版本比较"),
                "module_spider_version": _("模块配置的spider版本，用于tendbcluster的兼容性检查"),
            },
        }

    except Exception as e:
        logger.error(_("获取集群版本信息失败: {}").format(e))
        return {"error": str(e)}
