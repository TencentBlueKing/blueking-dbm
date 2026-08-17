# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

MySQL 侧单据主机退回顶层编排集合。

本模块承载 7 个 :class:`MysqlRevokeFlowBase` 子类，每个对应一类 TERMINATED 单据的 revoke
顶层入口；差异化仅通过覆盖 ``EXTRACTOR_CLASS`` + ``_LOG_PREFIX`` 两个类属性表达，编排骨架
（进程扫描 → 组级判定 → 元数据清理 → 机器脚本清理）完全由基类复用。
"""
from backend.flow.engine.bamboo.scene.mysql.revoke.base import MysqlRevokeFlowBase
from backend.flow.engine.bamboo.scene.mysql.revoke.extractors import (
    MysqlAddSlaveExtractor,
    MysqlHaApplyExtractor,
    MysqlMigrateClusterExtractor,
    MysqlProxyAddExtractor,
    MysqlProxySwitchExtractor,
    MysqlRestoreSlaveExtractor,
    MysqlSingleApplyExtractor,
)


class MysqlSingleApplyRevokeFlow(MysqlRevokeFlowBase):
    """TenDBSingle 部署单据（MYSQL_SINGLE_APPLY）主机退回编排。"""

    EXTRACTOR_CLASS = MysqlSingleApplyExtractor
    _LOG_PREFIX: str = "MysqlSingleApplyRevokeFlow"


class MysqlHaApplyRevokeFlow(MysqlRevokeFlowBase):
    """TenDBHA 部署单据（MYSQL_HA_APPLY）主机退回编排。"""

    EXTRACTOR_CLASS = MysqlHaApplyExtractor
    _LOG_PREFIX: str = "MysqlHaApplyRevokeFlow"


class MysqlMigrateClusterRevokeFlow(MysqlRevokeFlowBase):
    """TenDBHA 主从迁移单据（MYSQL_MIGRATE_CLUSTER）主机退回编排。"""

    EXTRACTOR_CLASS = MysqlMigrateClusterExtractor
    _LOG_PREFIX: str = "MysqlMigrateClusterRevokeFlow"


class MysqlRestoreSlaveRevokeFlow(MysqlRevokeFlowBase):
    """TenDBHA Slave 新机重建单据（MYSQL_RESTORE_SLAVE）主机退回编排。"""

    EXTRACTOR_CLASS = MysqlRestoreSlaveExtractor
    _LOG_PREFIX: str = "MysqlRestoreSlaveRevokeFlow"


class MysqlAddSlaveRevokeFlow(MysqlRevokeFlowBase):
    """TenDBHA Slave 添加单据（MYSQL_ADD_SLAVE）主机退回编排。"""

    EXTRACTOR_CLASS = MysqlAddSlaveExtractor
    _LOG_PREFIX: str = "MysqlAddSlaveRevokeFlow"


class MysqlProxyAddRevokeFlow(MysqlRevokeFlowBase):
    """TenDBHA Proxy 扩容单据（MYSQL_PROXY_ADD）主机退回编排。"""

    EXTRACTOR_CLASS = MysqlProxyAddExtractor
    _LOG_PREFIX: str = "MysqlProxyAddRevokeFlow"


class MysqlProxySwitchRevokeFlow(MysqlRevokeFlowBase):
    """TenDBHA Proxy 整机替换单据（MYSQL_PROXY_SWITCH）主机退回编排。"""

    EXTRACTOR_CLASS = MysqlProxySwitchExtractor
    _LOG_PREFIX: str = "MysqlProxySwitchRevokeFlow"
