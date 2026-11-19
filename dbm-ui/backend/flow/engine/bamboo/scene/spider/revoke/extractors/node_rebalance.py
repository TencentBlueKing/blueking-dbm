# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

TenDBCluster 存储层重均衡单据（NODE_REBALANCE）· 候选主机 Extractor。

NODE_REBALANCE 与 MIGRATE_UPGRADE 的 ticket_data 完全同构（``cluster_id`` /
``remote_group[{master,slave}]`` / ``remote_shard_num``；mysql 端口同为
``range(20000, 20000 + remote_shard_num)``），两单据共用同一个 Extractor 实现
（见 ``migrate_upgrade.py``）；本模块保留与单据类型对应的子类，供
``SpiderNodeRebalanceRevokeFlow`` 引用。
"""
from backend.flow.engine.bamboo.scene.spider.revoke.extractors.migrate_upgrade import (
    TenDBClusterMigrateUpgradeExtractor,
)


class SpiderNodeRebalanceExtractor(TenDBClusterMigrateUpgradeExtractor):
    """NODE_REBALANCE 单据的候选主机 Extractor：与迁移升级单据共用实现（子类）。

    仅覆盖 ``_err_prefix``：顶层兜底日志 / 异常消息中直接区分单据类型
    （父类默认为 ``[TenDBClusterMigrateUpgradeExtractor]``，对 NODE_REBALANCE
    单据有误导性）；提取逻辑完全继承父类，无任何行为差异。

    线程安全：是（无实例状态）
    """

    #: 日志/异常前缀：按单据类型定位来源（父类实现统一消费 self._err_prefix）
    _err_prefix: str = "[SpiderNodeRebalanceExtractor]"
