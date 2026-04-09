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
from typing import List, Optional

from backend.db_report.models import MysqlInspectIgnore

logger = logging.getLogger("root")

# policy 常量
POLICY_INCLUDE = "include"
# exclude 或空字符串都表示排除（忽略巡检）
POLICY_EXCLUDE = "exclude"

# 通配符常量
CLUSTER_ALL = "*"
BIZ_ALL = -1


class CheckIgnore:

    cluster_type = ""

    def __init__(self, subtype: str):
        self.subtype = subtype
        # 缓存：按 cluster_type 分组的忽略配置列表
        self._configs: List[MysqlInspectIgnore] = []
        self._cached_cluster_type: Optional[str] = None

    @staticmethod
    def _is_exclude_policy(policy: str) -> bool:
        """判断 policy 是否为排除策略（空或 'exclude' 都视为排除）"""
        return policy in ("", POLICY_EXCLUDE)

    def _load_configs(self, cluster_type: str):
        """加载并缓存指定 cluster_type 的忽略配置"""
        if self._cached_cluster_type == cluster_type and self._configs:
            return

        try:
            qs = MysqlInspectIgnore.objects.filter(subtype=self.subtype, is_enabled=True)
            if cluster_type:
                qs = qs.filter(cluster_type=cluster_type)
            self._configs = list(qs)
            self._cached_cluster_type = cluster_type
        except Exception as e:
            logger.error(f"Error loading ignore configs for subtype {self.subtype}: {e}")
            self._configs = []
            self._cached_cluster_type = cluster_type

    def _match_by_priority(self, bk_biz_id: int, cluster: str, cluster_type: str) -> Optional[MysqlInspectIgnore]:
        """
        按优先级从高到低匹配忽略配置，返回第一个匹配的配置。

        优先级规则：
          - 优先级 1（最高）：cluster 不为 '*' 且 bk_biz_id 不为 -1，精确匹配集群
          - 优先级 3（中等）：cluster='*'，匹配业务下所有集群
          - 优先级 5（最低）：bk_biz_id=-1，匹配所有业务
        """
        self._load_configs(cluster_type)

        # 按优先级分桶
        priority_1_matches: List[MysqlInspectIgnore] = []
        priority_3_matches: List[MysqlInspectIgnore] = []
        priority_5_matches: List[MysqlInspectIgnore] = []

        for config in self._configs:
            if config.bk_biz_id == BIZ_ALL:
                # 优先级 5：bk_biz_id=-1，所有业务
                priority_5_matches.append(config)
            elif config.cluster == CLUSTER_ALL and config.bk_biz_id == bk_biz_id:
                # 优先级 3：cluster='*'，匹配当前业务下所有集群
                priority_3_matches.append(config)
            elif config.cluster == cluster and config.bk_biz_id == bk_biz_id:
                # 优先级 1：精确匹配集群和业务
                priority_1_matches.append(config)

        # 从高到低返回第一个匹配
        for matches in [priority_1_matches, priority_3_matches, priority_5_matches]:
            if matches:
                return matches[0]

        return None

    def should_ignore_check(self, bk_biz_id: int, cluster: str) -> bool:
        """
        检查是否应该忽略某个集群的巡检（不需要 cluster_type）。

        Args:
            bk_biz_id: 业务ID
            cluster: 集群域名

        Returns:
            bool: True 表示应该忽略（跳过巡检），False 表示需要巡检
        """
        return self.should_ignore_check_cluster(bk_biz_id, cluster, cluster_type="")

    def should_ignore_check_cluster(self, bk_biz_id: int, cluster: str, cluster_type: str) -> bool:
        """
        检查是否应该忽略某个集群的巡检。

        匹配逻辑：
          1. 按优先级从高到低匹配配置
          2. 匹配到后根据 policy 决定：
             - policy 为空或 'exclude'：返回 True（忽略巡检）
             - policy 为 'include'：返回 False（需要巡检）
          3. 没有匹配到任何规则：返回 False（需要巡检）

        Args:
            bk_biz_id: 业务ID
            cluster: 集群域名
            cluster_type: 集群类型

        Returns:
            bool: True 表示应该忽略（跳过巡检），False 表示需要巡检
        """
        try:
            matched = self._match_by_priority(bk_biz_id, cluster, cluster_type)
            if matched is None:
                # 没有匹配到任何规则，需要巡检
                return False

            if self._is_exclude_policy(matched.policy):
                # exclude 策略：忽略巡检
                return True
            elif matched.policy == POLICY_INCLUDE:
                # include 策略：需要巡检
                return False
            else:
                # 未知 policy，按 exclude 处理
                logger.warning(f"Unknown policy '{matched.policy}' for config {matched}, treating as exclude")
                return True
        except Exception as e:
            logger.error(f"Error checking ignore config for cluster {cluster}: {e}")
            # 出错时不忽略，继续执行巡检
            return False
