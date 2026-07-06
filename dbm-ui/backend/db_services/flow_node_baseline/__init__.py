# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

flow_node_baseline 领域包（Service 层）：流程节点耗时基线的采集、归一化、聚合与顶层编排。

包内模块：
  - constants           常量与配置（清洗正则、阈值、LLM prompt 模板）
  - name_cleaner        NameCleaner：无损正则清洗
  - name_normalizer     NameNormalizer：alias 缓存 + LLM 语义匹配
  - sample_collector    FlowSampleCollector：从 flow_tree / flow_node 拉取样本
  - baseline_aggregator BaselineAggregator：Welford + 分位数聚合
  - baseline_service    FlowBaselineService：顶层编排（存量 / 增量 / 修复共用）

上下游入口（本包只做业务逻辑，不直接被 celery 调度器发现）：
  - 存量 / 修复入口：backend/db_periodic_task/management/commands/init_flow_node_baseline.py
  - 增量入口：backend/db_periodic_task/local_tasks/flow_node_baseline/task.py
                （celery 任务薄壳，通过 register_periodic_task 注册；task name 与
                 __module__ 强绑定并持久化到 DBPeriodicTask，故必须留在 local_tasks 下）

架构约束：
  - 本包为纯 Service 层，禁止 import celery / register_periodic_task 相关符号
  - 上游 Command / celery 任务壳统一 import `backend.db_services.flow_node_baseline.baseline_service`
  - 与 `backend.db_periodic_task.local_tasks` 的 CI 隔离规则相容
    （见 backend/core/translation/language_finder.py 的 IllegalImportPaths）
"""
