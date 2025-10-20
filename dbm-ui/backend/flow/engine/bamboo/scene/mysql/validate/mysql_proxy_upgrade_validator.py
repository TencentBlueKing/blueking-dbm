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

from backend.db_meta.exceptions import DBMetaException
from backend.db_meta.models import Cluster, ProxyInstance
from backend.db_package.models import Package
from backend.flow.engine.validate.exceptions import DuplicateClusterIDException
from backend.flow.engine.validate.mysql_base_validate import MysqlBaseValidator
from backend.flow.utils.mysql.mysql_version_parse import proxy_version_parse

logger = logging.getLogger("flow")


class MySQLProxyUpgradeValidator(MysqlBaseValidator):
    """
    MySQLProxyUpgrade类对应的validate类
    判断传入flow的data参数合法性

    校验内容：
    1. 检查集群存在性和基础信息合法性
    2. 检查升级包的存在性和有效性
    3. 检查proxy实例版本升级的合法性，确保升级版本高于当前版本
    4. 检查批次中所有集群使用的机器IP一致性，确保同一升级批次中所有集群的proxy实例都部署在相同的机器上
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
    - 当发现proxy版本升级不合法时，抛出DBMetaException异常
    - 当发现批次中集群使用的机器IP不一致时，抛出DBMetaException异常
    - 当发现重复集群ID时，抛出DuplicateClusterIDException异常
    - 提供详细的错误信息，包含集群ID和具体的版本差异或IP差异
    """

    def run_check_for_info(self, info: dict, index: int) -> list:

        """
        检查单个info的合法性

        @param info: 单个升级信息
        @param index: info在列表中的索引
        @return: 错误信息列表
        """
        error_msgs = []

        # 检查必要字段
        if "pkg_id" not in info:
            error_msg = _("第{}行缺少pkg_id字段").format(index + 1)
            error_msgs.append(error_msg)
            return error_msgs

        if "cluster_ids" not in info:
            error_msg = _("第{}行缺少cluster_ids字段").format(index + 1)
            error_msgs.append(error_msg)
            return error_msgs

        pkg_id = info["pkg_id"]
        cluster_ids = info["cluster_ids"]

        # 检查pkg_id是否为有效数字
        if not isinstance(pkg_id, int) or pkg_id <= 0:
            error_msg = _("第{}行pkg_id必须为正整数").format(index + 1)
            error_msgs.append(error_msg)
            return error_msgs

        # 检查cluster_ids是否为有效列表
        if not isinstance(cluster_ids, list) or not cluster_ids:
            error_msg = _("第{}行cluster_ids必须为非空列表").format(index + 1)
            error_msgs.append(error_msg)
            return error_msgs

        # 检查包是否存在且启用
        try:
            package = Package.objects.get(id=pkg_id, enable=True)
        except Package.DoesNotExist:
            error_msg = _("第{}行pkg_id {}对应的包不存在或未启用").format(index + 1, pkg_id)
            error_msgs.append(error_msg)
            return error_msgs

        # 检查集群是否存在
        try:
            clusters = Cluster.objects.filter(id__in=cluster_ids)
            if len(clusters) != len(cluster_ids):
                found_ids = [c.id for c in clusters]
                missing_ids = set(cluster_ids) - set(found_ids)
                error_msg = _("第{}行集群ID {}不存在").format(index + 1, list(missing_ids))
                error_msgs.append(error_msg)
                return error_msgs
        except Exception as e:
            error_msg = _("第{}行检查集群存在性时发生错误: {}").format(index + 1, str(e))
            error_msgs.append(error_msg)
            return error_msgs

        # 检查proxy版本升级合法性
        try:
            new_proxy_version_num = proxy_version_parse(package.name)
            proxies = ProxyInstance.objects.filter(cluster__in=clusters)

            if len(proxies) <= 0:
                error_msg = _("第{}行根据cluster_ids {}无法找到对应的proxy实例").format(index + 1, cluster_ids)
                error_msgs.append(error_msg)
                return error_msgs

            for proxy_instance in proxies:
                current_version = proxy_version_parse(proxy_instance.version)
                if current_version >= new_proxy_version_num:
                    logger.error(
                        _("集群 {} 的proxy实例 {} 当前版本 {} 大于等于升级版本 {}").format(
                            proxy_instance.cluster.id, proxy_instance.ip_port, current_version, new_proxy_version_num
                        )
                    )
                    error_msg = _("第{}行集群 {} 的proxy实例 {} 待升级版本大于等于当前版本，请确认升级的版本").format(
                        index + 1, proxy_instance.cluster.id, proxy_instance.ip_port
                    )
                    error_msgs.append(error_msg)

            # 注意：IP一致性校验移到了__call__方法中进行批次级别的校验

        except Exception as e:
            error_msg = _("第{}行检查proxy版本升级合法性时发生错误: {}").format(index + 1, str(e))
            error_msgs.append(error_msg)

        return error_msgs

    def __call__(self):
        """
        发起校验，实例函数化

        执行流程：
        1. 检查每个info的基础信息合法性
        2. 检查proxy版本升级的合法性
        3. 检查是否存在重复的集群ID
        4. 如果发现错误，分别抛出对应的异常
        5. 如果没有错误，返回None表示校验通过

        异常处理：
        - proxy版本升级检查失败时，抛出DBMetaException
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
            raise DBMetaException(message="; ".join(error_msgs))

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

        # 阶段3 检查每个info中集群使用的机器IP是否一致
        for info in self.data["infos"]:
            cluster_ids = info.get("cluster_ids", [])

            # 如果只有一个集群或没有集群，跳过检查
            if len(cluster_ids) <= 1:
                continue

            # 收集该info中所有集群的proxy IP
            info_cluster_ips = {}
            for cluster_id in cluster_ids:
                try:
                    proxies = ProxyInstance.objects.filter(cluster__id=cluster_id)
                    if proxies.exists():
                        cluster_ips = set(proxy.machine.ip for proxy in proxies)
                        info_cluster_ips[cluster_id] = cluster_ips
                except Exception as e:
                    error_msg = _("检查集群 {} 的机器IP时发生错误: {}").format(cluster_id, str(e))
                    raise DBMetaException(message=error_msg)

            # 检查该info中所有集群的IP是否一致
            if len(info_cluster_ips) > 1:
                first_cluster_id = None
                first_cluster_ips = None

                for cluster_id, cluster_ips in info_cluster_ips.items():
                    if first_cluster_id is None:
                        first_cluster_id = cluster_id
                        first_cluster_ips = cluster_ips
                    else:
                        if cluster_ips != first_cluster_ips:
                            error_msg = _("同一批次中集群使用的机器IP不一致。集群 {} 使用IP: {}，集群 {} 使用IP: {}").format(
                                first_cluster_id,
                                ", ".join(sorted(first_cluster_ips)),
                                cluster_id,
                                ", ".join(sorted(cluster_ips)),
                            )
                            raise DBMetaException(message=error_msg)

        return None
