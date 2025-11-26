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

from django.utils.translation import gettext as _

from backend.components import DRSApi
from backend.configuration.constants import DBType
from backend.db_meta.enums import InstanceInnerRole
from backend.db_meta.exceptions import DBMetaException
from backend.db_meta.models import Cluster
from backend.db_package.models import Package
from backend.flow.consts import MediumEnum
from backend.flow.engine.bamboo.scene.common.get_real_version import get_mysql_real_version
from backend.flow.engine.bamboo.scene.mysql.validate.exception import TenDBHAUpgradeParamCheckFailedException
from backend.flow.engine.validate.mysql_base_validate import MysqlBaseValidator
from backend.flow.utils.mysql.common.mysql_cluster_info import get_version_and_charset
from backend.flow.utils.mysql.mysql_version_parse import mysql_version_parse

logger = logging.getLogger("flow")

# 需要检查的参数及其关闭状态的值
UPGRADE_CHECK_PARAMS = ["log_bin_compress", "binlog_checksum"]
PARAM_OFF_VALUES = ["0", "off", "OFF", "NONE", "none", ""]

# 升级到 MySQL 8.0 需要的最低 tlinux 版本
MIN_TLINUX_VERSION = (1, 2)


class TenDBHAUpgradeValidator(MysqlBaseValidator):
    """
    TenDBHA迁移升级校验类

    校验内容：
    1. 检查升级前后字符集一致性
    2. 当升级目标版本是 MySQL 8.0 及以上时：
       - 检查 master 实例的以下参数必须已关闭：
         * log_bin_compress: 必须为 0 或 OFF
         * binlog_checksum: 必须为 0、OFF 或 NONE
       - 检查新主机的操作系统版本：
         * tlinux 版本必须大于 1.2

    数据格式：
    {
        "bk_biz_id": 10101,
        "infos": [
            {
                "pkg_id": 15072,
                "cluster_ids": [1110001],
                "new_db_module_id": 578,
                "old_nodes": {
                    "old_master": [{"ip": "127.0.0.1", "bk_cloud_id": 0, ...}],
                    "old_slave": [...]
                }
            }
        ],
        "nodes": {
            "0_new_master": [{"ip": "127.0.0.2", "os_name": "tlinux-2.6", ...}],
            "0_new_slave": [{"ip": "127.0.0.3", "os_name": "tlinux-2.6", ...}]
        }
    }

    注意：注释中的 IP 地址必须使用 127.0.0.x 格式，避免敏感信息泄露。
    """

    def _get_pkg_info(self, pkg_id: int) -> Package:
        """
        根据包ID获取包信息

        @param pkg_id: 包ID
        @return: Package对象
        """
        try:
            return Package.objects.get(id=pkg_id, pkg_type=MediumEnum.MySQL, db_type=DBType.MySQL)
        except Package.DoesNotExist:
            raise DBMetaException(message=_("包ID {} 不存在或不是MySQL包").format(pkg_id))

    def _is_mysql_80_or_above(self, pkg_name: str) -> bool:
        """
        判断是否为 MySQL 8.0 及以上版本

        使用精确的版本解析方法，避免简单字符串匹配导致的误判。

        @param pkg_name: 包名，如 "mysql-txsql-8.0.30-20241001-linux-x86_64.tar.gz"
        @return: 是否为 8.0 及以上版本
        """
        try:
            # 使用项目中的方法获取真实版本号，如 "8.0.30"
            real_version = get_mysql_real_version(pkg_name)
            # 解析版本号为数字进行比较，如 8000030
            version_num = mysql_version_parse(real_version)
            # MySQL 8.0.0 对应的版本号是 8000000
            mysql_80_version_num = mysql_version_parse("8.0.0")
            return version_num >= mysql_80_version_num
        except Exception as e:
            logger.warning(_("解析包名 {} 版本失败: {}，使用备用判断").format(pkg_name, str(e)))
            # 备用判断：检查版本号部分是否以 8. 开头
            try:
                real_version = get_mysql_real_version(pkg_name)
                return real_version.startswith("8.")
            except Exception:
                return False

    def _parse_tlinux_version(self, os_name: str) -> tuple:
        """
        解析 tlinux 版本号

        支持的格式：
        - "tlinux-2.6"
        - "Tencent tlinux release 2.2 (Final)"

        @param os_name: 操作系统名称
        @return: (major, minor) 版本元组，解析失败返回 (0, 0)
        """
        if not os_name:
            return (0, 0)

        os_name_lower = os_name.lower()

        # 匹配 tlinux 后面的版本号
        # 格式1: tlinux-2.6
        # 格式2: tlinux release 2.2
        patterns = [
            r"tlinux[- ]+(\d+)\.(\d+)",  # 匹配 tlinux-2.6
            r"tlinux\s+release\s+(\d+)\.(\d+)",  # 匹配 tlinux release 2.2
        ]

        for pattern in patterns:
            match = re.search(pattern, os_name_lower)
            if match:
                try:
                    major = int(match.group(1))
                    minor = int(match.group(2))
                    return (major, minor)
                except (ValueError, IndexError):
                    continue

        return (0, 0)

    def _is_tlinux_version_valid(self, os_name: str) -> bool:
        """
        检查 tlinux 版本是否满足要求（大于 1.2）

        @param os_name: 操作系统名称
        @return: 是否满足版本要求
        """
        version = self._parse_tlinux_version(os_name)

        # 版本为 (0, 0) 表示无法解析，可能不是 tlinux 系统，暂时放行
        if version == (0, 0):
            logger.warning(_("无法解析操作系统版本: {}，跳过版本检查").format(os_name))
            return True

        # 比较版本：必须大于 1.2
        return version > MIN_TLINUX_VERSION

    def _query_master_variables(self, master_ip: str, master_port: int, bk_cloud_id: int) -> dict:
        """
        查询 master 实例的变量值

        @param master_ip: master IP
        @param master_port: master 端口
        @param bk_cloud_id: 云区域ID
        @return: 变量名到值的映射
        """
        query_sql = "show global variables where Variable_name in ('{}')".format("','".join(UPGRADE_CHECK_PARAMS))
        address = "{}:{}".format(master_ip, master_port)

        try:
            res = DRSApi.rpc(
                {
                    "addresses": [address],
                    "cmds": [query_sql],
                    "force": False,
                    "bk_cloud_id": bk_cloud_id,
                }
            )

            if res[0]["error_msg"]:
                logger.error(_("查询 {} 变量失败: {}").format(address, res[0]["error_msg"]))
                return {}

            variables = {}
            if isinstance(res[0]["cmd_results"][0]["table_data"], list):
                for row in res[0]["cmd_results"][0]["table_data"]:
                    variables[row["Variable_name"]] = row["Value"]

            return variables

        except Exception as e:
            logger.error(_("查询 {} 变量时发生异常: {}").format(address, str(e)))
            return {}

    def _check_param_is_off(self, param_name: str, param_value: str) -> bool:
        """
        检查参数是否已关闭

        @param param_name: 参数名
        @param param_value: 参数值
        @return: 是否已关闭
        """
        return param_value in PARAM_OFF_VALUES

    def _check_master_params(self, info: dict, pkg_name: str) -> list:
        """
        检查单个 info 中所有 master 的参数

        @param info: infos 中的单个元素
        @param pkg_name: 目标包名
        @return: 错误信息列表
        """
        error_msgs = []
        cluster_ids = info.get("cluster_ids", [])

        for cluster_id in cluster_ids:
            try:
                cluster = Cluster.objects.get(id=cluster_id)
                master_instance = cluster.storageinstance_set.filter(
                    instance_inner_role=InstanceInnerRole.MASTER.value
                ).first()

                if not master_instance:
                    error_msgs.append(_("集群 {} 没有找到 master 实例").format(cluster_id))
                    continue

                errors = self._check_single_master(
                    master_ip=master_instance.machine.ip,
                    master_port=master_instance.port,
                    bk_cloud_id=cluster.bk_cloud_id,
                    cluster_id=cluster_id,
                )
                error_msgs.extend(errors)

            except Cluster.DoesNotExist:
                error_msgs.append(_("集群 {} 不存在").format(cluster_id))
        return error_msgs

    def _check_single_master(self, master_ip: str, master_port: int, bk_cloud_id: int, cluster_id: int) -> list:
        """
        检查单个 master 实例的参数

        @param master_ip: master IP
        @param master_port: master 端口
        @param bk_cloud_id: 云区域ID
        @param cluster_id: 集群ID
        @return: 错误信息列表
        """
        error_msgs = []
        address = "{}:{}".format(master_ip, master_port)

        logger.info(_("检查 master {} 的升级参数").format(address))

        variables = self._query_master_variables(master_ip, master_port, bk_cloud_id)

        if not variables:
            error_msgs.append(_("集群 {} 的 master {} 无法查询变量，请检查实例状态").format(cluster_id, address))
            return error_msgs

        # 检查每个参数
        invalid_params = []
        for param_name in UPGRADE_CHECK_PARAMS:
            param_value = variables.get(param_name, "")
            if not self._check_param_is_off(param_name, param_value):
                invalid_params.append("{}={}".format(param_name, param_value))

        if invalid_params:
            # 优化错误信息格式，使用换行符使信息更清晰
            error_msg = _("集群 {} 的 master {} 存在未关闭的参数: {}").format(cluster_id, address, ", ".join(invalid_params))
            error_msgs.append(error_msg)

        return error_msgs

    def pre_check_upgrade_params(self) -> list:
        """
        检查升级到 8.0 版本时的参数要求

        @return: 错误信息列表
        """
        error_msgs = []

        for info in self.data.get("infos", []):
            pkg_id = info.get("pkg_id")

            if not pkg_id:
                continue

            try:
                pkg = self._get_pkg_info(pkg_id)
                pkg_name = pkg.name

                # 只有升级到 8.0 版本才需要检查
                if not self._is_mysql_80_or_above(pkg_name):
                    logger.info(_("目标版本 {} 不是 8.0，跳过参数检查").format(pkg_name))
                    continue

                logger.info(_("目标版本 {} 是 8.0，开始检查 master 参数").format(pkg_name))

                # 检查 master 参数
                errors = self._check_master_params(info, pkg_name)
                error_msgs.extend(errors)

            except DBMetaException as e:
                error_msgs.append(str(e))
                logger.error(str(e))

        return error_msgs

    def pre_check_charset_consistency(self) -> list:
        """
        检查升级前后字符集一致性

        @return: 错误信息列表
        """
        error_msgs = []
        bk_biz_id = self.data.get("bk_biz_id")

        if not bk_biz_id:
            logger.warning(_("单据数据中缺少 bk_biz_id，跳过字符集检查"))
            return error_msgs

        for info in self.data.get("infos", []):
            cluster_ids = info.get("cluster_ids", [])
            new_db_module_id = info.get("new_db_module_id")

            if not cluster_ids or not new_db_module_id:
                continue

            try:
                cluster_class = Cluster.objects.get(id=cluster_ids[0])
                origin_charset, origin_mysql_ver = get_version_and_charset(
                    bk_biz_id,
                    db_module_id=cluster_class.db_module_id,
                    cluster_type=cluster_class.cluster_type,
                )

                new_charset, new_mysql_ver = get_version_and_charset(
                    bk_biz_id,
                    db_module_id=new_db_module_id,
                    cluster_type=cluster_class.cluster_type,
                )

                if new_charset != origin_charset:
                    error_msgs.append(
                        _("{}升级前后字符集不一致,原字符集：{},新模块的字符集{}").format(
                            cluster_class.immute_domain, origin_charset, new_charset
                        )
                    )

            except Cluster.DoesNotExist:
                error_msgs.append(_("集群 {} 不存在").format(cluster_ids[0] if cluster_ids else _("未知")))
            except Exception as e:
                logger.error(_("检查集群 {} 字符集时发生异常: {}").format(cluster_ids[0] if cluster_ids else _("未知"), str(e)))
                error_msgs.append(_("检查字符集时发生异常: {}").format(str(e)))

        return error_msgs

    def __call__(self):
        """
        执行校验

        @return: None 表示校验通过，否则抛出异常
        """
        all_errors = []

        # 检查升级前后字符集一致性
        charset_errors = self.pre_check_charset_consistency()
        all_errors.extend(charset_errors)

        # 检查升级参数（log_bin_compress 和 binlog_checksum）
        upgrade_param_errors = self.pre_check_upgrade_params()

        # 如果有升级参数错误，格式化错误信息并添加操作说明
        if upgrade_param_errors:
            # 每个集群的错误信息独立一行
            formatted_param_errors = "\n".join(upgrade_param_errors)
            # 操作说明单独一行，更突出
            operation_instruction = _(
                "升级到 MySQL 8.0 版本前，需要关闭 log_bin_compress 和 binlog_checksum 参数（设置为 0 或 OFF），然后重新发起备份"
            )
            # 组合错误信息和操作说明
            formatted_param_errors_with_instruction = formatted_param_errors + "\n" + operation_instruction
            all_errors.append(formatted_param_errors_with_instruction)

        if all_errors:
            # 优化错误信息展示，不同错误类型之间用双换行符分隔
            formatted_error_msg = "\n\n".join(all_errors)
            raise TenDBHAUpgradeParamCheckFailedException(formatted_error_msg)

        return None
