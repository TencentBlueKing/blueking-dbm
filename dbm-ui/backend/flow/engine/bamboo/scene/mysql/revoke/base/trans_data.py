# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

主机退回资源池 · 通用 trans_data 容器。

模块职责：
  - 为所有 revoke 类顶层流程（TenDBHA / TenDBSingle / TenDBCluster / Redis 等）提供统一的
    ``init_trans_data_class`` 实例
  - 定义"单组子流程内"跨 Service 传递的**静态字段契约**

设计要点：
  - **利用 SubProcess 天然隔离**：bamboo 每个 SubProcess 各自持有独立的 ``trans_data``
    实例；顶层 revoke_flow 把每组构造成独立 SubProcess 并行执行 → 组间字段互不干扰。
    因此所有字段用**静态名**即可（无需 ``__group_id`` 后缀），字段契约清晰、可静态检查。
  - **只承载"单组子流程内"的状态传递**：跨组累计的可回收机器列表通过
    :class:`FlowOutputHandler(RecycleOutputContext.ToResourceSerializer)` 落地到
    FlowSummary 表（跨 SubProcess 天然共享），不再走 trans_data。
  - **不用 frozen / slots**：Service 通过 ``setattr(trans_data, field, value)`` 赋值，
    frozen 会禁止赋值；slots 与 dataclass 组合有兼容性坑，无必要。
"""
from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class RevokeTransData:
    """revoke 流程通用 trans_data 容器（跨 apply / expand / replace / rebuild 场景）。

    职责：
      - 顶层 revoke_flow 通过 ``run_pipeline(init_trans_data_class=RevokeTransData())``
        为 pipeline 注入 trans_data 初值
      - 每个组的独立 SubProcess 会持有本容器的独立副本，组内 4 段 Service 通过下列
        静态字段串联

    段间传递契约（同一 SubProcess 内按顺序读写）：
      - :attr:`host_process_check`     段 1 → 段 2 · 进程扫描结果 ``{ip: <ctx_dict>}``
        （由 :class:`MySQLHostProcessCheckService` 以 APPEND 模式写入，
        :class:`ResourceGroupJudgeService` 按 ip 索引消费）
      - :attr:`group_verdict`          段 2 → 段 3 / 段 4 · 组级判定结果 dict
        （由 :class:`ResourceGroupJudgeService` 写入 :func:`asdict` 序列化后的
        GroupVerdict；段 3 据此遍历 F3 evidence 清元数据，段 4 据此遍历
        F4=yes 筛选 exec_ips）
      - :attr:`group_verdict_decision` 段 2 → 段 3 / 段 4 · 组决策字符串
        （``group_recycle`` / ``group_manual`` 等；供下游 Service 分支判断，
        避免嵌套 dict 取值）

    契约演进说明（历史字段退场）：
      - ``pending_clear_ips``（旧：段 3 → 段 4）已废弃；段 4 现基于 :attr:`group_verdict`
        自主筛选 F4=yes 的 IP，消除"同一语义两个字段"的冗余
      - FlowSummary 写入职责已从段 3 迁移至段 2 Judge（判决产出瞬间同步落盘），
        不再是 trans_data 字段，由 :class:`FlowOutputHandler` 跨 SubProcess 共享

    线程安全：非线程安全（bamboo 单实例执行）

    边界：
      - 所有字段有默认值，未被上游赋值时消费方读到"零值"（{} / "" / []），
        Service 内部按"零值 → no-op"处理，不抛异常
    """

    #: 段 1 → 段 2 · 进程扫描结果 dict；结构 ``{ip: <ctx_dict>}``；
    #: 由 MySQLHostProcessCheckService（APPEND 模式）写入
    #: 最小示例： ``{"1.1.1.1": {"process_list": [...], "ports": [...]}, ...}``
    host_process_check: Dict[str, Any] = field(default_factory=dict)

    #: 段 2 → 段 3 / 段 4 · 组级判定结果 dict（asdict(GroupVerdict) + 枚举转 value 后的结构）
    #: 最小示例： ``{"group": {...}, "decision": "group_recycle",
    #:            "verdicts": [{"unit": {"ip": ..., "bk_host_id": ..., "bk_cloud_id": ...},
    #:                          "facts": {"f3_dbm_residue": {"state": "yes", "evidence": {...}},
    #:                                    "f4_process": {"state": "yes"}}, ...}]}``
    group_verdict: Dict[str, Any] = field(default_factory=dict)

    #: 段 2 → 段 3 / 段 4 · 组决策字符串（GroupDecision.value：group_recycle / group_manual / ...）
    #: 最小示例： ``"group_recycle"``
    group_verdict_decision: str = ""
