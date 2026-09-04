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
from typing import Optional, Tuple, Type

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


def _http_status_code(exc: Exception) -> Optional[int]:
    """Extract an HTTP status from common SDK / HTTP client exception shapes."""
    for attr in ("status_code", "status"):
        value = getattr(exc, attr, None)
        if isinstance(value, int):
            return value
    response = getattr(exc, "response", None)
    if response is not None:
        value = getattr(response, "status_code", None)
        if isinstance(value, int):
            return value
    # ApiResultError / AppBaseException may stash the HTTP status in ``code``.
    code = getattr(exc, "code", None)
    if isinstance(code, int):
        return code
    if isinstance(code, str) and code.isdigit():
        return int(code)
    return None


def _is_rate_limit_error(exc: Exception) -> bool:
    """True only when the exception carries an HTTP 429 status — never free-text."""
    return _http_status_code(exc) == 429


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
            if _is_rate_limit_error(exc):
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
