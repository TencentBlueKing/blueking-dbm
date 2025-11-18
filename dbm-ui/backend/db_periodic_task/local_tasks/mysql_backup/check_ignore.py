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

from backend.db_report.models import MysqlInspectIgnore

logger = logging.getLogger("root")


class CheckIgnore:

    cluster_all = "__all__"
    cluster_type = ""

    def __init__(self, subtype: str):
        self.subtype = subtype
        self.ignore_map = {}

    def should_ignore_check(self, bk_biz_id: int, cluster: str) -> bool:
        """
        检查是否应该忽略某个集群的巡检, 不需要 cluster_type

        Args:
            bk_biz_id: 业务ID, required
            cluster: 集群域名
            subtype: 巡检类型

        Returns:
            bool: True表示应该忽略，False表示不应该忽略
        """
        try:
            ignore_config = MysqlInspectIgnore.objects.filter(
                bk_biz_id=bk_biz_id, subtype=self.subtype, is_enabled=True
            )
            clusters = [self.cluster_all]
            if cluster != "":
                clusters.append(cluster)
            ignore_config = ignore_config.filter(cluster__in=clusters)

            if ignore_config.first():
                return True
            return False
        except Exception as e:
            logger.error(f"Error checking ignore config for cluster {cluster}: {e}")
            # 出错时不忽略，继续执行巡检
            return False

    # get ignore configs by subtype
    def __get_ignore_configs_by_type(self, cluster_type) -> list[MysqlInspectIgnore]:
        """
        根据巡检类型获取忽略配置列表

        Args:
            subtype: 巡检类型, required
            cluster_type: 集群类型

        Returns:
            list: 忽略配置对象列表
        """
        try:
            ignore_configs = MysqlInspectIgnore.objects.filter(subtype=self.subtype, is_enabled=True)
            if cluster_type != "":
                ignore_configs = ignore_configs.filter(cluster_type=cluster_type)

            return list(ignore_configs.all())
        except Exception as e:
            logger.error(f"Error getting ignore configs by subtype {self.subtype}: {e}")
            return []

    def __build_ignore_config_map(self, ignores: list[MysqlInspectIgnore]) -> dict:
        """
        构建忽略配置映射 {c.bk_biz_id}-{c.cluster}-{c.subtype}
        """
        self.ignore_map = {"__fake__": True}
        for ignore in ignores:
            self.ignore_map[ignore.__str__()] = ignore.is_enabled
        return self.ignore_map

    def should_ignore_check_cluster(self, bk_biz_id: int, cluster: str, cluster_type: str) -> bool:
        """
        构建忽略配置映射 {c.bk_biz_id}-{c.cluster}-{c.subtype}
        会缓存 ignore_map，避免重复查询
        如果 cluster_type 为空，则会根据 subtype 查到所有的 ignore_configs
        """
        if cluster_type != self.cluster_type:
            self.cluster_type = cluster_type
            self.ignore_map = {}

        if not self.ignore_map or cluster_type != self.cluster_type:
            self.__build_ignore_config_map(self.__get_ignore_configs_by_type(cluster_type))

        k1 = f"{bk_biz_id}-{cluster}-{self.subtype}"
        k2 = f"{bk_biz_id}-{self.cluster_all}-{self.subtype}"
        if self.ignore_map.get(k1, False):
            return True
        else:
            return self.ignore_map.get(k2, False)
