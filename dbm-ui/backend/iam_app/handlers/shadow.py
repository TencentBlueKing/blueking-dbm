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
from typing import Any, Tuple

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
# 类型标签 -> (判定函数, dump, load)
_CODECS = {
    "action": (
        lambda o: isinstance(o, ActionMeta),
        lambda o: {"id": o.id},
        lambda d: ActionEnum.get_action_by_id(d["id"]),
    ),
    "resource": (
        lambda o: isinstance(o, Resource),
        lambda o: o.to_dict(),
        lambda d: Resource(**d),
    ),
}

# 影子后端无状态，复用单例即可；IAMV4Api 内部也是模块级单例
_shadow_backend = None


def get_shadow_backend():
    global _shadow_backend
    if _shadow_backend is None:
        _shadow_backend = IAMV4Backend()
    return _shadow_backend


def _enabled() -> bool:
    # V4 已是真实链路、SKIP 模式下比对都无意义，仅在 V3 真实鉴权下生效
    return env.IAM_V4_SHADOW_ENABLE and not env.ENABLE_IAM_V4 and not env.BK_IAM_SKIP


def _sampled() -> bool:
    ratio = IAM_V4_SHADOW_RATIO
    return ratio >= 1 or random.random() < ratio


def try_shadow(method: str, v3_result: Any, args: Tuple, kwargs: dict):
    """主鉴权返回后调用。命中采样才序列化并返回待投递的负载，否则返回 None。"""
    if method not in SHADOWABLE_METHODS or not _enabled() or not _sampled():
        return None

    # args/kwargs 中含 ActionMeta/Resource 等非 JSON 对象，需先序列化成可入队的纯数据
    return method, v3_result, serialize_args(args), serialize_kwargs(kwargs)


def serialize_args(args: Tuple) -> list:
    return [_serialize(obj) for obj in args]


def serialize_kwargs(kwargs: dict) -> dict:
    return {key: _serialize(value) for key, value in kwargs.items()}


def deserialize_args(args: list) -> list:
    return [_deserialize(obj) for obj in args]


def deserialize_kwargs(kwargs: dict) -> dict:
    return {key: _deserialize(value) for key, value in kwargs.items()}


def _serialize(obj):
    for tag, (match, dump, _load) in _CODECS.items():
        if match(obj):
            return {"__type__": tag, "value": dump(obj)}
    if isinstance(obj, dict):
        return {k: _serialize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_serialize(v) for v in obj]
    return obj


def _deserialize(obj):
    if isinstance(obj, dict):
        tag = obj.get("__type__")
        if tag in _CODECS:
            return _CODECS[tag][2](obj["value"])
        return {k: _deserialize(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_deserialize(v) for v in obj]
    return obj


# def _serialize(obj: Any) -> Any:
#     """把鉴权参数转成可 JSON 序列化的纯数据。ActionMeta 按 id 重建，Resource 用 to_dict 还原。"""
#     if isinstance(obj, ActionMeta):
#         return {"__action__": obj.id}
#     if isinstance(obj, Resource):
#         return {"__resource__": obj.to_dict()}
#     if isinstance(obj, dict):
#         return {key: _serialize(value) for key, value in obj.items()}
#     if isinstance(obj, (list, tuple)):
#         return [_serialize(value) for value in obj]
#     return obj
#
#
# def _deserialize(obj: Any) -> Any:
#     """把 celery 入队后的纯数据还原成鉴权后端所需的 ActionMeta/Resource 对象。"""
#     if isinstance(obj, dict):
#         if "__action__" in obj:
#             return ActionEnum.get_action_by_id(obj["__action__"])
#         if "__resource__" in obj:
#             resource = obj["__resource__"]
#             return Resource(resource["system"], resource["type"], resource["id"], resource["attribute"])
#         return {key: _deserialize(value) for key, value in obj.items()}
#     if isinstance(obj, list):
#         return [_deserialize(value) for value in obj]
#     return obj


def normalize(method: str, result: Any) -> Any:
    """把两版返回归一化成可比较的稳定结构。

    batch 保留资源维度、只把两版 resource/action 的 key 规整成 str 后逐格比对，
    避免按 action 聚合计数丢失"哪个资源判定相反"的差异（如 V3 允许 A 拒绝 B、V4 允许 B 拒绝 A）。
    """
    if method == "is_allowed":
        return bool(result)
    if method == "multi_actions_is_allowed":
        return {str(k): bool(v) for k, v in (result or {}).items()}
    if method == "batch_is_allowed":
        return {
            str(resource_key): {
                str(action_id): bool(allowed)
                for action_id, allowed in sorted((per_resource or {}).items(), key=lambda kv: str(kv[0]))
            }
            for resource_key, per_resource in sorted((result or {}).items(), key=lambda kv: str(kv[0]))
        }
    return result
