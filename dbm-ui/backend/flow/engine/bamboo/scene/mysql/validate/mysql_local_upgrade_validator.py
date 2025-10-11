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

from django.utils.translation import gettext as _

from backend.configuration.constants import DBType
from backend.db_meta.enums import ClusterType, InstanceRole
from backend.db_meta.exceptions import DBMetaException
from backend.db_meta.models import Cluster, StorageInstance
from backend.db_package.models import Package
from backend.flow.consts import MediumEnum
from backend.flow.engine.bamboo.scene.mysql.mysql_upgrade import upgrade_version_check
from backend.flow.engine.bamboo.scene.mysql.validate.exception import (
    MySQLMasterSlaveVersionFailedException,
    MySQLUpgradeVersionFailedException,
)
from backend.flow.engine.validate.exceptions import DuplicateClusterIDException
from backend.flow.engine.validate.mysql_base_validate import MysqlBaseValidator
from backend.flow.utils.mysql.mysql_version_parse import get_online_mysql_version

logger = logging.getLogger("flow")


class MySQLLocalUpgradeValidator(MysqlBaseValidator):
    """
    MySQLLocalUpgrade类对应的validate类
    判断传入flow的data参数合法性

    校验内容：
    1. 检查集群存在性和基础信息合法性
    2. 检查所有MySQL存储节点的版本一致性（master和slave）
    3. 检查升级版本的合法性，不允许跨多个大版本升级
    4. 确保升级目标版本高于当前版本
    5. 检查是否存在重复的集群ID

    数据格式支持：
    {
        "infos": [
            {
                "pkg_id": 123,
                "cluster_ids": [1001, 1002, 1003]
            }
        ]
    }

    错误处理：
    - 当发现MySQL存储节点版本不一致时，抛出MySQLStorageVersionFailedException异常
    - 当版本升级不合法时，抛出MySQLUpgradeVersionFailedException异常
    - 当发现重复集群ID时，抛出DuplicateClusterIDException异常
    - 提供详细的错误信息，包含集群ID和具体的版本差异
    """

    def _iterate_clusters(self, cluster_check_func, context_data=None):
        """
        通用的集群遍历方法，减少重复代码

        参数：
        - cluster_check_func: 对每个集群进行检查的函数，签名为 func(cluster, cluster_id, context_data) -> list[str]
        - context_data: 传递给检查函数的上下文数据

        返回：
        - list: 错误信息列表
        """
        error_msgs = []

        for index, info in enumerate(self.data["infos"]):
            cluster_ids = info.get("cluster_ids", [])

            for cluster_id in cluster_ids:
                try:
                    cluster = Cluster.objects.get(id=cluster_id)
                    cluster_errors = cluster_check_func(cluster, cluster_id, context_data)
                    if cluster_errors:
                        error_msgs.extend(cluster_errors)
                except Cluster.DoesNotExist:
                    error_msg = _("集群 {} 不存在").format(cluster_id)
                    error_msgs.append(error_msg)
                    logger.error(error_msg)
                except Exception as e:
                    error_msg = _("检查集群 {} 时发生错误: {}").format(cluster_id, str(e))
                    error_msgs.append(error_msg)
                    logger.error(error_msg)

        return error_msgs

    def __get_pkg_name_by_pkg_id(self, pkg_id: int) -> str:
        """
        根据包ID获取包名

        参数：
        - pkg_id: 包ID

        返回：
        - str: 包名

        异常：
        - Package.DoesNotExist: 当包不存在时抛出
        """
        try:
            mysql_pkg = Package.objects.get(id=pkg_id, pkg_type=MediumEnum.MySQL, db_type=DBType.MySQL)
            return mysql_pkg.name
        except Package.DoesNotExist:
            raise DBMetaException(message=_("包ID {} 不存在或不是MySQL包").format(pkg_id))

    def _check_cluster_master_slave_version(self, cluster, cluster_id, context_data=None):
        """检查单个集群的主从版本一致性"""
        error_msgs = []

        # 获取主实例
        master_instances = StorageInstance.objects.filter(
            cluster=cluster, instance_role=InstanceRole.BACKEND_MASTER
        ).all()

        # 获取从实例
        slave_instances = StorageInstance.objects.filter(
            cluster=cluster, instance_role=InstanceRole.BACKEND_SLAVE
        ).all()

        if not master_instances:
            error_msg = _("集群 {} 没有找到主实例").format(cluster_id)
            error_msgs.append(error_msg)
            logger.error(error_msg)
            return error_msgs

        # 收集主实例版本
        master_versions = set()
        for instance in master_instances:
            if instance.version:
                master_versions.add(instance.version)

        # 收集从实例版本
        slave_versions = set()
        for instance in slave_instances:
            if instance.version:
                slave_versions.add(instance.version)

        # 检查主实例内部版本一致性
        if len(master_versions) > 1:
            error_msg = _("集群 {} 的主实例版本不一致，发现 {} 种不同版本: {}").format(
                cluster_id, len(master_versions), ", ".join(sorted(master_versions))
            )
            error_msgs.append(error_msg)
            logger.error(error_msg)

        # 检查从实例内部版本一致性
        if len(slave_versions) > 1:
            error_msg = _("集群 {} 的从实例版本不一致，发现 {} 种不同版本: {}").format(
                cluster_id, len(slave_versions), ", ".join(sorted(slave_versions))
            )
            error_msgs.append(error_msg)
            logger.error(error_msg)

        # 检查主从版本一致性
        if master_versions and slave_versions:
            if master_versions != slave_versions:
                error_msg = _("集群 {} 主从实例版本不一致，主实例版本: {}，从实例版本: {}").format(
                    cluster_id, ", ".join(sorted(master_versions)), ", ".join(sorted(slave_versions))
                )
                error_msgs.append(error_msg)
                logger.error(error_msg)
            else:
                logger.info(_("集群 {} 主从实例版本一致: {}").format(cluster_id, ", ".join(sorted(master_versions))))

        # 检查版本信息是否为空
        if not master_versions:
            error_msg = _("集群 {} 的主实例版本信息为空").format(cluster_id)
            error_msgs.append(error_msg)
            logger.error(error_msg)

        if slave_instances and not slave_versions:
            error_msg = _("集群 {} 的从实例版本信息为空").format(cluster_id)
            error_msgs.append(error_msg)
            logger.error(error_msg)

        return error_msgs

    def pre_check_mysql_master_slave_version(self):
        """
        检查MySQL主从实例的版本一致性

        仅对 TenDBHA 架构的集群执行此检查。

        返回：
        - list: 错误信息列表，如果没有错误则返回空列表
        """

        def checker(cluster, cluster_id, context_data=None):
            # 仅 TenDBHA 集群需要主从一致性检查
            if cluster.cluster_type != ClusterType.TENDB_HA:
                logger.info(_("跳过非 TenDBHA 集群 {} 的主从版本检查").format(cluster_id))
                return []
            return self._check_cluster_master_slave_version(cluster, cluster_id, context_data)

        return self._iterate_clusters(checker)

    def _check_cluster_upgrade_version(self, cluster, cluster_id, target_version):
        """检查单个集群的升级版本兼容性"""
        error_msgs = []
        cluster_name = cluster.name

        logger.info(_("检查集群 {} 的版本兼容性").format(cluster_name))

        # 只获取集群的主实例进行版本检查
        master_instances = StorageInstance.objects.filter(
            cluster=cluster, instance_role__in=[InstanceRole.ORPHAN, InstanceRole.BACKEND_MASTER]
        )

        if not master_instances.exists():
            error_msg = _("集群 {} 没有找到主实例").format(cluster_name)
            error_msgs.append(error_msg)
            logger.error(error_msg)
            return error_msgs

        # 只对主实例进行版本检查
        for instance in master_instances:
            try:
                # 使用 get_online_mysql_version 获取真实的在线版本
                online_version = get_online_mysql_version(
                    instance.machine.ip, instance.port, instance.machine.bk_cloud_id
                )

                if not online_version:
                    error_msg = _("集群 {} 主实例 {}:{} 无法获取在线版本").format(cluster_name, instance.machine.ip, instance.port)
                    error_msgs.append(error_msg)
                    logger.error(error_msg)
                    continue

                # 使用真实的在线版本进行升级版本检查
                upgrade_version_check(online_version, target_version)
                logger.info(
                    _("集群 {} 主实例 {}:{} 版本检查通过: {} -> {}").format(
                        cluster_name, instance.machine.ip, instance.port, online_version, target_version
                    )
                )
            except Exception as e:
                error_msg = _("集群 {} 主实例 {}:{} 版本检查失败: {}").format(
                    cluster_name, instance.machine.ip, instance.port, str(e)
                )
                error_msgs.append(error_msg)
                logger.error(error_msg)

        return error_msgs

    def pre_check_mysql_upgrade_version(self):
        """
        检查MySQL升级版本的合法性（从mysql_upgrade.py中的_pre_upgrade_version_check抽取）

        校验逻辑：
        1. 遍历所有待升级的集群信息
        2. 获取每个集群的所有MySQL存储实例
        3. 对每个实例调用upgrade_version_check进行详细的版本检查
        4. 确保所有实例的版本都能成功升级到目标版本

        返回：
        - list: 错误信息列表，如果没有错误则返回空列表
        """
        error_msgs = []

        logger.info(_("开始进行升级前版本兼容性检查"))

        # 遍历所有待升级的集群信息
        for index, info in enumerate(self.data["infos"]):
            cluster_ids = info.get("cluster_ids", [])
            pkg_id = info.get("pkg_id")

            if not pkg_id:
                error_msg = _("包ID信息缺失")
                error_msgs.append(error_msg)
                continue

            try:
                target_version = self.__get_pkg_name_by_pkg_id(pkg_id)
                logger.info(_("参数pkg_id:{},获取包名: {}").format(pkg_id, target_version))
            except DBMetaException as e:
                error_msg = _("获取包名失败: {}").format(str(e))
                error_msgs.append(error_msg)
                logger.error(error_msg)
                continue

            # 使用公共方法进行集群检查，传递目标版本作为上下文
            for cluster_id in cluster_ids:
                try:
                    cluster = Cluster.objects.get(id=cluster_id)
                    cluster_errors = self._check_cluster_upgrade_version(cluster, cluster_id, target_version)
                    if cluster_errors:
                        error_msgs.extend(cluster_errors)
                except Cluster.DoesNotExist:
                    error_msg = _("集群 {} 不存在").format(cluster_id)
                    error_msgs.append(error_msg)
                    logger.error(error_msg)
                except Exception as e:
                    error_msg = _("检查集群 {} 升级版本时发生错误: {}").format(cluster_id, str(e))
                    error_msgs.append(error_msg)
                    logger.error(error_msg)

        return error_msgs

    def run_check_for_info(self, info: dict, index: int) -> list:
        """
        检查每个info的基础信息合法性

        @param info：  self.data["infos"]每个元素体
        @param index： 每个元素体的编号
        """
        row_key = info.get("row_key", "")
        error_msgs = []

        # 检查集群ID是否存在
        cluster_ids = info.get("cluster_ids", [])
        if not cluster_ids:
            error_msgs.append(_("cluster_ids 不能为空"))
            return error_msgs

        log_format_tag = self.create_log_tag(field="cluster_ids", index=index, row_key=row_key)
        error_msg = self.pre_check_cluster_exist(cluster_ids, **log_format_tag)
        if error_msg:
            error_msgs.append(error_msg)

        # 检查包ID
        pkg_id = info.get("pkg_id")
        if not pkg_id:
            error_msgs.append(_("pkg_id 不能为空"))
        else:
            # 验证包ID是否有效
            try:
                self.__get_pkg_name_by_pkg_id(pkg_id)
            except DBMetaException as e:
                error_msgs.append(_("无效的pkg_id {}: {}").format(pkg_id, str(e)))

        return error_msgs

    def __call__(self):
        """
        发起校验，实例函数化

        执行流程：
        1. 检查每个info的基础信息合法性
        2. 检查MySQL存储节点版本一致性
        3. 检查升级版本的合法性
        4. 检查是否存在重复的集群ID
        5. 如果发现错误，分别抛出对应的异常
        6. 如果没有错误，返回None表示校验通过

        异常处理：
        - MySQL主从版本一致性失败时，抛出MySQLMasterSlaveVersionFailedException
        - 升级版本检查失败时，抛出MySQLUpgradeVersionFailedException
        - 重复集群ID时，抛出DuplicateClusterIDException
        - 异常消息包含所有发现的问题

        返回：
        - None: 校验通过
        - 异常: 校验失败时抛出对应的具体异常
        """
        # 阶段1 检测每个行的数据合法性
        error_msgs = []
        for index, info in enumerate(self.data["infos"]):
            error_msgs += self.run_check_for_info(info, index)
        if error_msgs:
            return error_msgs

        # 阶段2 检查重复集群ID
        all_cluster_ids = []
        for info in self.data["infos"]:
            all_cluster_ids.extend(info.get("cluster_ids", []))

        duplicate_clusters = []
        seen_clusters = set()
        for cluster_id in all_cluster_ids:
            if cluster_id in seen_clusters:
                duplicate_clusters.append(cluster_id)
            else:
                seen_clusters.add(cluster_id)

        if duplicate_clusters:
            error_msg = _("存在重复的集群ID: {}").format(", ".join(map(str, duplicate_clusters)))
            raise DuplicateClusterIDException(error_msg)

        # 阶段3 检查MySQL主从版本一致性（仅 TenDBHA）
        master_slave_version_errors = self.pre_check_mysql_master_slave_version()
        if master_slave_version_errors:
            # MySQL主从版本一致性检查失败，抛出专门的异常
            raise MySQLMasterSlaveVersionFailedException("\n".join(master_slave_version_errors))

        # 阶段4 检查升级版本的合法性（从mysql_upgrade.py抽取的逻辑）
        upgrade_version_errors = self.pre_check_mysql_upgrade_version()
        if upgrade_version_errors:
            # 升级版本检查失败，抛出专门的异常
            raise MySQLUpgradeVersionFailedException("\n".join(upgrade_version_errors))

        return None
