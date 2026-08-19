# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

集群画像报告生成器 - 对外统一导出入口。

模块职责：
    - 面向调用方（celery 定时任务 / OpenAPI / 运维脚本）显式导出：
      基类 :class:`ClusterPortraitGenerator`、各 db_type 子类、结果 dataclass、业务异常
    - 调用方**明确知道自己要处理哪个 db_type**，直接 import 对应子类调用其 ``run()``：
      ``from backend.db_report.portrait.generator import MysqlClusterPortraitGenerator``
      ``result = MysqlClusterPortraitGenerator().run(cluster=..., report_from=..., report_to=...)``

设计要点：
    - **无反向注册 / 无分发中间层**：不使用 ``__init_subclass__``、不维护 ``db_type -> 子类`` 字典、
      不提供根据 cluster 反查子类的统一入口函数
    - 本 ``__init__`` 中的 import 均为**普通显式导出**，不带 ``# noqa: F401`` 副作用性质注释；
      子类模块被 import 后不产生任何除"定义类"以外的副作用
    - 与 ``portrait/sdk.py`` (ingest_summary) 完全解耦：
      * sdk.py 面向"单一维度巡检"追加写 PortraitDimensionSummary
      * generator/ 面向"整份集群画像报告"两阶段写 ClusterPortraitReport

边界：
    - 新增 DB 接入时：在 :mod:`generator` 下新建 ``xxx.py`` 子类模块，
      并在本 ``__init__`` 中显式追加 import + 更新 ``__all__``
    - 权限校验 / 定时调度 / 分布式锁 / 结果去重 均**不在本包职责**，由调用方兜底
"""
from backend.db_report.portrait.generator.base import (
    ClusterPortraitGenerator,
    ParsedPortraitResult,
    PortraitGenerateException,
    PortraitInvalidParamException,
    PortraitRunResult,
)
from backend.db_report.portrait.generator.mysql import (
    MysqlClusterPortraitGenerator,
    TendbClusterClusterPortraitGenerator,
)

__all__ = [
    # 基类与结果 / 中间态 dataclass
    "ClusterPortraitGenerator",
    "PortraitRunResult",
    "ParsedPortraitResult",
    # 业务异常
    "PortraitGenerateException",
    "PortraitInvalidParamException",
    # 各 db_type 子类（调用方直接 import 使用）
    "MysqlClusterPortraitGenerator",
    "TendbClusterClusterPortraitGenerator",
]
