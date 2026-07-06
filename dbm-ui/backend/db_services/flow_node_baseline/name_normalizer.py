# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

NameNormalizer：flow 节点名称归一化器。

模块职责：
  - 对每条 (ticket_type, component_code, raw_name) 输出稳定的 normalized_name
  - 三级决策链：正则清洗 → alias 表精准匹配 → 调 LLM 语义匹配 → 写回 alias 表
  - 复用 dbm_aiagent.agent.handlers.AgentHandler 作为 LLM 通道
  - LLM 结果持久化到 FlowNodeNameAlias，长期复用避免重复调用

上下游边界：
  - 上游：BaselineAggregator 逐条样本调用 normalize() 获取归一化 name
  - 下游：FlowNodeNameAlias（读写）、AgentHandler（LLM 调用）、NameCleaner（清洗）

线程安全：
  - 单实例内部有 in-memory 缓存 (_local_alias_cache)，读写用 lock 保护
  - 建议单进程复用同一实例；跨进程各自维护独立缓存无一致性问题（DB 是 source of truth）

LLM 不可用时的降级行为（简述，详见 constants.py "二、name 归一化"章节）：
  - 单次失败：写 LLM_FALLBACK + needs_review=True，normalized_name = cleaned_name
  - 全局不可用：新 cleaned_name 都各成一类，基线桶会膨胀；
    CATEGORIES_WARN_THRESHOLD / HARD_LIMIT 兜底告警与熔断
  - 恢复后**不会自动纠正**：alias 表命中缓存直接返回旧记录；
    DBA 需先清理 match_source='llm_fallback' 的记录，再触发 rebuild/repair
  - 当前不提供"主动关闭 LLM"的运维开关，需要时请直接停用相关定时任务
