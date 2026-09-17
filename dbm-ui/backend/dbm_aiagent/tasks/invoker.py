# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
import json
import logging
import time
from dataclasses import asdict, dataclass
from typing import Iterator, Optional, Tuple, Type

from backend.db_periodic_task.dispatch.config import DEFAULT_REQUEUE_COOLDOWN_SECONDS
from backend.db_periodic_task.dispatch.outcomes import DispatchOutcomeType
from backend.dbm_aiagent.agent.constants import DBMAgentCode
from backend.dbm_aiagent.tasks.config import AGENT_RESPONSE_LOG_MAX_CHARS
from backend.dbm_aiagent.tasks.outcomes import AgentOutcome
from backend.env import DEFAULT_USERNAME

logger = logging.getLogger("root")

# Built-in TimeoutError plus requests timeouts (not subclasses of TimeoutError).
_TIMEOUT_EXC_TYPES: Tuple[Type[BaseException], ...] = (TimeoutError,)
try:
    from requests.exceptions import Timeout as _RequestsTimeout

    _TIMEOUT_EXC_TYPES = (TimeoutError, _RequestsTimeout)
except ImportError:  # pragma: no cover - requests is a hard dependency in practice
    pass


# aidev ``AgentException`` wraps the original SDK error as
# ``Error executing agent: Error code: 429 - {body}`` without ``raise ... from``.
# The HTTP 429 lives on ``__context__`` (OpenAI ``RateLimitError.status_code``).
_HTTP_STATUS_MIN = 100
_HTTP_STATUS_MAX = 599
# BlueKing AI gateway body: ``{'code_name': 'RATE_LIMIT_RESTRICTION', 'code': 1111111}``.
# ``1111111`` is a business code (module + HTTP + seq), not an HTTP status.
_RATE_LIMIT_CODE_NAMES = frozenset({"RATE_LIMIT_RESTRICTION"})


def _as_http_status(value) -> Optional[int]:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        status = value
    elif isinstance(value, str) and value.isdigit():
        status = int(value)
    else:
        return None
    if _HTTP_STATUS_MIN <= status <= _HTTP_STATUS_MAX:
        return status
    return None


def _iter_exception_chain(exc: BaseException) -> Iterator[BaseException]:
    stack = [exc]
    seen: set[int] = set()
    while stack:
        current = stack.pop()
        if current is None or id(current) in seen:
            continue
        seen.add(id(current))
        yield current
        if current.__cause__ is not None:
            stack.append(current.__cause__)
        if current.__context__ is not None:
            stack.append(current.__context__)


def _http_status_from_exc(exc: BaseException) -> Optional[int]:
    """Extract an HTTP status from one exception object (no chain walk)."""
    for attr in ("status_code", "status"):
        status = _as_http_status(getattr(exc, attr, None))
        if status is not None:
            return status
    response = getattr(exc, "response", None)
    if response is not None:
        status = _as_http_status(getattr(response, "status_code", None))
        if status is not None:
            return status
    # ApiResultError / AppBaseException may stash the HTTP status in ``code``.
    # Reject business codes such as 1111111 — they are not HTTP statuses.
    return _as_http_status(getattr(exc, "code", None))


def _has_structured_rate_limit(exc: BaseException) -> bool:
    for source in (exc, getattr(exc, "body", None)):
        if source is None:
            continue
        code_name = source.get("code_name") if isinstance(source, dict) else getattr(source, "code_name", None)
        if code_name in _RATE_LIMIT_CODE_NAMES:
            return True
    return False


def is_http_rate_limit_error(exc: Exception) -> bool:
    """判定异常是否为 HTTP 429 / 网关限频（绝不做 free-text 嗅探）。

    设计要点 / 怎么做：
      - 沿 ``__cause__`` / ``__context__`` 追溯包装链（aidev 会把 OpenAI
        ``RateLimitError`` 包成只有 message 的 ``AgentException``）
      - HTTP 状态取自 ``status_code`` / ``status`` / ``response.status_code`` /
        ``code``（仅接受 100-599；``code=1111111`` 这类业务码不算状态码）
      - 结构化 ``code_name=RATE_LIMIT_RESTRICTION``（异常自身或 ``body`` dict）
        也视为限频
      - 作为项目公开 API 供跨模块复用（例如 :mod:`db_report.portrait.generator.base`
        侧的 :meth:`ClusterPortraitGenerator.run` 需要就地判定 429 后回滚占位记录并
        抛 :class:`PortraitRateLimitException`）

    :param exc: 任意异常实例（通常是 AI 网关 / requests / httpx SDK 抛出的异常）
    :return: True 表示 HTTP 429 / 网关限速；False 表示其他类型异常
    边界：
        - 找不到可识别的状态码或 ``code_name`` -> 返回 False（安全默认）
        - message 里偶然出现 ``429``（端口号等）不触发
    """
    for current in _iter_exception_chain(exc):
        if _http_status_from_exc(current) == 429:
            return True
        if _has_structured_rate_limit(current):
            return True
    return False


