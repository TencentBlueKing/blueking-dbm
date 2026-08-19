# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

集群画像 AI 返回文本的结构化解析器。

模块职责：
    - 把 :class:`AgentHandler.ask_agent_with_content` 返回的**自然语言/JSON 混杂文本**
      转换成结构化的 :class:`ParsedPortraitResult`（summary + share_url + score + ai_ok）
    - 提供**三级降级**策略，任何情况下都不抛异常给调用方（异常语义由基类 run() 管道处理）

AI 侧 JSON 契约（对应 system prompt 中定义）：
    {
        "ai_status": bool,           // true=画像生成成功；false=数据不足/内部错/拒答等
        "report_url": str,           // 报告详情页链接；成功时必填，失败时为空串
        "report_score": int,         // 报告健康分 0~100；失败时 -1
        "message": str               // 成功=报告摘要；失败=失败原因（一字段两义）
    }

字段名映射（AI 侧 → 内部）：
    ai_status  -> ai_ok       （bool，业务层"是否成功"判断依据）
    report_url -> share_url   （沿用既有内部命名，与 ClusterPortraitReport 对齐）
    report_score -> score
    message    -> summary     （既承载摘要，也承载失败原因）

设计要点：
    - 第 1 级：``[ai_result]...[ai_result]`` 标签抽取 + ``json.loads`` + JSON Schema 校验；
              命中 -> ``parsed_ok=True``，``ai_ok`` 采纳 AI 侧 ``ai_status``（可能 True 也可能 False）。
              标签契约与 ``CheckClusterAlarmForAIService`` 保持一致，用于绕开 LLM 冗余输出对
              直接 ``json.loads`` 的干扰（模型常在 JSON 前后夹杂 Markdown 代码块 / 思考过程等）。
    - 第 2 级：正则兜底提取 report_url（沿用 ``mysql_cluster_skew`` 的 URL 模式），
              剩余文本作为 summary，score=-1；命中 -> ``parsed_ok=True``, ``ai_ok=True``
              （视为"业务上可展示"，即便 AI 侧 JSON 结构不符）
    - 第 3 级：彻底解析失败；summary=原始文本截断，share_url="", score=-1，
              ``parsed_ok=False``, ``ai_ok=False``（由基类 run() 判定为 ``STATUS_PARSE_ERROR``）
    - ``score`` 归一化：非 int / 越界 -> ``-1`` + warning 日志；不阻塞
    - ``summary`` 语义分道：``ai_status=true`` 时**固定**为简短话术 :attr:`PortraitResponseParser.SUCCESS_SUMMARY_TEXT`
                          （成功路径无需保留过程细节，前端点 share_url 跳详情即可）；
                          ``ai_status=false`` 时取 AI 侧 message（作为失败原因）

边界：
    - 本类无 IO / DB 访问；纯文本转换；线程安全
    - summary 上限（软限制）由 :attr:`PortraitResponseParser.MAX_SUMMARY_CHARS` 控制
