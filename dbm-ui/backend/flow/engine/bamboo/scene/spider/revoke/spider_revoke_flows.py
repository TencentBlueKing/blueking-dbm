# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

TenDBCluster 部署单据（SPIDER_CLUSTER_APPLY）主机退回顶层编排。

承担 TERMINATED 后的 revoke 顶层入口；差异化仅通过 ``EXTRACTOR_CLASS`` + ``_LOG_PREFIX``
两个类属性表达，编排骨架完全继承 :class:`MysqlRevokeFlowBase`。姐妹实现见
``backend/flow/engine/bamboo/scene/mysql/revoke/mysql_revoke_flows.py``。
"""
from backend.flow.engine.bamboo.scene.mysql.revoke.base import MysqlRevokeFlowBase
from backend.flow.engine.bamboo.scene.spider.revoke.extractors.tendb_cluster_apply import TenDBClusterApplyExtractor


class TenDBClusterApplyRevokeFlow(MysqlRevokeFlowBase):
    """TenDBCluster 部署单据（SPIDER_CLUSTER_APPLY）主机退回编排。"""

    EXTRACTOR_CLASS = TenDBClusterApplyExtractor
    _LOG_PREFIX: str = "TenDBClusterApplyRevokeFlow"
