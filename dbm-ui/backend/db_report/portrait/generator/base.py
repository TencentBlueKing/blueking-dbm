# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

集群画像报告生成器 - 基类、结果 dataclass 与业务异常。

模块职责：
    - 提供抽象基类 :class:`ClusterPortraitGenerator`：以「模板方法」形式固化画像生成 4 阶段管线
      （入参校验 → init_record → 请求 AI → 解析 → fill_report_result）
    - 定义业务异常家族（继承自 :class:`PortraitSDKBaseException`）
    - 定义结果 / 中间态 dataclass（:class:`PortraitRunResult` / :class:`ParsedPortraitResult`）

设计要点：
    - **两阶段写入 ClusterPortraitReport**：init_record 只落占位，fill_report_result 只在
      最终阶段（成功 / AI 异常 / 解析失败）一次性补齐，避免中途留下"半份记录"
    - **异常语义分层**：
        * 入参校验失败 -> 冒泡 :class:`PortraitInvalidParamException`，**不落记录**
        * AI 调用失败 -> 落 status=ai_error 的完整记录，函数返回不冒泡
        * 解析失败 -> 落 status=parse_error 的完整记录，函数返回不冒泡
    - **子类"薄壳"**：通常只声明 3 个类属性即可（``db_type / agent_code / dimension_enum``）；
      基类提供**默认 prompt 模板** (:attr:`ClusterPortraitGenerator.PROMPT_TEMPLATE`) 与默认
      :meth:`ClusterPortraitGenerator.build_content` 实现，子类可按需通过覆盖类属性 / 覆写
      :meth:`ClusterPortraitGenerator.get_extra_context` / 重写 :meth:`ClusterPortraitGenerator.build_content` 三级递进定制
    - **无反向注册 / 无分发中间层**：不使用 ``__init_subclass__``、不维护 ``db_type -> 子类`` 字典、
      不提供根据 cluster 反查子类的模块级入口；调用方明确知道 db_type 并直接 import 对应子类调用其 ``run()``

边界：
    - 本模块不定义任何 celery 任务；不做鉴权 / 幂等 / 去重
    - 类属性 (:attr:`db_type` / :attr:`agent_code` / :attr:`dimension_enum`) 若未在子类声明，
      **首次实例化**时（``__init__``）快速失败并抛出 :class:`PortraitGenerateException`
