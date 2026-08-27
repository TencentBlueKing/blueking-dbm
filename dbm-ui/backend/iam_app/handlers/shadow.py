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

import logging
import random
from typing import Any, List, Tuple

from iam import Resource

from backend import env
from backend.iam_app.dataclass.actions import ActionEnum, ActionMeta
from backend.iam_app.handlers.backends.v4 import IAMV4Backend

logger = logging.getLogger("iam_v4_shadow")

# 只对只读鉴权方法做影子比对：
# - grant_creator_actions 是写操作（会改授权数据），绝不能在影子模式里重复执行
# - get_apply_url / get_system_info 无可稳定比对的结果
SHADOWABLE_METHODS = {"is_allowed", "multi_actions_is_allowed", "batch_is_allowed"}
# 采样率 0~1，如 0.5 表示约一半鉴权请求触发一次影子比对
IAM_V4_SHADOW_RATIO = 0.5

# 影子后端无状态，复用单例即可；IAMV4Api 内部也是模块级单例
shadow_backend = IAMV4Backend()


def _enabled() -> bool:
    # V4 已是真实链路、SKIP 模式下比对都无意义，仅在 V3 真实鉴权下生效
    return env.IAM_V4_SHADOW_ENABLE and not env.ENABLE_IAM_V4 and not env.BK_IAM_SKIP


def _sampled() -> bool:
    ratio = IAM_V4_SHADOW_RATIO
    return ratio >= 1 or random.random() < ratio


def try_shadow(method: str, v3_result: Any, args: Tuple, kwargs: dict) -> None:
    """主鉴权返回后调用。命中采样才投递到 celery 异步跑 V4，绝不抛异常、绝不阻塞主链路。"""
    if method not in SHADOWABLE_METHODS or not _enabled() or not _sampled():
        return

    # args/kwargs 中含 ActionMeta/Resource 等非 JSON 对象，需先序列化成可入队的纯数据
    # 延迟导入避免与 tasks -> shadow 的循环依赖
    from backend.iam_app import tasks

    try:
        tasks.try_shadow.delay(method, v3_result, serialize_args(args), serialize_kwargs(kwargs))
    except Exception as e:  # pylint: disable=broad-except
        logger.warning("[iam_v4_shadow] dispatch failed: %s", e)


def serialize_args(args: Tuple) -> list:
    return [_serialize(obj) for obj in args]


def serialize_kwargs(kwargs: dict) -> dict:
    return {key: _serialize(value) for key, value in kwargs.items()}


def deserialize_args(args: list) -> list:
    return [_deserialize(obj) for obj in args]


def deserialize_kwargs(kwargs: dict) -> dict:
    return {key: _deserialize(value) for key, value in kwargs.items()}


def _serialize(obj: Any) -> Any:
    """把鉴权参数转成可 JSON 序列化的纯数据。ActionMeta 按 id 重建，Resource 用 to_dict 还原。"""
    if isinstance(obj, ActionMeta):
        return {"__action__": obj.id}
    if isinstance(obj, Resource):
        return {"__resource__": obj.to_dict()}
    if isinstance(obj, dict):
        return {key: _serialize(value) for key, value in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_serialize(value) for value in obj]
    return obj


def _deserialize(obj: Any) -> Any:
    """把 celery 入队后的纯数据还原成鉴权后端所需的 ActionMeta/Resource 对象。"""
    if isinstance(obj, dict):
        if "__action__" in obj:
            return ActionEnum.get_action_by_id(obj["__action__"])
        if "__resource__" in obj:
            resource = obj["__resource__"]
            return Resource(resource["system"], resource["type"], resource["id"], resource["attribute"])
        return {key: _deserialize(value) for key, value in obj.items()}
    if isinstance(obj, list):
        return [_deserialize(value) for value in obj]
    return obj


def normalize(method: str, result: Any) -> Any:
    """把两版返回归一化成可比较的稳定结构。两版资源维度的 key 约定不同，按动作维度聚合比对。"""
    if method == "is_allowed":
        return bool(result)
    if method == "multi_actions_is_allowed":
        return {str(k): bool(v) for k, v in (result or {}).items()}
    if method == "batch_is_allowed":
        agg = {}
        for per_resource in (result or {}).values():
            for action_id, allowed in (per_resource or {}).items():
                key = str(action_id)
                allow, deny = agg.get(key, (0, 0))
                agg[key] = (allow + 1, deny) if allowed else (allow, deny + 1)
        return dict(sorted(agg.items()))
    return result


def extract_action_ids(method: str, args: list) -> List[str]:
    """从序列化后的 args 里取被鉴权的动作 id，供日志定位是哪批权限的查询。

    args 的第 2 位是动作参数：is_allowed 为单个 ActionMeta，其余为动作列表。
    序列化后 ActionMeta 变成 {"__action__": id}，字符串动作 id 保持原样。
    """
    if not args or len(args) < 2:
        return []
    raw = args[1]
    items = [raw] if method == "is_allowed" else (raw or [])
    ids = []
    for item in items:
        if isinstance(item, dict) and "__action__" in item:
            ids.append(str(item["__action__"]))
        elif isinstance(item, str):
            ids.append(item)
    return ids


def diff_action_ids(v3_norm: Any, v4_norm: Any) -> List[str]:
    """两版归一化结果都是 dict 时，列出取值不一致的动作 id，便于直接看出差异点。"""
    if not isinstance(v3_norm, dict) or not isinstance(v4_norm, dict):
        return []
    keys = set(v3_norm) | set(v4_norm)
    return sorted(k for k in keys if v3_norm.get(k) != v4_norm.get(k))
