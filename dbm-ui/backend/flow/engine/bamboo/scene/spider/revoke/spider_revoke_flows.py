# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

Spider（TenDBCluster）侧单据主机退回顶层编排集合。

本模块承载 13 个 :class:`MysqlRevokeFlowBase` 子类，每个对应一类 TERMINATED 单据的 revoke
顶层入口；差异化仅通过覆盖 ``EXTRACTOR_CLASS`` + ``_LOG_PREFIX`` 两个类属性表达，编排骨架
（进程扫描 → 组级判定 → 元数据清理 → 机器脚本清理）完全由基类复用。

接入单据清单（均为"会在资源池申请机器"的 spider 单据）：
  - 部署类：SPIDER_CLUSTER_APPLY（TenDBClusterApplyRevokeFlow）；
    回档系列临时集群部署（TenDBClusterRollbackTempApplyRevokeFlow，复用部署 Extractor）
  - 运维扩容类：SPIDER_ADD_NODES / SPIDER_SWITCH_NODES / SPIDER_CONF_UP_DOWN /
    SPIDER_MNT_APPLY / SPIDER_SLAVE_APPLY
  - DR/迁移/升级类：SPIDER_LAYER_DR / SPIDER_UPGRADE / MIGRATE_UPGRADE /
    MIGRATE_CLUSTER / NODE_REBALANCE / RESTORE_SLAVE

明确不接入（及其原因，改动前务必阅读）：
  - 回档执行 flow（``tendb_cluster_rollback_data``）：执行 flow 的 ticket_data 不含新机字段，
    且临时集群部署成功后机器已成为集群成员，其回收属于集群下架范畴（与
    ``TENDBCLUSTER_ROLLBACK_NEW_HOST`` 维持 recycle_skip 的理由一致），不自动退回
  - 本地升级系列（LOCAL_UPGRADE / REMOTE_UPGRADE / TDBCTL_UPGRADE）：不申请资源池机器
    （未注册 ``is_apply``，终止不会触发 RECYCLE_APPLY_HOST）
  - 重建/故障切换/缩容/下架等：不申请资源池机器

