# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

当前流程节点日志上下文。本模块不得导入 flow 基类或 DTS 客户端，避免循环导入。
"""
from contextlib import contextmanager
from contextvars import ContextVar, Token
from typing import Any, Iterator

_flow_log_extra: ContextVar[dict[str, Any] | None] = ContextVar("mysqldts_flow_log_extra", default=None)


def get_flow_log_extra() -> dict[str, Any] | None:
    extra = _flow_log_extra.get()
    if not extra:
        return None
    if not extra.get("root_id") and not extra.get("node_id"):
        return None
    return extra


def set_flow_log_extra(extra: dict[str, Any] | None) -> Token:
    return _flow_log_extra.set(extra)


def reset_flow_log_extra(token: Token) -> None:
    _flow_log_extra.reset(token)


@contextmanager
def flow_log_context(extra: dict[str, Any] | None) -> Iterator[None]:
    token = set_flow_log_extra(extra)
    try:
        yield
    finally:
        reset_flow_log_extra(token)
