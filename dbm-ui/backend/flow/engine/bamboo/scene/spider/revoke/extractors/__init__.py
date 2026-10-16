# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

主机退回资源池 · 单据专属 Extractor 集合。

模块职责：
  - 定义 Extractor 抽象基类 :class:`HostExtractor`
  - 各单据类型（部署类 TenDBCluster，运维类 主从迁移 等）实现自己的 Extractor 子类
  - Extractor 只负责从 ticket_data 提取 ResourceGroup 列表，不做任何判定或副作用

契约：
  - Extractor 只提取 ``apply_infos`` / ``infos`` 里"本单从资源池新申领"的机器，不涉及老集群成员机
  - 机器角色由 Extractor 根据 ticket_data 字段名硬编码指定
  - 字段非法 / 缺失一律抛 :class:`NormalTenDBFlowException`，由上层 revoke_flow 顶层 try/except 兜底
"""

from backend.flow.engine.bamboo.scene.spider.revoke.extractors.tendb_cluster_apply import TenDBClusterApplyExtractor

#: 包公共 API：对外暴露抽象基类 + 单据专属 Extractor；
#: 子模块内部辅助函数 / 常量（如 _cluster_meta.py）不进入公共 API，调用方必须走子模块全路径
__all__: list[str] = [
    "TenDBClusterApplyExtractor",
]
