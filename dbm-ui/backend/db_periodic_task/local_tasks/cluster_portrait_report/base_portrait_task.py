# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

集群画像 DispatchTask 通用基类 —— worker 唯一动作是调 :meth:`ClusterPortraitGenerator.run`。

模块职责：
    - 定义 :class:`PortraitReportTaskBase`：所有 db_type 画像 DispatchTask 的抽象基类
    - 沉淀通用逻辑：work_item 身份 / on_before_execute / execute 入口 / status→outcome 映射
    - 子类只需实现 1 个钩子（``resolve_generator``）+ 填 1 个类属性（``config_cls``）
      + 加 1 个 ``@register_dispatch_task`` 装饰器，即可完成一个新 db_type 画像消费者的接入

设计要点：
    - **绝不拆解生成器逻辑**：worker 侧只调 :meth:`ClusterPortraitGenerator.run`，
      入参校验 / init_record 占位 / build_content / _call_agent / parse_response /
      _persist_success / _persist_failure 全部由 :meth:`ClusterPortraitGenerator.run` 内部承担；
    - **429 自动 requeue**：:meth:`ClusterPortraitGenerator.run` 遇到 AI 网关 HTTP 429 时
      会**先回滚占位记录再抛** :class:`PortraitRateLimitException`；本 execute 捕获后转
      :attr:`DispatchOutcomeType.REQUEUED`（+ ``should_requeue=True`` + cooldown），
      DispatchQueue 框架自动冷却后 requeue；
    - **不继承 AITask**：AITask 天然绑 AITaskQueue（ai namespace），本框架要独立
      ``cluster_portrait`` namespace，直接继承 DispatchTask；
    - **producer 侧不做 init_record**：占位记录由 :meth:`ClusterPortraitGenerator.run`
      内部落，避免 producer / worker 两侧存在双写点。

边界：
    - :meth:`ClusterPortraitGenerator.run` 对入参有 aware datetime 硬约束；本 execute 从
      item 中反序列化 ``datetime.fromisoformat`` 会自动恢复 tzinfo，只要 producer 侧
      构造的是 aware datetime 即可满足契约；
    - 单集群执行超时 = ``config.execution_timeout_seconds``（画像默认 540s），
      超时后 dispatch 框架会 reap 该 job 并释放 reserved slot。