def _truncate_agent_response_for_log(response, max_chars: int = AGENT_RESPONSE_LOG_MAX_CHARS) -> str:
    if not isinstance(response, str):
        return repr(response)
    if len(response) <= max_chars:
        return repr(response)
    return f"{response[:max_chars]!r}...[truncated, total_len={len(response)}]"


@dataclass
class AgentRequest:
    """Payload sent to AgentHandler."""

    content: str = ""
    session_code: Optional[str] = None
    username: Optional[str] = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, raw: dict) -> "AgentRequest":
        return cls(
            content=raw.get("content", ""),
            session_code=raw.get("session_code"),
            username=raw.get("username"),
        )


class AgentInvoker:
    """Universal middle layer between AITask workers and AgentHandler."""

    @classmethod
    def invoke(
        cls,
        *,
        task_key: str,
        agent_code: DBMAgentCode,
        request: AgentRequest,
        execution_timeout_seconds: int,
        requeue_cooldown_seconds: int = DEFAULT_REQUEUE_COOLDOWN_SECONDS,
        work_item_ref: str = "",
    ) -> AgentOutcome:
        execution_timeout = max(1, int(execution_timeout_seconds))
        invoke_started_at = time.monotonic()
        try:
            from backend.dbm_aiagent.agent.handlers import AgentHandler

            # Handler defaults to DEFAULT_USERNAME. Passing None/"" overrides that
            # and skips the PaaS sandbox virtual-user rewrite (executor whitelist).
            username = request.username or DEFAULT_USERNAME
            if request.session_code:
                ai_response, _ = AgentHandler.ask_agent_with_content_in_session(
                    agent_code=agent_code,
                    content=request.content,
                    session_code=request.session_code,
                    username=username,
                    timeout=execution_timeout,
                )
            else:
                ai_response = AgentHandler.ask_agent_with_content(
                    agent_code=agent_code,
                    content=request.content,
                    username=username,
                    timeout=execution_timeout,
                )
            elapsed = time.monotonic() - invoke_started_at
            logger.info(
                "%s: work_item=%s outcome=%s elapsed=%.2fs execution_timeout=%ds agent_response=%s",
                task_key,
                work_item_ref,
                DispatchOutcomeType.SUCCESS,
                elapsed,
                execution_timeout,
                _truncate_agent_response_for_log(ai_response),
            )
            return AgentOutcome(outcome=DispatchOutcomeType.SUCCESS, response=ai_response, elapsed_seconds=elapsed)

        except _TIMEOUT_EXC_TYPES as exc:
            elapsed = time.monotonic() - invoke_started_at
            logger.warning(
                "%s: work_item=%s outcome=%s elapsed=%.2fs execution_timeout=%ds: %s",
                task_key,
                work_item_ref,
                DispatchOutcomeType.TIMEOUT,
                elapsed,
                execution_timeout,
                exc,
            )
            return AgentOutcome(outcome=DispatchOutcomeType.TIMEOUT, error=exc, elapsed_seconds=elapsed)

        except Exception as exc:
            elapsed = time.monotonic() - invoke_started_at
            if is_http_rate_limit_error(exc):
                cooldown = max(1, int(requeue_cooldown_seconds))
                logger.warning(
                    "%s: work_item=%s outcome=%s cooldown=%ds: %s",
                    task_key,
                    work_item_ref,
                    DispatchOutcomeType.REQUEUED,
                    cooldown,
                    exc,
                )
                return AgentOutcome(
                    outcome=DispatchOutcomeType.REQUEUED,
                    error=exc,
                    elapsed_seconds=elapsed,
                    should_requeue=True,
                    requeue_cooldown_seconds=cooldown,
                    exhausted_outcome=DispatchOutcomeType.REQUEUE_EXHAUSTED,
                )

            logger.exception(
                "%s: work_item=%s outcome=%s elapsed=%.2fs execution_timeout=%ds: %s",
                task_key,
                work_item_ref,
                DispatchOutcomeType.ERROR,
                elapsed,
                execution_timeout,
                exc,
            )
            return AgentOutcome(outcome=DispatchOutcomeType.ERROR, error=exc, elapsed_seconds=elapsed)

    @staticmethod
    def serialize_request(request: AgentRequest) -> str:
        return json.dumps(request.to_dict(), ensure_ascii=False)

    @staticmethod
    def deserialize_request(payload: str) -> AgentRequest:
        return AgentRequest.from_dict(json.loads(payload))