"""
import logging
import time
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Type

from django.utils import timezone as django_timezone
from django.utils.translation import gettext_lazy as _

from backend.configuration.constants import DBType
from backend.db_meta.models import Cluster
from backend.db_report.models.cluster_portrait_report import ClusterPortraitReport
from backend.db_report.portrait.exceptions import PortraitSDKBaseException
from backend.dbm_aiagent.agent.constants import DEFAULT_AGENT_CHAT_TIMEOUT, DBMAgentCode
from backend.dbm_aiagent.agent.handlers import AgentHandler
from backend.utils.time import datetime2str
from blue_krill.data_types.enum import StrStructuredEnum

logger = logging.getLogger("root")

# ---------------------------------------------------------------------------
# status 常量（对应 PortraitRunResult.status 字段）
# ---------------------------------------------------------------------------

#: 画像生成完全成功（AI 正常返回 + 解析成功，含正则兜底命中）
STATUS_SUCCESS: str = "success"

#: AI 调用异常（网络 / 超时 / 服务端错误）；已落 ClusterPortraitReport，summary=简要错误信息
STATUS_AI_ERROR: str = "ai_error"

#: AI 返回文本解析失败（三级降级都未命中）；已落 ClusterPortraitReport，summary=截断的原始文本
STATUS_PARSE_ERROR: str = "parse_error"


# ---------------------------------------------------------------------------
# 业务异常家族
# ---------------------------------------------------------------------------


class PortraitGenerateException(PortraitSDKBaseException):
    """集群画像生成器异常基类。

    职责：作为 :mod:`generator` 包内所有业务异常的公共父类，供上层统一捕获。
    与既有 :class:`PortraitSDKBaseException` 的关系：
        - ``PortraitSDKBaseException`` 更大范畴：涵盖 SDK 上报（ingest_summary）+ 生成器 两条路径
        - ``PortraitGenerateException`` 是生成器路径的专属子树；调用方可以细粒度地
          ``except PortraitGenerateException`` 只捕获生成器路径的异常
    边界：本类不直接抛，请使用具体子类。
    """

    ERROR_CODE = "110"
    MESSAGE = _("集群画像生成器异常")
    MESSAGE_TPL = _("{msg}")


class PortraitInvalidParamException(PortraitGenerateException):
    """入参非法异常。

    触发条件：
        - cluster 不是 :class:`Cluster` 实例 / report_from >= report_to /
          report_to > 当前时间 / dimensions 内出现非本 db_type 的枚举成员
        - 子类未声明必需类属性（db_type / agent_code / dimension_enum），首次实例化时抛出
    修复建议：
        - 校验调用点参数；参考 :meth:`ClusterPortraitGenerator._validate_inputs`
        - 子类需按需求 2.1 声明三个必需类属性
    """

    ERROR_CODE = "111"
    MESSAGE = _("集群画像生成入参非法")
    MESSAGE_TPL = _("{msg}")


# ---------------------------------------------------------------------------
# 结果 / 中间态 dataclass
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ParsedPortraitResult:
    """解析器输出的中间态结构。

    字段语义：
        - summary: 报告级摘要文本；已按 :attr:`PortraitResponseParser.MAX_SUMMARY_CHARS` 截断；
                   AI 侧对应 ``message`` 字段（成功=报告摘要 / 失败=失败原因，一字段两义）
        - share_url: 分享链接；AI 侧对应 ``report_url`` 字段；解析失败或 URL 未匹配时为空串
        - score: 报告健康分；AI 侧对应 ``report_score`` 字段；``-1`` 表示未上报 / 归一化失败 / 越界；正常范围 ``[0, 100]``
        - parsed_ok: **JSON 结构层面**是否成功抽取；只关心"响应文本是否可被结构化"，与 AI 语义无关
                    JSON 完整解析 或 share_url 正则命中 -> True；彻底失败（第 3 级兜底） -> False
        - ai_ok: **AI 语义层面**是否成功生成画像；AI 侧对应 ``ai_status`` 字段
                 ``True``  -> AI 报告 ai_status=true，画像生成成功
                 ``False`` -> AI 报告 ai_status=false（数据不足 / 内部处理失败 / 拒答等）
                 默认 ``True``；兜底路径（share_url 正则命中）也标 True，视为"业务上可展示"

    双字段设计原因（parsed_ok vs ai_ok）：
        - 解析器只判"结构是否合法"（parsed_ok），不做"AI 语义成败"判断
        - AI 语义成败由 :meth:`ClusterPortraitGenerator.run` 阶段 4 依据 ``ai_ok`` 二次分支
        - 只有 ``parsed_ok=True and ai_ok=True`` 才会落 ``STATUS_SUCCESS``

    边界：
        - 冻结不可变；跨阶段传递结果对象天然线程安全
    """

    summary: str
    share_url: str
    score: int
    parsed_ok: bool
    ai_ok: bool = True


@dataclass(frozen=True)
class PortraitRunResult:
    """:meth:`ClusterPortraitGenerator.run` 的最终返回结构。

    字段语义：
        - record_id: :class:`ClusterPortraitReport` 主键；入参校验失败时可能为 ``None``
        - status: 枚举字符串；取值见 ``STATUS_*`` 常量
        - summary / share_url / score: 与落库字段一致（成功路径 = 解析结果；失败路径 = 错误摘要 / 截断原文）
        - raw_response: AI 原始返回文本；便于调用方回溯 prompt 质量；AI 调用未成功时为空串
        - error: 失败原因简要文本；成功路径为 ``None``；失败路径为异常类名或解析降级描述
    边界：
        - 冻结不可变；调用方按 ``status`` 分支决策，不应修改字段
    """

    record_id: Optional[int]
    status: str
    summary: str
    share_url: str
    score: int
    raw_response: str = ""
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# 抽象基类（无注册表 / 无分发入口）
# ---------------------------------------------------------------------------


class ClusterPortraitGenerator:
    """集群画像报告生成器基类（纯模板方法，不做子类自动注册）。

    职责：
        - 以 :meth:`run` 为唯一主入口，串起 4 阶段管线：
            1) 校验入参（不落记录）
            2) init_record 落占位
            3) build_content -> ask_agent -> raw_text
            4) parse_response -> fill_report_result

    子类接入方式（"薄壳"，通常只需声明 3 个类属性）::

        class MysqlClusterPortraitGenerator(ClusterPortraitGenerator):
            db_type = DBType.MySQL
            agent_code = DBMAgentCode.MYSQL_PORTRAIT_CLUSTER
            dimension_enum = MysqlPortraitDimensionCode

        # 需要向 prompt 注入额外占位时（不需要就不重写）：
        class RedisClusterPortraitGenerator(ClusterPortraitGenerator):
            db_type = DBType.Redis
            agent_code = DBMAgentCode.REDIS_PORTRAIT_CLUSTER
            dimension_enum = RedisPortraitDimensionCode

            # 在默认模板末尾追加一段自定义描述（含 {shard_num} 占位）
            PROMPT_TEMPLATE = (
                ClusterPortraitGenerator.PROMPT_TEMPLATE
                + "\\n## Redis 额外信息\\n- 分片数: {shard_num}\\n"
            )

            def get_extra_context(self, cluster, dimensions):
                return {"shard_num": cluster.storageinstance_set.count()}

    调用方式（调用方明确知道 db_type，直接 import 对应子类）::

        from backend.db_report.portrait.generator import MysqlClusterPortraitGenerator
        result = MysqlClusterPortraitGenerator().run(cluster=..., report_from=..., report_to=...)

    线程安全：是（无实例状态；每次 :meth:`run` 都是独立调用）
    边界：
        - 子类未声明必需类属性 -> 首次实例化时（``__init__``）抛 :class:`PortraitGenerateException`（fail-fast）
        - 不做子类自动注册；不同 db_type 子类彼此独立，互不感知
    """

    # ---- 子类必须声明的类属性（基类默认 None，__init__ 会校验非空） ----

    #: 本子类所属 DB 类型；子类 SHALL 声明为 :class:`DBType` 枚举成员
    db_type: Optional[DBType] = None

    #: 本 db_type 使用的画像智能体 code；子类 SHALL 声明为 :class:`DBMAgentCode` 枚举成员
    agent_code: Optional[DBMAgentCode] = None

    #: 本 db_type 允许的画像维度枚举**类型**（非成员）；
    #  基类用它做 dimensions 参数的 isinstance 校验，防止串号
    dimension_enum: Optional[Type[StrStructuredEnum]] = None

    # ---- 可选覆盖 ----

    #: 自定义解析器类；``None`` 表示使用默认 :class:`PortraitResponseParser`（懒 import 避免循环依赖）
    parser_cls: Optional[Type] = None

    #: AI 调用超时时间（秒）；默认沿用 AgentHandler 的常量
    ai_timeout: int = DEFAULT_AGENT_CHAT_TIMEOUT

    #: 默认集群画像 prompt 模板（多次调试后的稳定形态，各 db_type 子类默认共享）。
    #  可用占位（均由 :meth:`build_content` 注入）：
    #    - ``{bk_biz_id}`` / ``{cluster_domain}``：集群坐标
    #    - ``{report_from}`` / ``{report_to}``：已本地时区格式化的时间窗
    #    - ``{dimensions_section}``：维度清单段落（空列表时为"全维度"描述）
    #  子类若需完全替换文案可直接在类体中覆写本类属性；
    #  若只需新增占位，请覆写 :meth:`get_extra_context` 注入额外字段。
    #
    #  输出契约采用 **few-shot 示例**表达（比自然语言"要求 JSON 为..."更稳定），
    #  完整字段语义与拒答规则由 agent 侧 system prompt 承载（见 system_prompt.md）；
    #  本任务 prompt 只保留 3 个示例作为格式 anchor：
    #    - 示例 1 ai_status=true：完整生成成功
    #    - 示例 2 ai_status=false：数据源不足以生成
    #    - 示例 3 ai_status=false：AI 内部处理异常
    #
    #  ⚠️ 双花括号 ``{{ }}`` 是 :meth:`str.format` 的转义写法，
    #  用于让 JSON 示例中的 ``{`` / ``}`` 不被误当作 format 占位。
    PROMPT_TEMPLATE: str = _(
        "生成集群画像报告。\n"
        "\n"
        "## 集群坐标\n"
        "- bk_biz_id: {bk_biz_id}\n"
        "- cluster_domain: {cluster_domain}\n"
        "\n"
        "## 画像时间窗\n"
        "- report_from: {report_from}\n"
        "- report_to: {report_to}\n"
        "\n"
        "## 指定分析维度\n"
        "{dimensions_section}\n"
        "\n"
        "## 输出要求\n"
        "在你的响应中，**必须**包含且仅包含一对 `[ai_result]` 标签，把核心 4 字段 JSON 完整地包在其中，"
        "形如：`[ai_result]{{...}}[ai_result]`（**开始标签与结束标签文本完全相同**）。\n"
        "标签**之外**的文本可以是你的报告综述 / 分析过程 / 结论说明（自然语言即可，不必是 JSON），"
        "但标签**之内**必须是且仅是一个合法的 JSON 对象，不允许包含 Markdown 代码块围栏（```json / ```）"
        "或任何注释、trailing comma 等非标准 JSON 语法。\n"
        "\n"
        "### 字段来源与约束（严格遵守，不得违反）\n"
        "- `report_score`：**必须**取自本次画像结果对象中的 `health_score` 字段的原值（0~100 的整数）；\n"
        "  **严禁**由 AI 自行估算 / 猜测 / 伪造。若结果对象未产出 `health_score`，`report_score` 一律填 `-1`。\n"
        "- `message`：仅在 `ai_status=false` 时使用，用于说明失败 / 拒答原因；\n"
        '  当 `ai_status=true` 时，`message` **必须**为空字符串 `""`，不要在其中重复报告摘要 / 结论。\n'
        '- `report_url`：仅在 `ai_status=true` 时给出完整分享链接；`ai_status=false` 时填空字符串 `""`。\n'
        "\n"
        "### 示例 1：正常生成（ai_status=true，message 留空，report_score 取自 health_score）\n"
        "> 标签外可自由输出报告综述文本（示例略）；标签内固定放 4 字段 JSON：\n"
        '[ai_result]{{"ai_status": true, "report_url": "https://bk-dbm.example.com/ai-chat/share/'
        '2c1f0e88-33b0-4a2f-9a2b-1a2b3c4d5e6f/", "report_score": 88,'
        ' "message": ""}}[ai_result]\n'
        "\n"
        "### 示例 2：数据不足以生成（ai_status=false，report_score=-1）\n"
        '[ai_result]{{"ai_status": false, "report_url": "", "report_score": -1,'
        ' "message": "所选时间窗内该集群无监控埋点，无法生成画像。"}}[ai_result]\n'
        "\n"
        "### 示例 3：AI 内部处理失败（ai_status=false，report_score=-1）\n"
        '[ai_result]{{"ai_status": false, "report_url": "", "report_score": -1,'
        ' "message": "MCP 工具 query_slow_log 调用超时"}}[ai_result]\n'
    )

    # ------------------------------------------------------------------
    # 构造：类属性契约自检（首次实例化 fail-fast）
    # ------------------------------------------------------------------

    def __init__(self) -> None:
        """构造时对必需类属性做一次运行时自检，缺失 / 类型错立即抛出。

        设计要点 / 怎么做：
            - 采取"首次实例化时校验"策略而非"子类定义时校验"，是为了严格避开
              ``__init_subclass__`` / 元类等隐式机制，让代码流向对开发者可读、可控
            - 校验通过的实例状态无副作用；每次实例化都会重复自检，成本可忽略

        :raises PortraitGenerateException: 三个必需类属性任一缺失 / 类型不符

        边界：
            - 抽象基类自身不应被实例化（无 build_content 实现）；若被直接实例化，
              类属性均为 None，本自检会立即拒绝
            - 子类的子类（若有）同样走本自检
        """
        cls_name: str = type(self).__name__

        # 三个必需类属性缺失 -> fail-fast
        if self.db_type is None:
            raise PortraitGenerateException(context={"msg": _("子类 {name} 未声明必需类属性 db_type").format(name=cls_name)})
        if self.agent_code is None:
            raise PortraitGenerateException(context={"msg": _("子类 {name} 未声明必需类属性 agent_code").format(name=cls_name)})
        if self.dimension_enum is None:
            raise PortraitGenerateException(
                context={"msg": _("子类 {name} 未声明必需类属性 dimension_enum").format(name=cls_name)}
            )

        # 类型校验
        if not isinstance(self.db_type, DBType):
            raise PortraitGenerateException(
                context={"msg": _("子类 {name}.db_type 必须是 DBType 枚举成员").format(name=cls_name)}
            )
        if not isinstance(self.agent_code, DBMAgentCode):
            raise PortraitGenerateException(
                context={"msg": _("子类 {name}.agent_code 必须是 DBMAgentCode 枚举成员").format(name=cls_name)}
            )
        if not (isinstance(self.dimension_enum, type) and issubclass(self.dimension_enum, StrStructuredEnum)):
            raise PortraitGenerateException(
                context={"msg": _("子类 {name}.dimension_enum 必须是 StrStructuredEnum 的子类").format(name=cls_name)}
            )

    # ------------------------------------------------------------------
    # 主入口：模板方法
    # ------------------------------------------------------------------

    def run(
        self,
        cluster: Cluster,
        report_from: datetime,
        report_to: datetime,
        dimensions: Optional[List[StrStructuredEnum]] = None,
        operator: str = "system",
    ) -> PortraitRunResult:
        """执行一次完整的画像生成管线。

        执行流程：
            阶段1  :meth:`_validate_inputs` 校验入参；不合法直接抛异常（不落记录）
            阶段2  :meth:`ClusterPortraitReport.init_record` 落占位记录，拿到 ``record_id``
            阶段3  :meth:`build_content` 构造 prompt -> :meth:`_call_agent` 请求 AI；
                   AI 调用异常 -> 走 :meth:`_persist_failure`(AI_ERROR) 直接返回
            阶段4  :meth:`parse_response` 解析原始文本；三态分支：
                   * parsed_ok=True + ai_ok=True  -> :meth:`_persist_success` + STATUS_SUCCESS
                   * parsed_ok=True + ai_ok=False -> :meth:`_persist_failure`(AI_ERROR)；
                     AI 自报画像未生成成功（数据不足 / 内部错 / 拒答等），summary 采纳 AI 侧 ``message``
                   * parsed_ok=False              -> :meth:`_persist_failure`(PARSE_ERROR)；
                     JSON 结构解析失败，summary 采纳截断的原始 AI 文本

        :param cluster: 目标 :class:`Cluster` ORM 实例，必填；基类从中读取 bk_biz_id / immute_domain
        :param report_from: 画像时间窗起点（业务时间）；必须 < report_to
        :param report_to: 画像时间窗终点（业务时间）；必须 <= 当前时间
        :param dimensions: 指定维度枚举成员列表；``None`` / 空列表 = 全维度画像；
                           非空时每个成员必须是本子类 :attr:`dimension_enum` 的成员
        :param operator: 创建 / 更新人 username，用于 :class:`AuditedModel` 审计字段；默认 ``"system"``
        :return: :class:`PortraitRunResult`；调用方按 ``status`` 分支决策

        边界 / 异常：
            - 入参非法 -> :class:`PortraitInvalidParamException`（不落记录）
            - AI / 解析失败 -> 不冒泡异常，通过 ``status`` 返回；已完整落记录
            - 落库失败（ORM 原生异常） -> 原样冒泡；由框架 500 兜底
        """
        # 阶段 1：入参校验（不落记录）
        # 允许 dimensions=None，规范化为空列表，简化后续处理
        normalized_dimensions: List[StrStructuredEnum] = list(dimensions) if dimensions else []
        self._validate_inputs(
            cluster=cluster,
            report_from=report_from,
            report_to=report_to,
            dimensions=normalized_dimensions,
        )

        cluster_domain: str = cluster.immute_domain
        db_type_value: str = str(self.db_type.value)  # type: ignore[union-attr]
        logger.info(
            "[portrait_generator] run start: db_type=%s cluster=%s report_from=%s report_to=%s dims=%d",
            db_type_value,
            cluster_domain,
            report_from,
            report_to,
            len(normalized_dimensions),
        )
        t_start: float = time.monotonic()

        # 阶段 2：init_record 占位
        record_id: int = ClusterPortraitReport.init_record(
            bk_biz_id=cluster.bk_biz_id,
            cluster_domain=cluster_domain,
            db_type=db_type_value,
            creator=operator,
        )
        logger.info(
            "[portrait_generator] placeholder created: db_type=%s cluster=%s record_id=%s",
            db_type_value,
            cluster_domain,
            record_id,
        )

        # 阶段 3：build_content + call agent
        try:
            content: str = self.build_content(
                cluster=cluster,
                report_from=report_from,
                report_to=report_to,
                dimensions=normalized_dimensions,
            )
            raw_response: str = self._call_agent(content)
        except Exception as exc:  # 覆盖 AI 调用 / prompt 构造的所有异常
            logger.exception(
                "[portrait_generator] agent call failed: db_type=%s cluster=%s record_id=%s",
                db_type_value,
                cluster_domain,
                record_id,
            )
            error_msg: str = _("AI 调用异常：{cls}").format(cls=type(exc).__name__)
            self._persist_failure(
                record_id=record_id,
                status=STATUS_AI_ERROR,
                error_summary=str(error_msg),
                raw_response="",
                operator=operator,
            )
            return PortraitRunResult(
                record_id=record_id,
                status=STATUS_AI_ERROR,
                summary=str(error_msg),
                share_url="",
                score=-1,
                raw_response="",
                error=f"{type(exc).__name__}: {exc}",
            )

        # 阶段 4：解析 + 补齐记录（三态分支：SUCCESS / AI_ERROR / PARSE_ERROR）
        parsed: ParsedPortraitResult = self.parse_response(raw_response)
        used_time: float = time.monotonic() - t_start

        # 分支 A：JSON 解析成功 + AI 自报成功 -> 落 SUCCESS
        if parsed.parsed_ok and parsed.ai_ok:
            self._persist_success(record_id=record_id, parsed=parsed, operator=operator)
            logger.info(
                "[portrait_generator] run done: db_type=%s cluster=%s record_id=%s used_time=%.2fs status=%s",
                db_type_value,
                cluster_domain,
                record_id,
                used_time,
                STATUS_SUCCESS,
            )
            return PortraitRunResult(
                record_id=record_id,
                status=STATUS_SUCCESS,
                summary=parsed.summary,
                share_url=parsed.share_url,
                score=parsed.score,
                raw_response=raw_response,
                error=None,
            )

        # 分支 B：JSON 解析成功 + AI 自报失败 -> 落 AI_ERROR（AI 语义层面失败）
        #  summary 采纳 AI 侧 ``message``（已由解析器映射到 parsed.summary）；
        #  加 [ai_rejected] 前缀便于运维一眼区分"AI 语义拒绝"与"网络/超时异常"
        if parsed.parsed_ok and not parsed.ai_ok:
            ai_reject_summary: str = f"[ai_rejected] {parsed.summary}" if parsed.summary else "[ai_rejected]"
            self._persist_failure(
                record_id=record_id,
                status=STATUS_AI_ERROR,
                error_summary=ai_reject_summary,
                raw_response=raw_response,
                operator=operator,
            )
            logger.warning(
                "[portrait_generator] run ai_rejected: db_type=%s cluster=%s record_id=%s "
                "used_time=%.2fs message=%s",
                db_type_value,
                cluster_domain,
                record_id,
                used_time,
                parsed.summary[:200],
            )
            return PortraitRunResult(
                record_id=record_id,
                status=STATUS_AI_ERROR,
                summary=ai_reject_summary,
                share_url="",
                score=-1,
                raw_response=raw_response,
                error="ai_rejected",
            )

        # 分支 C：JSON 解析彻底失败 -> 落 PARSE_ERROR；summary=已截断的原始文本（parser 已处理）
        self._persist_failure(
            record_id=record_id,
            status=STATUS_PARSE_ERROR,
            error_summary=parsed.summary,
            raw_response=raw_response,
            operator=operator,
        )
        logger.warning(
            "[portrait_generator] run parse_error: db_type=%s cluster=%s record_id=%s used_time=%.2fs raw_head=%s",
            db_type_value,
            cluster_domain,
            record_id,
            used_time,
            raw_response[:200],
        )
        return PortraitRunResult(
            record_id=record_id,
            status=STATUS_PARSE_ERROR,
            summary=parsed.summary,
            share_url="",
            score=-1,
            raw_response=raw_response,
            error="parse_failed",
        )

    # ------------------------------------------------------------------
    # 子类扩展点
    # ------------------------------------------------------------------

    def build_content(
        self,
        cluster: Cluster,
        report_from: datetime,
        report_to: datetime,
        dimensions: List[StrStructuredEnum],
    ) -> str:
        """默认实现：基于 :attr:`PROMPT_TEMPLATE` + 预置上下文 + :meth:`get_extra_context` 组装 prompt。

        设计要点 / 怎么做：
            - 把多次调试得到的**稳定 prompt 文案**沉淀在基类 :attr:`PROMPT_TEMPLATE`；
              各 db_type 子类默认复用，改一处全局生效
            - 预置上下文包含：``bk_biz_id / cluster_domain / report_from / report_to /
              dimensions_section``，覆盖共性需求
            - 子类若需向 prompt 注入额外占位（如 Redis 的 shard_num），
              **无需重写本方法**，只需重写 :meth:`get_extra_context` 返回额外 dict 即可
            - 子类若需完全重写 prompt 结构，直接覆盖 :attr:`PROMPT_TEMPLATE` 或本方法

        :param cluster: 目标集群实例（bk_biz_id / immute_domain / cluster_type 均可读取）
        :param report_from: 画像时间窗起点
        :param report_to: 画像时间窗终点
        :param dimensions: 已规范化为 list；空列表 = 全维度画像
        :return: prompt 文本

        边界：
            - :meth:`get_extra_context` 返回的字段若与预置字段同名，以 extra_context 为准（便于子类覆盖）
            - 若子类重写 :attr:`PROMPT_TEMPLATE` 但引入了 extra_context 未提供的占位，
              ``str.format`` 会抛 ``KeyError``；子类需自行保证占位一致性
        """
        base_context: Dict[str, Any] = {
            "bk_biz_id": cluster.bk_biz_id,
            "cluster_domain": cluster.immute_domain,
            "report_from": datetime2str(report_from),
            "report_to": datetime2str(report_to),
            "dimensions_section": self._build_dimensions_section(dimensions),
        }
        # 子类钩子：合并额外上下文；同名字段以子类返回值为准（便于覆盖预置字段）
        extra_context: Dict[str, Any] = self.get_extra_context(cluster, dimensions) or {}
        base_context.update(extra_context)
        return str(self.PROMPT_TEMPLATE).format(**base_context)

    def get_extra_context(
        self,
        cluster: Cluster,
        dimensions: List[StrStructuredEnum],
    ) -> Dict[str, Any]:
        """（钩子）向默认 prompt 模板注入额外占位字段；默认返回空 dict。

        使用场景：
            - 某 db_type 的 prompt 需要额外占位（如 Redis 的 ``shard_num`` / MongoDB 的 ``replica_set``），
              子类覆盖 :attr:`PROMPT_TEMPLATE` 新增占位 + 覆写本方法返回对应值即可，
              **无需重写** :meth:`build_content`

        :param cluster: 目标集群实例
        :param dimensions: 已规范化的维度列表
        :return: 额外上下文 dict；若与预置字段同名会覆盖预置字段（便于子类做局部定制）
        边界：
            - 默认返回空 dict；子类重写时建议保持返回类型为 Dict，不要返回 None
        """
        return {}

    def parse_response(self, raw_text: str) -> ParsedPortraitResult:
        """解析 AI 返回文本；默认使用 :class:`PortraitResponseParser` 三级降级策略。

        子类如需**新增字段**或**替换正则**，可覆盖本方法或自定义 :attr:`parser_cls`。

        :param raw_text: AI 原始返回文本
        :return: :class:`ParsedPortraitResult`；``parsed_ok`` 表达业务成功与否
        边界：
            - 默认解析器不抛异常；覆盖本方法时也应遵循"失败靠 parsed_ok=False 表达"的约定
        """
        parser_cls: Type = self.parser_cls or self._default_parser_cls()
        return parser_cls().parse(raw_text)

    @staticmethod
    def _default_parser_cls() -> Type:
        """惰性 import 默认解析器，避免 base.py 与 parser.py 循环依赖。

        :return: :class:`PortraitResponseParser` 类对象
        """
        # 局部 import：base.py 是 parser.py 的依赖上游，反向 import 需惰性化
        from backend.db_report.portrait.generator.parser import PortraitResponseParser

        return PortraitResponseParser

    # ------------------------------------------------------------------
    # 私有辅助
    # ------------------------------------------------------------------

    def _validate_inputs(
        self,
        cluster: Any,
        report_from: Any,
        report_to: Any,
        dimensions: List[Any],
    ) -> None:
        """入参格式与集群语义校验；不通过直接抛 :class:`PortraitInvalidParamException`。

        校验清单：
            - cluster 必须是 :class:`Cluster` 实例
            - report_from / report_to 必须是 datetime，且**必须是 aware datetime**（携带 tzinfo）
            - report_from < report_to；report_to <= now()
            - dimensions 必须是 list；每个成员必须是本子类 :attr:`dimension_enum` 的成员

        :param cluster: 待校验的集群参数
        :param report_from: 待校验的时间窗起点
        :param report_to: 待校验的时间窗终点
        :param dimensions: 已规范化为 list（可空）
        :raises PortraitInvalidParamException: 任一校验项不通过

        边界 / 设计要点：
            - 单条错误快速失败（不做累积），便于调用方定位
            - **strict-timezone 策略**：naive datetime 视为入参非法，直接抛 :class:`PortraitInvalidParamException`
              而非静默补时区；避免"默默按本地时区解读"造成的 UTC vs 本地时区错位。
              调用方请使用 :func:`django.utils.timezone.now` 或显式 ``tzinfo=ZoneInfo(...)``。
        """
        if not isinstance(cluster, Cluster):
            raise PortraitInvalidParamException(
                context={"msg": _("cluster 必须是 Cluster ORM 实例，实际类型：{t}").format(t=type(cluster).__name__)}
            )

        if not isinstance(report_from, datetime):
            raise PortraitInvalidParamException(context={"msg": _("report_from 必须是 datetime")})
        if not isinstance(report_to, datetime):
            raise PortraitInvalidParamException(context={"msg": _("report_to 必须是 datetime")})

        # aware datetime 强制校验：naive datetime 直接判为入参非法（不做静默时区补齐）
        if not django_timezone.is_aware(report_from):
            raise PortraitInvalidParamException(
                context={
                    "msg": _(
                        "report_from 必须是 aware datetime（携带 tzinfo）；" "请使用 django.utils.timezone.now() 或显式指定 tzinfo"
                    )
                }
            )
        if not django_timezone.is_aware(report_to):
            raise PortraitInvalidParamException(
                context={
                    "msg": _("report_to 必须是 aware datetime（携带 tzinfo）；" "请使用 django.utils.timezone.now() 或显式指定 tzinfo")
                }
            )

        if report_from >= report_to:
            raise PortraitInvalidParamException(
                context={
                    "msg": _("report_from={rf} 必须早于 report_to={rt}").format(
                        rf=report_from.isoformat(), rt=report_to.isoformat()
                    )
                }
            )
        now: datetime = django_timezone.now()
        if report_to > now:
            raise PortraitInvalidParamException(
                context={
                    "msg": _("report_to={rt} 不能晚于当前时间 now={now}").format(rt=report_to.isoformat(), now=now.isoformat())
                }
            )

        if not isinstance(dimensions, list):
            raise PortraitInvalidParamException(context={"msg": _("dimensions 必须是 list 或 None")})

        # dimensions 非空时逐一校验属于本 db_type 的维度枚举
        for idx, dim in enumerate(dimensions):
            if not isinstance(dim, self.dimension_enum):  # type: ignore[arg-type]
                raise PortraitInvalidParamException(
                    context={
                        "msg": _("dimensions[{idx}]={dim} 不属于本 db_type 允许的维度枚举 {enum}").format(
                            idx=idx,
                            dim=dim,
                            enum=self.dimension_enum.__name__ if self.dimension_enum else "None",
                        )
                    }
                )

    def _call_agent(self, content: str) -> str:
        """封装 :meth:`AgentHandler.ask_agent_with_content` 调用；便于测试 mock。

        :param content: 已构造好的 prompt 文本
        :return: AI 返回的原始文本
        边界：
            - 网络 / 超时 / 服务端异常原样抛出；由 :meth:`run` 的 try/except 统一转 STATUS_AI_ERROR
        """
        return AgentHandler.ask_agent_with_content(
            agent_code=self.agent_code,  # type: ignore[arg-type]
            content=content,
            timeout=self.ai_timeout,
        )

    def _persist_success(
        self,
        record_id: int,
        parsed: ParsedPortraitResult,
        operator: str,
    ) -> None:
        """成功路径落库：把解析后的 summary / share_url / score 补齐到占位记录。

        :param record_id: :meth:`init_record` 返回的主键 id
        :param parsed: 解析器输出（``parsed_ok=True``）
        :param operator: 更新人 username
        边界：
            - ``ClusterPortraitReport.fill_report_result`` 返回 0（记录不存在）时不阻塞，仅打 warning 日志
        """
        updated_rows: int = ClusterPortraitReport.fill_report_result(
            record_id=record_id,
            summary=parsed.summary,
            share_url=parsed.share_url,
            score=parsed.score,
            updater=operator,
        )
        if updated_rows == 0:
            logger.warning(
                "[portrait_generator] persist success but record not found: record_id=%s",
                record_id,
            )

    def _persist_failure(
        self,
        record_id: int,
        status: str,
        error_summary: str,
        raw_response: str,
        operator: str,
    ) -> None:
        """失败路径落库：AI 异常 / 解析失败共用；summary 按上限截断，score=-1，share_url=""。

        :param record_id: :meth:`init_record` 返回的主键 id
        :param status: :data:`STATUS_AI_ERROR` 或 :data:`STATUS_PARSE_ERROR`（仅用于日志区分，不落库）
        :param error_summary: 待落库的 summary（AI 异常时 = 错误摘要；解析失败时 = 截断原文）
        :param raw_response: AI 原始返回；当前仅用于日志，不落库；后续如需持久化再扩展 model
        :param operator: 更新人 username
        边界：
            - summary 上限按 :class:`ClusterPortraitReport.summary` (TextField) 语义不硬截；
              防御性截断到 :attr:`ParsedPortraitResult` 相同上限（4000 字符）避免超大 blob
            - fill_report_result 返回 0 -> warning 日志，不抛异常
        """
        # 与 parser MAX_SUMMARY_CHARS 保持一致；这里显式引用防御性截断
        safe_summary: str = (error_summary or "")[:4000]
        updated_rows: int = ClusterPortraitReport.fill_report_result(
            record_id=record_id,
            summary=safe_summary,
            share_url="",
            score=-1,
            updater=operator,
        )
        if updated_rows == 0:
            logger.warning(
                "[portrait_generator] persist failure but record not found: record_id=%s status=%s",
                record_id,
                status,
            )

    # ------------------------------------------------------------------
    # prompt 组装工具（供默认 build_content 使用；子类重写 build_content 时也可复用）
    #
    # 说明 1：时间格式化统一走 :func:`backend.utils.time.datetime2str`（ISO 8601 + 本地时区 offset）；
    #         不再自造 _format_local_time，避免与项目既有时间工具函数重复。
    # 说明 2：入参 datetime 已在 :meth:`_validate_inputs` 中被强制要求为 aware datetime，
    #         因此本文件不再提供 _to_aware "静默补时区"工具；naive datetime 会在校验阶段被直接拒绝。
    # ------------------------------------------------------------------

    @staticmethod
    def _build_dimensions_section(dimensions: List[StrStructuredEnum]) -> str:
        """构造"指定分析维度"段落文本。

        规则：
            - 空列表 -> 明确说明"未指定，请对全部可用维度进行画像"
            - 非空 -> 列出 ``- <code>: <label>`` 的项目符号清单

        :param dimensions: 已规范化的 dimensions 列表
        :return: 段落文本；直接嵌入到 :attr:`PROMPT_TEMPLATE` 的 ``{dimensions_section}`` 占位
        边界：
            - 每个成员通过 ``type(dim).get_choice_label(dim.value)`` 取中文 label；
              若 label 不可获取则退化到 ``dim.name``
        """
        if not dimensions:
            return str(_("- （未指定维度，请对全部可用维度进行综合画像）"))

        lines: List[str] = []
        for dim in dimensions:
            try:
                label: str = str(type(dim).get_choice_label(dim.value))
            except Exception:  # noqa: BLE001 - 兜底：label 取不到不阻塞 prompt 组装
                label = getattr(dim, "name", str(dim))
            lines.append(f"- {dim.value}: {label}")
        return "\n".join(lines)