"""
import json
import logging
import re
import threading
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from django.db import transaction
from django.db.models import F
from django.utils import timezone

from backend.db_report.models import FlowNodeNameAlias, NameMatchSource
from backend.db_services.flow_node_baseline.constants import (
    CATEGORIES_HARD_LIMIT,
    CATEGORIES_WARN_THRESHOLD,
    LLM_CALL_RETRY_TIMES,
    LLM_CALL_TIMEOUT_SECONDS,
    LLM_JSON_EXTRACT_PATTERN,
    LLM_LOW_CONFIDENCE_THRESHOLD,
    LLM_NAME_MATCH_PROMPT,
)
from backend.db_services.flow_node_baseline.name_cleaner import NameCleaner
from backend.dbm_aiagent.agent.constants import DBMAgentCode
from backend.dbm_aiagent.agent.handlers import AgentHandler

logger = logging.getLogger("root")


@dataclass(frozen=True)
class NormalizeResult:
    """归一化结果的结构化返回值。

    :ivar normalized_name: 最终归一化 name（作为基线四维 key 之一）
    :ivar cleaned_name: NameCleaner 清洗结果（供上游追踪使用）
    :ivar match_source: 归一化决策来源（NameMatchSource 值）
    :ivar hit_alias_cache: 是否命中 alias 表缓存（性能观测用）
    """

    normalized_name: str
    cleaned_name: str
    match_source: str
    hit_alias_cache: bool


class _LLMSemanticMatcher:
    """LLM 语义匹配器：仅负责一次"新 name → 已有类别"的判断。

    职责：
      - 组装 prompt 并调用 AgentHandler
      - 解析 LLM JSON 输出，返回结构化匹配结果
      - 处理超时 / 解析失败 / 低置信度等边界

    使用方式：
        matcher = _LLMSemanticMatcher()
        result = matcher.match(ticket_type, code, cleaned_name, existing_names)
        # result 形如 {"matched": True, "matched_name": "...", "confidence": 0.9, "reasoning": "..."}

    线程安全：是（无实例状态，AgentHandler 内部各自维护会话）
    """

    #: 使用的智能体 code；主智能体 DBM 支持通用问答
    _AGENT_CODE: DBMAgentCode = DBMAgentCode.TASK_GUARDIAN

    def match(
        self,
        ticket_type: str,
        component_code: str,
        cleaned_name: str,
        existing_names: List[str],
    ) -> Dict:
        """执行一次 LLM 语义匹配。

        :param ticket_type: 单据类型
        :param component_code: 组件代码
        :param cleaned_name: 待判断的清洗后 name
        :param existing_names: 该 (tt, code) 下已有的归一化 name 列表；调用方应传入 top-N
        :return: dict，字段 matched/bool、matched_name/str|None、confidence/float、reasoning/str
                 LLM 失败时返回 {"matched": False, "matched_name": None, "confidence": 0.0, "reasoning": "<错误原因>"}
        边界：
          - existing_names 为空 → 直接返回不匹配（调用方应避免此调用）
          - LLM 超时 / JSON 解析失败 → 返回 matched=False + reasoning 携带错误
          - 重试次数由 LLM_CALL_RETRY_TIMES 控制
        """
        if not existing_names:
            return {
                "matched": False,
                "matched_name": None,
                "confidence": 0.0,
                "reasoning": "no existing categories",
            }

        prompt: str = self._build_prompt(ticket_type, component_code, cleaned_name, existing_names)

        # 首次 + 重试；最多共 (LLM_CALL_RETRY_TIMES + 1) 次
        last_error: str = ""
        for attempt in range(LLM_CALL_RETRY_TIMES + 1):
            try:
                raw_response: str = self._call_llm(prompt)
                parsed: Dict = self._parse_response(raw_response, existing_names)
                return parsed
            except Exception as err:
                last_error = f"attempt={attempt} err={err}"
                logger.warning(
                    "[NameNormalizer] LLM match failed, tt=%s code=%s name=%s attempt=%d err=%s",
                    ticket_type,
                    component_code,
                    cleaned_name,
                    attempt,
                    err,
                )

        return {
            "matched": False,
            "matched_name": None,
            "confidence": 0.0,
            "reasoning": f"llm call failed: {last_error}",
        }

    @staticmethod
    def _build_prompt(
        ticket_type: str,
        component_code: str,
        cleaned_name: str,
        existing_names: List[str],
    ) -> str:
        """按 constants.LLM_NAME_MATCH_PROMPT 模板组装 prompt。

        设计说明：
          - 候选类别不再做 Top-N 截断，直接全量传入
          - 上游 _get_existing_categories 已在超过 CATEGORIES_HARD_LIMIT 时抛异常
            熔断，此处保证到达此处时候选规模一定在可控范围内
          - 编号从 1 开始，对齐 LLM 训练语料中"1-based 列表"的主流分布
        """
        categories_block: str = "\n".join(f"{idx + 1}. {name}" for idx, name in enumerate(existing_names))

        return LLM_NAME_MATCH_PROMPT.format(
            ticket_type=ticket_type,
            component_code=component_code,
            existing_categories=categories_block,
            cleaned_name=cleaned_name,
        )

    def _call_llm(self, prompt: str) -> str:
        """调用 AgentHandler 获取 LLM 原始响应文本。"""
        start_ts: float = time.time()
        response_text: str = AgentHandler.ask_agent_with_content(
            agent_code=self._AGENT_CODE,
            content=prompt,
            timeout=LLM_CALL_TIMEOUT_SECONDS,
        )
        elapsed_ms: int = int((time.time() - start_ts) * 1000)
        logger.debug("[NameNormalizer] LLM call elapsed=%dms len=%d", elapsed_ms, len(response_text or ""))
        return response_text or ""

    @staticmethod
    def _parse_response(raw_response: str, existing_names: List[str]) -> Dict:
        """从 LLM 输出中提取 JSON 结果并做字段规整。

        :param raw_response: LLM 原始文本，可能带 markdown 代码块或解释性文字
        :param existing_names: 已有类别，用于校验 matched_name 是否在集合内（防幻觉）
        :return: 已规整字段的 dict
        边界：
          - 未找到 JSON 块 → 抛 ValueError，由 match() 走重试
          - matched=True 但 matched_name 不在 existing_names → 视为幻觉，改为 matched=False
          - confidence 缺失 → 默认 0.0
        """
        # 先直接尝试 json.loads；LLM 若严格遵循 prompt 会输出纯 JSON
        text: str = raw_response.strip()
        # 剥离 markdown 代码块标记（```json ... ```）
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)

        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            # 兜底：用正则从长文本中提取第一个 JSON 对象
            match = LLM_JSON_EXTRACT_PATTERN.search(raw_response)
            if match:
                try:
                    payload = json.loads(match.group(0))
                except json.JSONDecodeError as err:
                    raise ValueError(f"llm response json parse failed: {err}") from err
            else:
                raise ValueError("llm response contains no JSON")

        if not isinstance(payload, dict):
            raise ValueError("llm response payload is not dict")

        matched: bool = bool(payload.get("matched", False))
        matched_name: Optional[str] = payload.get("matched_name")
        confidence: float = float(payload.get("confidence") or 0.0)
        reasoning: str = str(payload.get("reasoning") or "")

        # 反幻觉：LLM 声称匹配但给的名字不在候选集合内，视为不匹配
        if matched and (not matched_name or matched_name not in existing_names):
            logger.warning(
                "[NameNormalizer] LLM hallucination detected: matched_name=%s not in existing", matched_name
            )
            matched = False
            matched_name = None
            reasoning = f"hallucination filtered; original: {reasoning}"

        return {
            "matched": matched,
            "matched_name": matched_name,
            "confidence": confidence,
            "reasoning": reasoning,
        }


class NameNormalizer:
    """flow 节点名称归一化器（顶层入口）。

    三级决策链：
      1. NameCleaner 正则清洗 raw_name → cleaned_name
      2. 查 FlowNodeNameAlias 表；命中即返回缓存的 normalized_name
      3. 未命中：查同 (tt, code) 下已有类别集合
         - 集合为空 → 首次出现，直接以 cleaned_name 作为 normalized_name
         - 集合非空 → 调 LLM 判断是否属于已有类别
             - 匹配到某类别 → normalized_name = 该类别
             - 未匹配 → normalized_name = cleaned_name（新类别）
             - LLM 失败 → 走 fallback：normalized_name = cleaned_name + needs_review=True
      4. 结果写入 alias 表，供下次直接命中

    使用方式：
        normalizer = NameNormalizer()
        result = normalizer.normalize("MYSQL_ROLLBACK_EXERCISE", "mysql_exec_trans_file", "下发MySQL介质")
        # 使用 result.normalized_name 作为基线四维 key 的第 4 维

    线程安全：是（in-memory 缓存用 lock 保护；DB 操作走 Django ORM 事务）
    副作用：读写 FlowNodeNameAlias 表；调用 LLM
    边界：
      - raw_name 为空 → 返回空 normalized_name，match_source=first_seen
      - manual_locked=True 的记录：即使命中也不覆盖（保护人工设定）
      - 大批量场景可复用同一实例，in-memory 缓存能挡下大部分重复查询
    """

    def __init__(self) -> None:
        """无参构造；实例内部持有一个 NameCleaner + 一个 LLM 匹配器 + 一层内存缓存。"""
        self._cleaner: NameCleaner = NameCleaner()
        self._matcher: _LLMSemanticMatcher = _LLMSemanticMatcher()

        #: 内存 alias 缓存：{(ticket_type, code, cleaned_name): normalized_name}
        #: 单进程内多次 normalize 命中同一 key 时避免重复查 DB
        self._local_alias_cache: Dict[Tuple[str, str, str], str] = {}

        #: 内存已有类别缓存：{(ticket_type, code): [normalized_name, ...]}
        #: 用于 LLM 匹配时快速拿到候选集合，避免每条样本都查 DB
        self._local_categories_cache: Dict[Tuple[str, str], List[str]] = {}

        #: 保护上述两个缓存的读写锁
        self._cache_lock: threading.Lock = threading.Lock()

    # =========================================================================
    # 对外主入口
    # =========================================================================

    def normalize(self, ticket_type: str, component_code: str, raw_name: str) -> NormalizeResult:
        """归一化单条样本的 name（对外主入口）。

        :param ticket_type: 单据类型，非空
        :param component_code: 组件代码，非空；空 code 场景应由上游过滤
        :param raw_name: 原始节点名称
        :return: NormalizeResult，包含 normalized_name / cleaned_name / match_source / hit_alias_cache
        边界：
          - raw_name 为空 → 返回 normalized_name="" match_source=first_seen
          - alias 命中 → hit_alias_cache=True，不触发 LLM
          - 未命中且已有类别为空 → 首次出现路径，不触发 LLM
          - 未命中且已有类别非空 → 触发 LLM 匹配
        """
        cleaned_name: str = self._cleaner.clean(raw_name)
        if not cleaned_name:
            return NormalizeResult(
                normalized_name="",
                cleaned_name="",
                match_source=NameMatchSource.FIRST_SEEN.value,
                hit_alias_cache=False,
            )

        # 第 2 级：alias 缓存精准匹配
        cached: Optional[str] = self._get_alias_from_cache_or_db(ticket_type, component_code, cleaned_name)
        if cached is not None:
            self._touch_alias_hit(ticket_type, component_code, cleaned_name)
            return NormalizeResult(
                normalized_name=cached,
                cleaned_name=cleaned_name,
                match_source=NameMatchSource.LLM_MATCHED.value,  # 复用命中路径的 source 由 alias 表记录
                hit_alias_cache=True,
            )

        # 第 3 级：查已有类别集合，走 LLM 决策
        existing_names: List[str] = self._get_existing_categories(ticket_type, component_code)
        if not existing_names:
            # 首次出现：直接以 cleaned_name 作为 normalized_name
            self._persist_alias(
                ticket_type,
                component_code,
                cleaned_name,
                normalized_name=cleaned_name,
                match_source=NameMatchSource.FIRST_SEEN.value,
                confidence=None,
                reasoning="",
                needs_review=False,
            )
            return NormalizeResult(
                normalized_name=cleaned_name,
                cleaned_name=cleaned_name,
                match_source=NameMatchSource.FIRST_SEEN.value,
                hit_alias_cache=False,
            )

        # 已有类别非空：调 LLM
        llm_result: Dict = self._matcher.match(ticket_type, component_code, cleaned_name, existing_names)
        return self._resolve_and_persist_llm_result(
            ticket_type, component_code, cleaned_name, existing_names, llm_result
        )

    def clear_cache(self) -> None:
        """清空内存缓存；长时间运行场景（如全量回填）分批处理时可主动释放内存。"""
        with self._cache_lock:
            self._local_alias_cache.clear()
            self._local_categories_cache.clear()

    # =========================================================================
    # alias 表读写
    # =========================================================================

    def _get_alias_from_cache_or_db(self, ticket_type: str, component_code: str, cleaned_name: str) -> Optional[str]:
        """先查内存缓存，未命中再查 DB。

        :return: 命中时返回 normalized_name；未命中返回 None
        """
        cache_key: Tuple[str, str, str] = (ticket_type, component_code, cleaned_name)

        with self._cache_lock:
            hit: Optional[str] = self._local_alias_cache.get(cache_key)
            if hit is not None:
                return hit

        # DB 查询
        row: Optional[FlowNodeNameAlias] = (
            FlowNodeNameAlias.objects.filter(
                ticket_type=ticket_type,
                component_code=component_code,
                cleaned_name=cleaned_name,
            )
            .only("normalized_name")
            .first()
        )

        if row is None:
            return None

        # 回填内存缓存
        with self._cache_lock:
            self._local_alias_cache[cache_key] = row.normalized_name
        return row.normalized_name

    def _get_existing_categories(self, ticket_type: str, component_code: str) -> List[str]:
        """获取该 (tt, code) 下已存在的所有 normalized_name（去重）。

        :return: normalized_name 列表；正常业务下规模应 ≤ CATEGORIES_WARN_THRESHOLD
        边界：
          - 数量 > CATEGORIES_WARN_THRESHOLD → warning 日志（提示清洗规则可能漏参数）
          - 数量 > CATEGORIES_HARD_LIMIT → 抛 ValueError 熔断，避免打爆 LLM prompt
        """
        cache_key: Tuple[str, str] = (ticket_type, component_code)

        with self._cache_lock:
            cached: Optional[List[str]] = self._local_categories_cache.get(cache_key)
            if cached is not None:
                return list(cached)

        # 直接全量拉取；不做 hit_count 排序也不做 Top-N 截断：
        #   1. 单个 (tt, code) 下的语义类别数受 flow 编排约束，天然是有限集合
        #   2. cleaned_name 层面的分布近似均衡，"长尾 + Top-N" 假设不成立
        #   3. 静默截断会掩盖清洗规则漏参数 / LLM 误判造成的新桶爆炸问题
        distinct_names: List[str] = list(
            FlowNodeNameAlias.objects.filter(ticket_type=ticket_type, component_code=component_code)
            .values_list("normalized_name", flat=True)
            .distinct()
        )

        # 熔断：超过硬上限直接抛异常，交给上层 sample_collector / rebuild 记录失败
        if len(distinct_names) > CATEGORIES_HARD_LIMIT:
            raise ValueError(
                f"existing categories exceed hard limit: tt={ticket_type} "
                f"code={component_code} count={len(distinct_names)} "
                f"limit={CATEGORIES_HARD_LIMIT}; "
                f"check NameCleaner patterns / LLM misclassification"
            )

        # 告警：超过预期阈值打日志，提示排查清洗规则或已归一化类别
        if len(distinct_names) > CATEGORIES_WARN_THRESHOLD:
            logger.warning(
                "[NameNormalizer] categories count exceeds warn threshold: "
                "tt=%s code=%s count=%d threshold=%d; "
                "investigate cleaner rules or historical LLM decisions",
                ticket_type,
                component_code,
                len(distinct_names),
                CATEGORIES_WARN_THRESHOLD,
            )

        with self._cache_lock:
            self._local_categories_cache[cache_key] = distinct_names
        return list(distinct_names)

    def _persist_alias(
        self,
        ticket_type: str,
        component_code: str,
        cleaned_name: str,
        normalized_name: str,
        match_source: str,
        confidence: Optional[float],
        reasoning: str,
        needs_review: bool,
    ) -> None:
        """将归一化决策写入 alias 表，同步刷新内存缓存。

        使用 update_or_create 保证幂等；已存在且 manual_locked=True 的记录不被覆盖。
        """
        cache_key: Tuple[str, str, str] = (ticket_type, component_code, cleaned_name)
        cat_cache_key: Tuple[str, str] = (ticket_type, component_code)

        with transaction.atomic(using="report_db"):
            existing: Optional[FlowNodeNameAlias] = (
                FlowNodeNameAlias.objects.select_for_update()
                .filter(
                    ticket_type=ticket_type,
                    component_code=component_code,
                    cleaned_name=cleaned_name,
                )
                .first()
            )

            if existing is None:
                FlowNodeNameAlias.objects.create(
                    ticket_type=ticket_type,
                    component_code=component_code,
                    cleaned_name=cleaned_name,
                    normalized_name=normalized_name,
                    match_source=match_source,
                    llm_confidence=confidence,
                    llm_reasoning=reasoning,
                    needs_review=needs_review,
                    manual_locked=False,
                    hit_count=1,
                    last_hit_at=timezone.now(),
                )
            elif not existing.manual_locked:
                # 未被人工锁定，允许自动流程更新
                existing.normalized_name = normalized_name
                existing.match_source = match_source
                existing.llm_confidence = confidence
                existing.llm_reasoning = reasoning
                existing.needs_review = needs_review
                existing.hit_count = (existing.hit_count or 0) + 1
                existing.last_hit_at = timezone.now()
                existing.save(
                    update_fields=[
                        "normalized_name",
                        "match_source",
                        "llm_confidence",
                        "llm_reasoning",
                        "needs_review",
                        "hit_count",
                        "last_hit_at",
                    ]
                )
            else:
                # manual_locked=True：保留人工设定，仅刷新命中信息
                existing.hit_count = (existing.hit_count or 0) + 1
                existing.last_hit_at = timezone.now()
                existing.save(update_fields=["hit_count", "last_hit_at"])
                normalized_name = existing.normalized_name  # 上层缓存以人工设定为准

        # 更新内存缓存
        with self._cache_lock:
            self._local_alias_cache[cache_key] = normalized_name
            # 若创建了新类别，追加到 categories 缓存尾部（下次查询会自然刷新排序）
            categories: Optional[List[str]] = self._local_categories_cache.get(cat_cache_key)
            if categories is not None and normalized_name not in categories:
                categories.append(normalized_name)

    @staticmethod
    def _touch_alias_hit(ticket_type: str, component_code: str, cleaned_name: str) -> None:
        """alias 命中时刷新 hit_count / last_hit_at；非关键路径，出错仅告警不中断主流程。"""
        try:
            FlowNodeNameAlias.objects.filter(
                ticket_type=ticket_type,
                component_code=component_code,
                cleaned_name=cleaned_name,
            ).update(hit_count=models_f_incr(), last_hit_at=timezone.now())
        except Exception as err:
            logger.warning(
                "[NameNormalizer] touch alias hit failed, tt=%s code=%s name=%s err=%s",
                ticket_type,
                component_code,
                cleaned_name,
                err,
            )

    # =========================================================================
    # LLM 结果落地
    # =========================================================================

    def _resolve_and_persist_llm_result(
        self,
        ticket_type: str,
        component_code: str,
        cleaned_name: str,
        existing_names: List[str],
        llm_result: Dict,
    ) -> NormalizeResult:
        """根据 LLM 输出决定 normalized_name，并落库。

        决策矩阵（严格）：
          - matched=True 且 matched_name 命中候选 且 confidence >= LLM_LOW_CONFIDENCE_THRESHOLD
            → 合并到已有类别（needs_review=False）
          - matched=True 但 confidence < LLM_LOW_CONFIDENCE_THRESHOLD
            → **拒绝合并**：作为新类别落库，match_source=LLM_NEW_CLUSTER，
              同时 needs_review=True 保留 LLM 的 reasoning，供 DBA 事后核对
            —— 变更原因：低置信度合并会污染基线，且后续同 cleaned_name 会持续
              命中 alias 缓存吃错映射；宁可多一个类别，交由 DBA 人工介入
          - matched=False（含 LLM 失败降级） → 作为新类别落库
              LLM 失败时 match_source=LLM_FALLBACK 且 needs_review=True
        """
        matched: bool = bool(llm_result.get("matched", False))
        matched_name: Optional[str] = llm_result.get("matched_name")
        confidence: float = float(llm_result.get("confidence") or 0.0)
        reasoning: str = str(llm_result.get("reasoning") or "")

        # 分支 1：LLM 明确匹配到已有类别，且置信度达标 → 合并
        if matched and matched_name in existing_names and confidence >= LLM_LOW_CONFIDENCE_THRESHOLD:
            self._persist_alias(
                ticket_type,
                component_code,
                cleaned_name,
                normalized_name=matched_name,
                match_source=NameMatchSource.LLM_MATCHED.value,
                confidence=confidence,
                reasoning=reasoning,
                needs_review=False,
            )
            return NormalizeResult(
                normalized_name=matched_name,
                cleaned_name=cleaned_name,
                match_source=NameMatchSource.LLM_MATCHED.value,
                hit_alias_cache=False,
            )

        # 分支 2：LLM 声称匹配但置信度不足 → 拒绝合并，作为新类别落库
        # 保留 LLM reasoning + 低置信度作为审阅线索，DBA 可通过 needs_review 过滤审查
        low_confidence_reject: bool = matched and (matched_name in existing_names)
        if low_confidence_reject:
            logger.info(
                "[NameNormalizer] reject low-confidence merge: tt=%s code=%s name=%s "
                "target=%s confidence=%.2f threshold=%.2f",
                ticket_type,
                component_code,
                cleaned_name,
                matched_name,
                confidence,
                LLM_LOW_CONFIDENCE_THRESHOLD,
            )
            enriched_reasoning: str = (
                f"low_confidence_reject: llm_matched_to={matched_name} "
                f"confidence={confidence:.2f} threshold={LLM_LOW_CONFIDENCE_THRESHOLD:.2f}; "
                f"original: {reasoning}"
            )
            self._persist_alias(
                ticket_type,
                component_code,
                cleaned_name,
                normalized_name=cleaned_name,
                match_source=NameMatchSource.LLM_NEW_CLUSTER.value,
                confidence=confidence,
                reasoning=enriched_reasoning,
                needs_review=True,
            )
            return NormalizeResult(
                normalized_name=cleaned_name,
                cleaned_name=cleaned_name,
                match_source=NameMatchSource.LLM_NEW_CLUSTER.value,
                hit_alias_cache=False,
            )

        # 分支 3：LLM 判为新类别（含 LLM 调用失败降级）
        # reasoning 里含 "llm call failed" 说明是失败降级，归为 LLM_FALLBACK 并置 needs_review
        is_fallback: bool = "llm call failed" in reasoning
        source: str = NameMatchSource.LLM_FALLBACK.value if is_fallback else NameMatchSource.LLM_NEW_CLUSTER.value

        self._persist_alias(
            ticket_type,
            component_code,
            cleaned_name,
            normalized_name=cleaned_name,
            match_source=source,
            confidence=confidence if not is_fallback else None,
            reasoning=reasoning,
            needs_review=is_fallback,
        )
        return NormalizeResult(
            normalized_name=cleaned_name,
            cleaned_name=cleaned_name,
            match_source=source,
            hit_alias_cache=False,
        )


def models_f_incr():
    """返回 hit_count + 1 的 F 表达式；独立函数便于测试 mock。"""

    return F("hit_count") + 1
