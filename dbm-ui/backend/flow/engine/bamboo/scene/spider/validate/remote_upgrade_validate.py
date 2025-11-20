"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from django.utils.translation import gettext as _

from backend.db_meta.enums import ClusterStatus, InstanceRole
from backend.db_meta.models import Cluster, StorageInstance
from backend.db_package.models import Package
from backend.flow.engine.bamboo.scene.spider.validate.exception import (
    StorageVersionFailedException,
    UpgradeVersionFailedException,
)
from backend.flow.engine.validate.mysql_base_validate import MysqlBaseValidator
from backend.flow.utils.mysql.mysql_version_parse import major_version_parse


class TenDBClusterRemoteUpgradeValidator(MysqlBaseValidator):
    """
    TenDBClusterRemoteUpgrade类对应的validate类
    判断传入flow的data参数合法性

    校验内容：
    1. 集群状态正常
    2. 包的存在性校验
    3. 存储所有节点版本主版本必须一致
    4. 本地升级时：存储所有节点版本主版本和包的主版本必须一致
    5. 本地升级时：主机维度切换时master和slave机器上的分片必须一致
    6. 迁移升级：待定

    数据格式支持：
    - upgrade_local: 是否本地升级
    - infos: 升级信息列表，包含cluster_id、pkg_id等

    错误处理：
    - 当发现版本不一致时，抛出StorageVersionFailedException异常
    - 当包不存在时，抛出UpgradeVersionFailedException异常
    - 提供详细的错误信息，包含集群ID和具体的版本差异
    """

    def pre_check_cluster_status(self):
        """
        检查集群状态是否正常

        校验逻辑：
        1. 遍历所有待升级的集群信息
        2. 检查集群状态是否为NORMAL
        3. 如果发现异常状态，记录错误信息

        返回：
        - list: 错误信息列表，如果没有错误则返回空列表
        """
        error_msgs = []

        for info in self.data["infos"]:
            cluster_id = info["cluster_id"]
            try:
                cluster = Cluster.objects.get(id=cluster_id)
                if cluster.status != ClusterStatus.NORMAL.value:
                    error_msg = _("集群 {} 状态异常，当前状态: {}，无法进行升级").format(cluster_id, cluster.status)
                    error_msgs.append(error_msg)
            except Cluster.DoesNotExist:
                error_msg = _("集群 {} 不存在").format(cluster_id)
                error_msgs.append(error_msg)
            except Exception as e:
                error_msg = _("检查集群 {} 状态时发生异常: {}").format(cluster_id, str(e))
                error_msgs.append(error_msg)

        return error_msgs

    def pre_check_package_existence(self):
        """
        检查包的存在性

        校验逻辑：
        1. 遍历所有待升级的集群信息
        2. 检查pkg_id对应的包是否存在且启用
        3. 如果发现包不存在或未启用，记录错误信息

        返回：
        - list: 错误信息列表，如果没有错误则返回空列表
        """
        error_msgs = []

        for info in self.data["infos"]:
            pkg_id = info.get("pkg_id")
            if not pkg_id:
                error_msg = _("缺少包ID信息")
                error_msgs.append(error_msg)
                continue

            try:
                package = Package.objects.get(id=pkg_id, enable=True)
                if not package:
                    error_msg = _("包 {} 不存在或未启用").format(pkg_id)
                    error_msgs.append(error_msg)
            except Package.DoesNotExist:
                error_msg = _("包 {} 不存在或未启用").format(pkg_id)
                error_msgs.append(error_msg)
            except Exception as e:
                error_msg = _("检查包 {} 时发生异常: {}").format(pkg_id, str(e))
                error_msgs.append(error_msg)

        return error_msgs

    def pre_check_storage_version_consistency(self):
        """
        检查存储所有节点版本主版本必须一致

        校验逻辑：
        1. 遍历所有待升级的集群信息
        2. 获取每个集群的所有存储实例
        3. 解析每个存储实例的版本号，提取主版本号
        4. 检查所有存储实例的主版本号是否一致
        5. 如果发现版本不一致，记录错误信息

        返回：
        - list: 错误信息列表，如果没有错误则返回空列表
        """
        error_msgs = []

        for info in self.data["infos"]:
            cluster_id = info["cluster_id"]
            try:
                cluster = Cluster.objects.get(id=cluster_id)
                storage_instances = StorageInstance.objects.filter(
                    cluster=cluster,
                    instance_role__in=[InstanceRole.BACKEND_MASTER.value, InstanceRole.BACKEND_SLAVE.value],
                )

                if not storage_instances.exists():
                    error_msg = _("集群 {} 没有找到存储实例").format(cluster_id)
                    error_msgs.append(error_msg)
                    continue

                # 收集所有存储实例的主版本号
                major_versions = set()
                version_details = []

                for instance in storage_instances:
                    if not instance.version:
                        error_msg = _("集群 {} 的存储实例 {}:{} 版本信息为空").format(
                            cluster_id, instance.machine.ip, instance.port
                        )
                        error_msgs.append(error_msg)
                        continue

                    try:
                        major_version = major_version_parse(instance.version)
                        major_versions.add(major_version)
                        version_details.append(
                            _("实例 {}:{} 版本: {} (主版本: {})").format(
                                instance.machine.ip, instance.port, instance.version, major_version
                            )
                        )
                    except Exception as e:
                        error_msg = _("解析集群 {} 存储实例 {}:{} 版本 {} 时发生异常: {}").format(
                            cluster_id, instance.machine.ip, instance.port, instance.version, str(e)
                        )
                        error_msgs.append(error_msg)

                # 检查主版本一致性
                if len(major_versions) > 1:
                    error_msg = _("集群 {} 存储节点主版本不一致，发现 {} 种不同主版本: {}").format(
                        cluster_id, len(major_versions), ", ".join(map(str, major_versions))
                    )
                    error_msg += _("\n详细信息:\n{}").format("\n".join(version_details))
                    error_msgs.append(error_msg)

            except Cluster.DoesNotExist:
                error_msg = _("集群 {} 不存在").format(cluster_id)
                error_msgs.append(error_msg)
            except Exception as e:
                error_msg = _("检查集群 {} 存储版本一致性时发生异常: {}").format(cluster_id, str(e))
                error_msgs.append(error_msg)

        return error_msgs

    def pre_check_local_upgrade_version_consistency(self):
        """
        检查本地升级时存储版本与包版本的一致性

        校验逻辑：
        1. 检查是否为本地升级模式
        2. 如果是本地升级，检查存储所有节点版本主版本和包的主版本必须一致
        3. 如果发现版本不一致，记录错误信息

        返回：
        - list: 错误信息列表，如果没有错误则返回空列表
        """
        error_msgs = []

        # 检查是否为本地升级模式
        upgrade_local = self.data.get("upgrade_local", False)
        if not upgrade_local:
            # 非本地升级模式，跳过此检查
            return error_msgs

        for info in self.data["infos"]:
            cluster_id = info["cluster_id"]
            pkg_id = info.get("pkg_id")

            if not pkg_id:
                continue

            try:
                # 获取包信息
                package = Package.objects.get(id=pkg_id, enable=True)
                pkg_major_version = major_version_parse(package.version)

                # 获取集群存储实例的主版本
                cluster = Cluster.objects.get(id=cluster_id)
                storage_instances = StorageInstance.objects.filter(
                    cluster=cluster,
                    instance_role__in=[InstanceRole.BACKEND_MASTER.value, InstanceRole.BACKEND_SLAVE.value],
                )

                if not storage_instances.exists():
                    continue

                # 检查存储实例主版本与包主版本的一致性
                storage_major_versions = set()
                for instance in storage_instances:
                    if instance.version:
                        try:
                            storage_major_version = major_version_parse(instance.version)
                            storage_major_versions.add(storage_major_version)
                        except Exception:
                            continue

                if storage_major_versions and pkg_major_version not in storage_major_versions:
                    error_msg = _("集群 {} 本地升级时存储主版本 {} 与包主版本 {} 不一致，" "本地升级要求存储版本主版本与包主版本必须一致").format(
                        cluster_id, ", ".join(map(str, storage_major_versions)), pkg_major_version
                    )
                    error_msgs.append(error_msg)

            except Package.DoesNotExist:
                error_msg = _("包 {} 不存在或未启用").format(pkg_id)
                error_msgs.append(error_msg)
            except Cluster.DoesNotExist:
                error_msg = _("集群 {} 不存在").format(cluster_id)
                error_msgs.append(error_msg)
            except Exception as e:
                error_msg = _("检查集群 {} 本地升级版本一致性时发生异常: {}").format(cluster_id, str(e))
                error_msgs.append(error_msg)

        return error_msgs

    def pre_check_shard_master_slave_same_machine(self):
        """
        检查分片主从同机校验（仅本地升级时执行）

        校验逻辑：
        1. 检查是否为本地升级模式
        2. 如果是本地升级，检查主机维度切换时，master和slave机器上的分片是否一致
        3. 通过 cluster.tendbclusterstorageset_set 获取分片信息
        4. 通过 storage_instance_tuple 获取主从关系
        5. 检查如果master_ip1上有分片1、2、3，那么slave_ip1上也必须有对应的分片1、2、3

        返回：
        - list: 错误信息列表，如果没有错误则返回空列表
        """
        error_msgs = []

        # 检查是否为本地升级模式
        upgrade_local = self.data.get("upgrade_local", False)
        if not upgrade_local:
            # 非本地升级模式，跳过此检查
            return error_msgs

        for info in self.data["infos"]:
            cluster_id = info["cluster_id"]
            try:
                cluster = Cluster.objects.get(id=cluster_id)

                # 获取集群的所有分片信息
                shards = cluster.tendbclusterstorageset_set.all()

                if not shards.exists():
                    # 如果没有分片信息，跳过检查
                    continue

                # 按master机器IP分组，检查对应的slave机器上的分片是否一致
                master_ip_to_shards = {}
                slave_ip_to_shards = {}
                shard_info = {}

                # 收集分片信息
                for shard in shards:
                    shard_id = shard.shard_id
                    # 通过 storage_instance_tuple 获取主从实例
                    remote_master = StorageInstance.objects.get(id=shard.storage_instance_tuple.ejector_id)
                    remote_slave = StorageInstance.objects.get(id=shard.storage_instance_tuple.receiver_id)

                    master_ip = remote_master.machine.ip
                    slave_ip = remote_slave.machine.ip

                    # 按master IP分组
                    if master_ip not in master_ip_to_shards:
                        master_ip_to_shards[master_ip] = []
                    master_ip_to_shards[master_ip].append(shard_id)

                    # 按slave IP分组
                    if slave_ip not in slave_ip_to_shards:
                        slave_ip_to_shards[slave_ip] = []
                    slave_ip_to_shards[slave_ip].append(shard_id)

                    # 保存分片信息
                    shard_info[shard_id] = {
                        "master_ip": master_ip,
                        "slave_ip": slave_ip,
                        "master_port": remote_master.port,
                        "slave_port": remote_slave.port,
                    }

                # 检查主机维度切换时，master和slave机器上的分片是否一致
                for master_ip, master_shard_ids in master_ip_to_shards.items():
                    # 找到这个master对应的slave IP
                    slave_ips = set()
                    for shard_id in master_shard_ids:
                        slave_ips.add(shard_info[shard_id]["slave_ip"])

                    # 如果这个master对应的slave分布在多个机器上，检查每个slave机器上的分片
                    for slave_ip in slave_ips:
                        # 获取这个slave机器上的分片
                        slave_shard_ids = slave_ip_to_shards.get(slave_ip, [])

                        # 检查master机器上的分片和slave机器上的分片是否一致
                        master_shard_set = set(master_shard_ids)
                        slave_shard_set = set(slave_shard_ids)

                        if master_shard_set != slave_shard_set:
                            # 找出不一致的分片
                            missing_in_slave = master_shard_set - slave_shard_set
                            extra_in_slave = slave_shard_set - master_shard_set

                            error_details = []
                            if missing_in_slave:
                                error_details.append(
                                    _("slave机器 {} 缺少分片: {}").format(
                                        slave_ip, ", ".join(map(str, sorted(missing_in_slave)))
                                    )
                                )
                            if extra_in_slave:
                                error_details.append(
                                    _("slave机器 {} 多余分片: {}").format(
                                        slave_ip, ", ".join(map(str, sorted(extra_in_slave)))
                                    )
                                )

                            error_msg = _(
                                "集群 {} 主机维度切换校验失败：master机器 {} 和slave机器 {} 上的分片不一致，"
                                "{}，本地升级要求主机维度切换时master和slave机器上的分片必须一致"
                            ).format(cluster_id, master_ip, slave_ip, "；".join(error_details))
                            error_msgs.append(error_msg)

            except Cluster.DoesNotExist:
                error_msg = _("集群 {} 不存在").format(cluster_id)
                error_msgs.append(error_msg)
            except Exception as e:
                error_msg = _("检查集群 {} 分片主从同机时发生异常: {}").format(cluster_id, str(e))
                error_msgs.append(error_msg)

        return error_msgs

    def __call__(self):
        """
        发起校验，实例函数化

        执行流程：
        1. 检查集群状态是否正常
        2. 检查包的存在性
        3. 检查存储所有节点版本主版本一致性
        4. 如果是本地升级，检查存储版本与包版本一致性
        5. 如果是本地升级，检查主机维度切换时master和slave机器上的分片是否一致
        6. 如果发现错误，抛出相应异常

        异常处理：
        - 当发现版本不一致时，抛出StorageVersionFailedException
        - 当包不存在时，抛出UpgradeVersionFailedException
        - 异常消息包含所有发现的校验问题

        返回：
        - None: 校验通过
        - 异常: 校验失败时抛出相应异常
        """
        all_error_msgs = []

        # 1. 检查集群状态是否正常
        cluster_status_errors = self.pre_check_cluster_status()
        all_error_msgs.extend(cluster_status_errors)

        # 2. 检查包的存在性
        package_existence_errors = self.pre_check_package_existence()
        all_error_msgs.extend(package_existence_errors)

        # 3. 检查存储所有节点版本主版本一致性
        storage_version_errors = self.pre_check_storage_version_consistency()
        all_error_msgs.extend(storage_version_errors)

        # 4. 如果是本地升级，检查存储版本与包版本一致性
        local_upgrade_errors = self.pre_check_local_upgrade_version_consistency()
        all_error_msgs.extend(local_upgrade_errors)

        # 5. 如果是本地升级，检查分片主从同机
        shard_same_machine_errors = self.pre_check_shard_master_slave_same_machine()
        all_error_msgs.extend(shard_same_machine_errors)

        # 如果有错误，抛出异常
        if all_error_msgs:
            # 根据错误类型选择不同的异常
            if package_existence_errors:
                raise UpgradeVersionFailedException("\n".join(all_error_msgs))
            else:
                raise StorageVersionFailedException("\n".join(all_error_msgs))

        return None