"""
import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, Optional

from backend.db_meta.models import Cluster
from backend.db_periodic_task.dispatch.base import DispatchTask
from backend.db_periodic_task.dispatch.outcomes import DispatchOutcome, DispatchOutcomeType
from backend.db_periodic_task.dispatch.portrait_queue import PortraitQueue
from backend.db_report.portrait.generator.base import (
    STATUS_AI_ERROR,
    STATUS_PARSE_ERROR,
    STATUS_SUCCESS,
    ClusterPortraitGenerator,
    PortraitInvalidParamException,
    PortraitRateLimitException,
    PortraitRunResult,
)

logger = logging.getLogger("root")

#: worker 侧统一 operator，用于 :meth:`ClusterPortraitGenerator.run` 的 ``operator`` 入参
#: 语义：ClusterPortraitReport.creator / updater 审计字段的默认值
_WORKER_OPERATOR: str = "system"


class PortraitReportTaskBase(DispatchTask, ABC):
    """集群画像 DispatchTask 通用基类。

    职责：
        - worker 唯一动作是调 :meth:`ClusterPortraitGenerator.run`；不拆解生成器逻辑
        - 沉淀通用扩展点：``work_item_id`` / ``work_item_data`` / ``on_before_execute``
        - 通过 1 个抽象钩子 :meth:`resolve_generator` 将 db_type 专属知识下放给子类

    子类接入模板::

        @register_dispatch_task(
            config_cls=XxxPortraitReportConfig,
            metadata={"db_type": "xxx"},
        )
        class XxxPortraitReportTask(PortraitReportTaskBase):
            config_cls = XxxPortraitReportConfig

            def resolve_generator(self, cluster):
                return XxxClusterPortraitGenerator()

    线程安全：是（execute 内部只用局部变量与生成器无状态方法）
    边界：
        - 集群不存在（``Cluster.DoesNotExist``）-> 通过 :meth:`on_before_execute` 提前 skip；
        - 生成器 429 限速 -> :class:`PortraitRateLimitException` -> REQUEUED outcome；
        - 生成器返回 status=success -> SUCCESS outcome；
        - 生成器返回 status=ai_error / parse_error -> SUCCESS outcome（已通过
          ClusterPortraitReport.status 落库表达失败态，不需要 dispatch 层 requeue）。
    """

    #: 所有画像消费者共用 PortraitQueue（namespace=cluster_portrait），子类无需覆盖
    queue_cls = PortraitQueue

    # ------------------------------------------------------------------
    # 抽象钩子：子类必须实现（db_type 专属知识）
    # ------------------------------------------------------------------

    @abstractmethod
    def resolve_generator(self, cluster: Cluster) -> ClusterPortraitGenerator:
        """根据集群实例返回对应的画像生成器。

        功能说明：
            - 子类通常直接返回一个 db_type 专属生成器实例；
            - MySQL 家族由于同一 db 组件下有多个 cluster_type（TenDBSingle /
              TenDBHA 用 mysql 生成器；TenDBCluster 用 tendbcluster 生成器），
              子类内部可根据 ``cluster.cluster_type`` 再做二次派发。

        :param cluster: 已从 DB 拉起的 :class:`Cluster` 实例；cluster_type 可读取
        :return: :class:`ClusterPortraitGenerator` 实例；后续统一调 ``.run()``；
                 生成器的 ``agent_code`` / ``dimension_enum`` 等类属性由生成器自己声明，
                 worker 不感知
        边界：
            - 子类返回的实例必须是**无状态的**；execute 内部只对它调一次 ``.run()``
        """

    # ------------------------------------------------------------------
    # DispatchTask 扩展点：work_item 身份与上下文（通用实现）
    # ------------------------------------------------------------------

    def work_item_id(self, item: Any) -> str:
        """构造 dedupe 键：``cluster:{cluster_id}:{schedule_date}``。

        功能说明：
            - 语义："同集群同调度日期"仅入队一次；日期变更（次日）自然产生新 dedupe 键
            - 与 ``IdempotenceMode.DEDUPE`` 配合，复现旧 dispatcher 的"按集群+日期"防重锁

        :param item: producer 传入的 dict，必须包含 ``cluster_id`` / ``schedule_date``
        :return: 形如 ``"cluster:{cluster_id}:{YYYY-MM-DD}"`` 的字符串
        边界：
            - item 缺少字段 -> KeyError；producer 必须保证字段齐全，不做兜底默认值
            - 若未来某 db_type 需要更细粒度（如 shard 级），子类可 override
        """
        return f"cluster:{item['cluster_id']}:{item['schedule_date']}"

    def work_item_data(self, item: Any) -> Dict[str, Any]:
        """把 producer 的 item 原样落到 job 上下文，供 worker 侧读取。

        :param item: producer 构造的 dict（cluster_id / cluster_domain / schedule_date /
                     report_from_iso / report_to_iso）
        :return: dict 副本；dispatch 框架会 JSON 序列化后落 Redis
        边界：
            - 非 dict item 走兜底逻辑（画像 producer 只传 dict）
        """
        if isinstance(item, dict):
            return dict(item)
        return {"value": item}

    def on_before_execute(self, item: Any) -> Optional[str]:
        """出队前 stale-state 复核：集群若在 pending 期间被下架 / 删除 -> skip。

        功能说明：
            - 只做与 dispatch 层最相关的"集群仍存在"复核，节省一次无用的 AI 调用；
            - 其他状态（如集群 phase 变化）交由生成器 :meth:`.run` 内部处理，
              避免在 dispatch 层增加过多与业务耦合的判断。

        :param item: work_item_data 反序列化后的 dict
        :return: skip 原因字符串（触发 SKIPPED outcome）；返回 None 表示继续执行
        边界：
            - 未提供 ``cluster_id`` -> 返回 "invalid item: cluster_id missing"
        """
        cluster_id = item.get("cluster_id") if isinstance(item, dict) else None
        if not cluster_id:
            return "invalid item: cluster_id missing"
        if not Cluster.objects.filter(id=cluster_id).exists():
            return f"cluster not found: cluster_id={cluster_id}"
        return None

    # ------------------------------------------------------------------
    # DispatchTask 主入口：execute —— 唯一动作是调 generator.run()
    # ------------------------------------------------------------------

    def execute(
        self,
        item: Any,
        *,
        job=None,
        overrides: Optional[dict] = None,
    ) -> DispatchOutcome:
        """执行一条画像 job：调 :meth:`ClusterPortraitGenerator.run` 并映射 outcome。

        执行流程：
            1) 读取 item 中的 cluster_id / schedule_date / report_from_iso / report_to_iso；
            2) 获取 :class:`Cluster` 实例；不存在 -> 直接返回 ERROR outcome（不落记录，
               因为 :meth:`run` 未执行 -> 无占位记录待清理）；
            3) 子类钩子 :meth:`resolve_generator` -> ``generator.run(...)``；
            4) 按返回值 :class:`PortraitRunResult.status` 映射 :class:`DispatchOutcome`：
               * ``STATUS_SUCCESS`` -> :attr:`DispatchOutcomeType.SUCCESS`
               * ``STATUS_AI_ERROR`` / ``STATUS_PARSE_ERROR`` -> :attr:`DispatchOutcomeType.SUCCESS`
                 （失败态已通过 ClusterPortraitReport.status 落库表达，不需要 dispatch 层 requeue）；
            5) 捕获 :class:`PortraitRateLimitException` -> :attr:`DispatchOutcomeType.REQUEUED`
               + ``should_requeue=True`` + cooldown，让框架自动 requeue；
            6) 捕获 :class:`PortraitInvalidParamException` -> :attr:`DispatchOutcomeType.ERROR`
               （入参非法是**永久失败**，重试无意义）；
            7) 捕获其他未预期异常 -> :attr:`DispatchOutcomeType.ERROR`（ORM 异常等）。

        :param item: work_item_data 反序列化后的 dict
        :param job: dispatch 框架传入的 job；本方法不用
        :param overrides: submit-time overrides；当前不消费（保留形参以符合父类
                          :meth:`DispatchTask.execute` 契约，未来需要基于 submit
                          时覆盖配置执行时再消费）
        :return: :class:`DispatchOutcome`；outcome / elapsed_seconds / should_requeue 由本方法决定

        边界 / 异常：
            - 429 -> REQUEUED（唯一会 requeue 的分支）
            - 入参非法 / ORM 异常 -> ERROR
            - AI 语义失败 / 解析失败 -> SUCCESS（业务失败态已落库）
        """
        started_at: float = time.monotonic()

        # ---- 1) 从 item 读上下文 ----
        cluster_id: int = int(item["cluster_id"])
        schedule_date: str = str(item.get("schedule_date", ""))
        report_from: datetime = datetime.fromisoformat(item["report_from_iso"])
        report_to: datetime = datetime.fromisoformat(item["report_to_iso"])

        work_item_ref: str = f"cluster:{cluster_id}:{schedule_date}"

        # ---- 2) 拉集群实例；on_before_execute 已过滤删除态，这里防御性再取一次 ----
        cluster: Optional[Cluster] = Cluster.objects.filter(id=cluster_id).first()
        if cluster is None:
            logger.warning(
                "[portrait_task] cluster not found before run: cluster_id=%s work_item=%s",
                cluster_id,
                work_item_ref,
            )
            elapsed: float = time.monotonic() - started_at
            return DispatchOutcome(outcome=DispatchOutcomeType.ERROR, elapsed_seconds=elapsed)

        # ---- 3) 子类钩子选生成器；worker 唯一动作是调 .run() ----
        generator: ClusterPortraitGenerator = self.resolve_generator(cluster)

        try:
            result: PortraitRunResult = generator.run(
                cluster=cluster,
                report_from=report_from,
                report_to=report_to,
                dimensions=None,
                operator=_WORKER_OPERATOR,
            )
        except PortraitRateLimitException as exc:
            # 429 限速 -> 请求框架冷却后自动 requeue；占位记录已被 run() 内部回滚
            cooldown: int = max(1, int(self.config.requeue_cooldown_seconds))
            elapsed = time.monotonic() - started_at
            logger.warning(
                "[portrait_task] rate limited (HTTP 429): work_item=%s cooldown=%ds elapsed=%.2fs exc=%s",
                work_item_ref,
                cooldown,
                elapsed,
                exc,
            )
            return DispatchOutcome(
                outcome=DispatchOutcomeType.REQUEUED,
                error=exc,
                elapsed_seconds=elapsed,
                should_requeue=True,
                requeue_cooldown_seconds=cooldown,
                exhausted_outcome=DispatchOutcomeType.REQUEUE_EXHAUSTED,
            )
        except PortraitInvalidParamException as exc:
            # 入参非法是永久失败，重试无意义 -> ERROR
            elapsed = time.monotonic() - started_at
            logger.exception(
                "[portrait_task] invalid params: work_item=%s elapsed=%.2fs: %s",
                work_item_ref,
                elapsed,
                exc,
            )
            return DispatchOutcome(outcome=DispatchOutcomeType.ERROR, error=exc, elapsed_seconds=elapsed)
        except Exception as exc:  # noqa: BLE001 - 兜底：ORM / 未预期异常 -> ERROR
            elapsed = time.monotonic() - started_at
            logger.exception(
                "[portrait_task] unexpected error in generator.run: work_item=%s elapsed=%.2fs: %s",
                work_item_ref,
                elapsed,
                exc,
            )
            return DispatchOutcome(outcome=DispatchOutcomeType.ERROR, error=exc, elapsed_seconds=elapsed)

        # ---- 4) 按 PortraitRunResult.status 映射 outcome ----
        elapsed = time.monotonic() - started_at
        logger.info(
            "[portrait_task] execute done: work_item=%s cluster=%s record_id=%s " "status=%s score=%s elapsed=%.2fs",
            work_item_ref,
            cluster.immute_domain,
            result.record_id,
            result.status,
            result.score,
            elapsed,
        )

        # AI 语义失败 / 解析失败：已通过 ClusterPortraitReport.status 落库表达，
        # 不需要 dispatch 层 requeue；outcome 均视为 SUCCESS（job 已终结）
        if result.status in (STATUS_SUCCESS, STATUS_AI_ERROR, STATUS_PARSE_ERROR):
            return DispatchOutcome(outcome=DispatchOutcomeType.SUCCESS, elapsed_seconds=elapsed)

        # 未来若 generator 新增未知 status 值 -> 兜底为 ERROR，便于告警
        logger.error(
            "[portrait_task] unknown result.status=%s: work_item=%s record_id=%s",
            result.status,
            work_item_ref,
            result.record_id,
        )
        return DispatchOutcome(outcome=DispatchOutcomeType.ERROR, elapsed_seconds=elapsed)


__all__ = ("PortraitReportTaskBase",)