姐妹实现见 ``backend/flow/engine/bamboo/scene/mysql/revoke/mysql_revoke_flows.py``。
"""
from backend.flow.engine.bamboo.scene.mysql.revoke.base import MysqlRevokeFlowBase
from backend.flow.engine.bamboo.scene.spider.revoke.extractors import (
    SpiderAddNodesExtractor,
    SpiderLayerDisasterRecoverExtractor,
    SpiderMigrateClusterExtractor,
    SpiderMntApplyExtractor,
    SpiderNodeRebalanceExtractor,
    SpiderRestoreSlaveExtractor,
    SpiderSlaveApplyExtractor,
    SpiderSwitchNodesExtractor,
    SpiderUpgradeExtractor,
    TenDBClusterApplyExtractor,
    TenDBClusterMigrateUpgradeExtractor,
)


class TenDBClusterApplyRevokeFlow(MysqlRevokeFlowBase):
    """TenDBCluster 部署单据（SPIDER_CLUSTER_APPLY）主机退回编排。"""

    EXTRACTOR_CLASS = TenDBClusterApplyExtractor
    _LOG_PREFIX: str = "TenDBClusterApplyRevokeFlow"


class TenDBClusterRollbackTempApplyRevokeFlow(MysqlRevokeFlowBase):
    """TenDBCluster 回档临时集群部署单据（BUILD_INTO_NEW_CLUSTER 的前置部署 flow）主机退回编排。

    复用 :class:`TenDBClusterApplyExtractor`：临时部署 flow 的 ticket_data 与 SPIDER_CLUSTER_APPLY
    完全同构（``spider_ip_list`` + ``remote_group`` + 端口/域名，由
    ``tendb_fixpoint_rollback.py`` 的 ``get_cluster_apply_spec`` 从 resource_spec hosts 组装）；
    ``remote_group`` 的 slave 恒为 ``{}``（no_slave 异形架构），Extractor 已兼容跳过。
    """

    EXTRACTOR_CLASS = TenDBClusterApplyExtractor
    _LOG_PREFIX: str = "TenDBClusterRollbackTempApplyRevokeFlow"


class SpiderAddNodesRevokeFlow(MysqlRevokeFlowBase):
    """TenDBCluster 接入层扩容单据（SPIDER_ADD_NODES）主机退回编排。"""

    EXTRACTOR_CLASS = SpiderAddNodesExtractor
    _LOG_PREFIX: str = "SpiderAddNodesRevokeFlow"


class SpiderSwitchNodesRevokeFlow(MysqlRevokeFlowBase):
    """TenDBCluster 接入层替换单据（SPIDER_SWITCH_NODES）主机退回编排。"""

    EXTRACTOR_CLASS = SpiderSwitchNodesExtractor
    _LOG_PREFIX: str = "SpiderSwitchNodesRevokeFlow"


class SpiderConfUpDownRevokeFlow(MysqlRevokeFlowBase):
    """TenDBCluster 接入层升降配单据（SPIDER_CONF_UP_DOWN）主机退回编排。

    ticket_data 与 SPIDER_SWITCH_NODES 同构（flow 继承 switch），共用
    :class:`SpiderSwitchNodesExtractor`，仅日志前缀区分单据类型。
    """

    EXTRACTOR_CLASS = SpiderSwitchNodesExtractor
    _LOG_PREFIX: str = "SpiderConfUpDownRevokeFlow"


class SpiderMntApplyRevokeFlow(MysqlRevokeFlowBase):
    """TenDBCluster 运维节点扩容单据（SPIDER_MNT_APPLY）主机退回编排。"""

    EXTRACTOR_CLASS = SpiderMntApplyExtractor
    _LOG_PREFIX: str = "SpiderMntApplyRevokeFlow"


class SpiderSlaveApplyRevokeFlow(MysqlRevokeFlowBase):
    """TenDBCluster 只读接入层部署单据（SPIDER_SLAVE_APPLY）主机退回编排。"""

    EXTRACTOR_CLASS = SpiderSlaveApplyExtractor
    _LOG_PREFIX: str = "SpiderSlaveApplyRevokeFlow"


class SpiderLayerDisasterRecoverRevokeFlow(MysqlRevokeFlowBase):
    """TenDBCluster 接入层灾难重建单据（SPIDER_LAYER_DR）主机退回编排。"""

    EXTRACTOR_CLASS = SpiderLayerDisasterRecoverExtractor
    _LOG_PREFIX: str = "SpiderLayerDisasterRecoverRevokeFlow"


class SpiderUpgradeRevokeFlow(MysqlRevokeFlowBase):
    """TenDBCluster 接入层迁移升级单据（SPIDER_UPGRADE）主机退回编排。"""

    EXTRACTOR_CLASS = SpiderUpgradeExtractor
    _LOG_PREFIX: str = "SpiderUpgradeRevokeFlow"


class TenDBClusterMigrateUpgradeRevokeFlow(MysqlRevokeFlowBase):
    """TenDBCluster 存储层迁移升级单据（MIGRATE_UPGRADE）主机退回编排。"""

    EXTRACTOR_CLASS = TenDBClusterMigrateUpgradeExtractor
    _LOG_PREFIX: str = "TenDBClusterMigrateUpgradeRevokeFlow"


class SpiderMigrateClusterRevokeFlow(MysqlRevokeFlowBase):
    """TenDBCluster 主从成对迁移单据（MIGRATE_CLUSTER）主机退回编排。"""

    EXTRACTOR_CLASS = SpiderMigrateClusterExtractor
    _LOG_PREFIX: str = "SpiderMigrateClusterRevokeFlow"


class SpiderNodeRebalanceRevokeFlow(MysqlRevokeFlowBase):
    """TenDBCluster 存储层重均衡单据（NODE_REBALANCE）主机退回编排。"""

    EXTRACTOR_CLASS = SpiderNodeRebalanceExtractor
    _LOG_PREFIX: str = "SpiderNodeRebalanceRevokeFlow"


class SpiderRestoreSlaveRevokeFlow(MysqlRevokeFlowBase):
    """TenDBCluster Slave 新机重建单据（RESTORE_SLAVE）主机退回编排。"""

    EXTRACTOR_CLASS = SpiderRestoreSlaveExtractor
    _LOG_PREFIX: str = "SpiderRestoreSlaveRevokeFlow"