"""
import json
import logging
import re
from typing import Any, Dict, Optional

from django.utils.translation import gettext_lazy as _
from jsonschema.exceptions import ValidationError
from jsonschema.validators import validate

from backend import env
from backend.db_report.portrait.generator.base import ParsedPortraitResult

logger = logging.getLogger("root")

#: AI 返回 JSON 契约 schema：四字段固定 (ai_status/report_url/report_score/message)；
#  额外字段允许存在但不采纳；字段类型宽松（如 report_score 允许字符串数字，走 _normalize_score 归一化）
_PORTRAIT_JSON_SCHEMA: Dict[str, Any] = {
    "type": "object",
    "required": ["ai_status", "report_url", "report_score", "message"],
    "properties": {
        # bool：画像生成是否成功；false 时其它字段可能为占位
        "ai_status": {"type": "boolean"},
        # 报告详情页链接；成功时必填，失败时为空串
        "report_url": {"type": "string"},
        # 报告健康分；允许 int / float / 数字字符串，最终归一化为 int
        "report_score": {"type": ["integer", "number", "string"]},
        # 摘要 / 失败原因，一字段两义
        "message": {"type": "string"},
    },
}

#: report_url 正则兜底模式：匹配 ``<BK_SAAS_HOST>/ai-chat/share/<uuid>[/]``；用于 JSON 解析失败时抢救链接
#  该模式与 backend/db_periodic_task/local_tasks/mysql_cluster_skew/generate_report/tasks.py
#  中的 _SKEW_REPORT_SHARE_URL_RE 保持一致，避免各处正则风格漂移
_SHARE_URL_RE: re.Pattern = re.compile(
    rf"{re.escape(env.BK_SAAS_HOST.rstrip('/'))}/ai-chat/share/"
    r"([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})/?",
    re.IGNORECASE,
)

#: [ai_result] 标签块正则：从任意长度的自然语言中"抓出被标签围住的核心 JSON"。
#  与 ``backend/flow/plugins/components/collections/common/check_cluster_alarm_for_ai.py``
#  中 ``CheckClusterAlarmForAIService`` 使用的标签保持完全一致（开始 / 结束标签文本相同均为 ``[ai_result]``）。
#  使用非贪婪匹配 ``\{.+?\}`` + ``re.DOTALL``，确保：
#    1) 多标签块时只匹配"第一个成对块"，避免跨块串号；
#    2) JSON 内含换行（模型偶尔美化输出）时仍能正确匹配；
#    3) 标签内**必须**以 ``{`` 开头、以 ``}`` 结尾，杜绝把标签外的 URL / 说明性文字误当 JSON。
_AI_RESULT_TAG_RE: re.Pattern = re.compile(
    r"\[ai_result\]\s*(?P<payload>\{.+?\})\s*\[ai_result\]",
    re.DOTALL,
)


class PortraitResponseParser:
    """集群画像 AI 返回文本 -> 结构化字段的解析器。

    职责：
        - 三级降级解析 AI 原始文本，产出稳定的 :class:`ParsedPortraitResult`
        - 兼容 AI 输出偶尔"包了自然语言外壳"或"JSON 字段缺失/越界"的情况，
          避免脏数据入 :class:`ClusterPortraitReport`
        - 采纳 AI 侧自报的 ``ai_status``，把 "AI 语义成败" 传递给基类 run() 做二次分支

    使用方式::

        parser = PortraitResponseParser()
        result: ParsedPortraitResult = parser.parse(raw_text)
        if result.parsed_ok and result.ai_ok:
            # 走 SUCCESS 路径（AI 报成功 + 结构合法）
            ...
        elif result.parsed_ok and not result.ai_ok:
            # 走 AI_ERROR 路径（AI 自报失败，summary 是失败原因）
            ...
        else:
            # 走 parse_error 路径（结构不合法，summary=截断原始文本）
            ...

    线程安全：是（无实例状态）
    边界：
        - summary 超出 :attr:`MAX_SUMMARY_CHARS` -> 截断（不抛异常）
        - score 非 int 或不在 ``[SCORE_MIN, SCORE_MAX]`` -> 归一化为 ``-1`` + warning 日志
        - 输入为空串 / None -> ``parsed_ok=False, ai_ok=False``；summary=""
    """

    #: summary 字段最大长度（软限制）；超过则截断；单位：字符（非字节）
    #  与 :class:`PortraitIngestSDK.MAX_SUMMARY_CHARS` 保持一致，避免两套上限漂移
    MAX_SUMMARY_CHARS: int = 4000

    #: score 合法下界；低于此值统一归一化为 ``-1``（不含 -1 本身，-1 表示"未上报"是合法特殊值）
    SCORE_MIN: int = 0

    #: score 合法上界；越界统一归一化为 ``-1``
    SCORE_MAX: int = 100

    #: 成功路径 summary 的**固定话术**：``ai_status=true`` 时不再采纳标签外自然语言 / JSON message，
    #  统一写入本常量。理由：成功路径的过程性中文综述属于噪音，前端只需 share_url 跳转详情页即可；
    #  同时避免 summary 字段承载数千字文本导致列表页渲染变慢。
    #  使用 ``gettext_lazy`` 支持 i18n；实际赋值到 :class:`ParsedPortraitResult.summary` 时会 ``str()`` 强转，
    #  以通过下游 SDK 的 ``isinstance(summary, str)`` 校验并按当前语言渲染。
    SUCCESS_SUMMARY_TEXT = _("生成报告成功")

    def parse(self, raw_text: str) -> ParsedPortraitResult:
        """按三级降级策略把 AI 原始文本转换为结构化字段。

        执行流程：
            1) 空/None 快速失败：返回全空占位 + ``parsed_ok=False, ai_ok=False``
            2) 第 1 级 ``_try_json``：``[ai_result]`` 标签抽取 + JSON + schema 校验；命中即返回，
               ``ai_ok`` 采纳 AI 侧 ``ai_status``（可能 True/False）
            3) 第 2 级 ``_try_share_url_fallback``：正则提取 report_url + 剩余文本作 summary；
               命中固定 ``parsed_ok=True, ai_ok=True``（视为"业务上可展示"）
            4) 第 3 级：兜底截断，``parsed_ok=False, ai_ok=False``

        :param raw_text: AgentHandler 返回的原始文本；期望包含 ``[ai_result]{...}[ai_result]`` 标签块，
                         也兼容纯 JSON / JSON 外裹自然语言 / 纯自然语言等异常形态
        :return: :class:`ParsedPortraitResult`；五字段均已归一化，可直接落库

        边界 / 异常：
            - 本方法不抛异常；所有失败分支通过 ``parsed_ok`` / ``ai_ok`` 表达
            - 解析降级 / 彻底失败时打 warning 日志，记录原始文本前 200 字符便于回溯
        """
        # 空输入：视为彻底失败；不做任何日志（属常见分支）
        if not raw_text:
            return ParsedPortraitResult(summary="", share_url="", score=-1, parsed_ok=False, ai_ok=False)

        # 第 1 级：[ai_result] 标签抽取 + JSON schema 校验
        json_result: Optional[ParsedPortraitResult] = self._try_json(raw_text)
        if json_result is not None:
            return json_result

        # 第 2 级：report_url 正则兜底
        url_result: Optional[ParsedPortraitResult] = self._try_share_url_fallback(raw_text)
        if url_result is not None:
            logger.warning(
                "[portrait_parser] [ai_result] tag extraction failed, report_url fallback matched: raw_head=%s",
                raw_text[:200],
            )
            return url_result

        # 第 3 级：彻底失败；把原始文本截断作 summary，方便事后 debug prompt 质量
        logger.warning(
            "[portrait_parser] parse totally failed, use raw text as summary: raw_head=%s",
            raw_text[:200],
        )
        return ParsedPortraitResult(
            summary=self._truncate_summary(raw_text),
            share_url="",
            score=-1,
            parsed_ok=False,
            ai_ok=False,
        )

    # ------------------------------------------------------------------
    # 私有实现
    # ------------------------------------------------------------------

    def _try_json(self, raw_text: str) -> Optional[ParsedPortraitResult]:
        """第 1 级：``[ai_result]`` 标签抽取 + ``json.loads`` + JSON Schema 校验。

        功能说明 / 怎么做：
            - 先用模块级 :data:`_AI_RESULT_TAG_RE` 从 ``raw_text`` 中抽取被
              ``[ai_result]{...}[ai_result]`` 标签围住的核心 JSON 片段（对 LLM 冗余输出免疫）；
            - 抽取到的 payload 再走 ``json.loads`` + :data:`_PORTRAIT_JSON_SCHEMA` 校验；
            - 校验通过后按字段名映射生成 :class:`ParsedPortraitResult`。

        字段名映射（AI 侧 → 内部）：
            - ``ai_status`` -> ``ai_ok``
            - ``report_url`` -> ``share_url``
            - ``report_score`` -> ``score``
            - ``message`` -> ``summary``（仅 ``ai_status=false`` 时；``ai_status=true`` 时走固定话术）

        ``summary`` 语义分道规则：
            - ``ai_status=true``（成功路径）：固定写入 :attr:`SUCCESS_SUMMARY_TEXT`；
              标签外自然语言 / JSON ``message`` 均**不采纳**（成功场景细节由 share_url 承载，无需入库）；
            - ``ai_status=false``（失败路径）：取 JSON ``message`` 作为失败原因，走 :meth:`_truncate_summary` 截断。

        :param raw_text: AI 原始返回文本；期望内含一对 ``[ai_result]{...}[ai_result]`` 标签块
        :return: 命中返回 :class:`ParsedPortraitResult`（parsed_ok=True）；未命中返回 ``None``

        边界：
            - ``[ai_result]`` 标签未命中（``re.search`` 未匹配） -> 返回 ``None``，交由上层降级
            - 标签命中但 payload ``json.loads`` / schema 校验失败 -> 打 warning 日志后返回 ``None``
            - AI 自报失败（``ai_status=false``） -> parsed_ok=True + ai_ok=False；
              summary 采纳 AI 侧 message；score/share_url 强制归零；由基类 run() 判定为 STATUS_AI_ERROR
            - score 非法通过 :meth:`_normalize_score` 归一化，不影响 parsed_ok 语义
            - 多标签块场景仅采纳**第一个**匹配（``re.search`` 语义），避免二义
        """
        # Step 1：抽取 [ai_result] 标签块；未命中直接返回 None 让上层走 URL 兜底
        match: Optional[re.Match] = _AI_RESULT_TAG_RE.search(raw_text)
        if match is None:
            return None

        payload_text: str = match.group("payload")

        # Step 2：对标签内 payload 走 json.loads + schema 校验
        try:
            payload: Any = json.loads(payload_text)
            validate(instance=payload, schema=_PORTRAIT_JSON_SCHEMA)
        except (json.JSONDecodeError, ValidationError, TypeError) as exc:
            logger.warning(
                "[portrait_parser] [ai_result] tag matched but payload invalid: err=%s payload_head=%s",
                exc,
                payload_text[:200],
            )
            return None

        # Step 3：按字段名映射装配基础字段
        ai_ok: bool = bool(payload.get("ai_status", False))
        share_url: str = str(payload.get("report_url", ""))
        score: int = self._normalize_score(payload.get("report_score"))
        message_text: str = str(payload.get("message", ""))

        # Step 4：summary 语义分道
        #   - ai_ok=True（成功路径）：固定话术 SUCCESS_SUMMARY_TEXT；
        #     成功场景的过程细节由 share_url 承载，DB 里保留一大段中文综述属于噪音、还拖慢列表页渲染
        #   - ai_ok=False（失败路径）：采纳 JSON message 作为失败原因；
        #     标签外文本此时通常是模型思考过程，不入库
        if ai_ok:
            # str() 强转：SUCCESS_SUMMARY_TEXT 是 gettext_lazy 惰性对象，落库前按当前语言实体化，
            # 同时满足下游 SDK 对 summary 的 isinstance(str) 校验
            summary: str = str(self.SUCCESS_SUMMARY_TEXT)
        else:
            summary = self._truncate_summary(message_text)

        # Step 5：语义一致性防御：ai_status=false 时 score/share_url 强制归零，避免 AI 侧字段冲突时脏数据入库
        if not ai_ok:
            score = -1
            share_url = ""

        return ParsedPortraitResult(
            summary=summary,
            share_url=share_url,
            score=score,
            parsed_ok=True,
            ai_ok=ai_ok,
        )

    def _try_share_url_fallback(self, raw_text: str) -> Optional[ParsedPortraitResult]:
        """第 2 级：正则提取 report_url，剩余文本作 summary。

        设计要点：
            - 正则模式与 ``mysql_cluster_skew`` 一致：``<BK_SAAS_HOST>/ai-chat/share/<uuid>[/]``
            - 提取到 URL 视为"业务上成功"：拿到分享链接就能兜底展示，无需强制要求 JSON 完整；
              固定标 ``ai_ok=True``，让 run() 按 SUCCESS 落库（前端至少可跳详情页）
            - score 无法从 URL 中提取，固定为 -1（"未上报"）

        :param raw_text: AI 原始返回文本
        :return: 命中返回 :class:`ParsedPortraitResult`（parsed_ok=True, ai_ok=True）；未命中返回 ``None``

        边界：
            - 未匹配到 URL -> 返回 ``None``，交由上层进入第 3 级兜底
        """
        match: Optional[re.Match] = _SHARE_URL_RE.search(raw_text)
        if not match:
            return None

        # 组装标准化 share_url（去掉末尾可能的 /）；剩余文本清洗后作 summary
        share_url: str = f"{env.BK_SAAS_HOST.rstrip('/')}/ai-chat/share/{match.group(1)}/"
        summary_raw: str = (raw_text[: match.start()] + raw_text[match.end() :]).strip()
        summary: str = self._truncate_summary(summary_raw)
        return ParsedPortraitResult(
            summary=summary,
            share_url=share_url,
            score=-1,
            parsed_ok=True,
            ai_ok=True,
        )

    def _normalize_score(self, value: Any) -> int:
        """把任意输入归一化为合法 score int。

        归一化规则：
            - 数字（int / float / 数字字符串，含 "88" / "88.0" / "88.7"） -> 转 int；
              在 ``[SCORE_MIN, SCORE_MAX]`` 区间原样返回
            - 越界 / 非数字 / None / inf / nan -> 返回 ``-1``（语义：未上报）
            - 每次归一化到 -1 都打 warning 日志（-1 直传 -1 不告警，属常见入参）

        :param value: 待归一化值；期望 int，但兼容 float / 数字字符串（含小数形式）
        :return: 合法 score int；范围 ``-1 | [SCORE_MIN, SCORE_MAX]``

        边界：
            - 采用 ``int(float(value))`` 先转 float 再转 int：
                * 支持 "88.0" / "88.7" 这类带小数点的数字字符串（若直接 int() 会 ValueError）；
                * 对正数等价于向下取整（trunc），保持"分数只跌不涨"的保守策略；
            - True/False 会被 int() 视作 1/0，属兼容分支，此处显式拦截避免误判为合法分数；
            - inf / -inf 会在 int(float(inf)) 时抛 OverflowError；nan 会抛 ValueError；
              二者均归一化为 -1；
        """
        try:
            # bool 是 int 的子类，先拦一下避免 True -> 1 误判为合法分数
            if isinstance(value, bool):
                raise TypeError("bool is not accepted as score")
            # 先 float 再 int：兼容 "88.0" / "88.7" 等带小数点数字字符串；
            # 对 float 等价于向下取整（trunc），与"分数只跌不涨"语义一致
            score_int: int = int(float(value))  # type: ignore[arg-type]
        except (TypeError, ValueError, OverflowError):
            # OverflowError 兜底 int(float("inf")) 场景，避免异常冒泡到 run()
            logger.warning(_("[portrait_parser] score normalize failed, value=%s"), value)
            return -1

        if score_int == -1:
            # 显式 -1：调用方主动声明"未上报"，直接透传
            return -1
        if not (self.SCORE_MIN <= score_int <= self.SCORE_MAX):
            logger.warning(
                _("[portrait_parser] score out of range, value=%s range=[%s,%s] -> -1"),
                score_int,
                self.SCORE_MIN,
                self.SCORE_MAX,
            )
            return -1
        return score_int

    def _truncate_summary(self, text: str) -> str:
        """截断 summary 到 :attr:`MAX_SUMMARY_CHARS` 上限；不足则原样返回。

        :param text: 原始 summary 文本
        :return: 长度 <= MAX_SUMMARY_CHARS 的字符串

        边界：
            - text 为 None / 非 str -> 返回空串（防御性）
        """
        if not isinstance(text, str):
            return ""
        if len(text) <= self.MAX_SUMMARY_CHARS:
            return text
        return text[: self.MAX_SUMMARY_CHARS]
