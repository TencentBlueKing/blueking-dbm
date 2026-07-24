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
from typing import Callable

from django.core.cache import cache

logger = logging.getLogger("root")

# Dispatch configuration changes rarely. Model writes schedule invalidation via
# ``transaction.on_commit`` so concurrent loaders cannot refill from a
# pre-commit snapshot. The TTL is only a safety net for bulk updates that
# bypass ``save``.
SETTINGS_CACHE_TTL_SECONDS = 24 * 60 * 60
# Not ``dispatch:config:``: ``config`` is a reserved routing namespace.
_CACHE_PREFIX = "dispatch:settings:"


class DispatchSettingsCache:
    """Django-cache backed loader for persisted dispatch settings."""

    @staticmethod
    def _cache_key(kind: str, identity: str) -> str:
        return f"{_CACHE_PREFIX}{kind}:{identity}"

    @classmethod
    def _get_raw(cls, kind: str, identity: str, loader: Callable[[], dict]) -> dict:
        cache_key = cls._cache_key(kind, identity)
        try:
            cached = cache.get(cache_key)
            if cached is not None:
                return cached
        except Exception as exc:
            logger.warning("dispatch config cache.get failed key=%s: %s", cache_key, exc)

        raw = loader()
        if not isinstance(raw, dict):
            logger.warning(
                "dispatch config loader returned non-dict kind=%s identity=%s type=%s",
                kind,
                identity,
                type(raw).__name__,
            )
            raw = {}
        try:
            cache.set(cache_key, raw, SETTINGS_CACHE_TTL_SECONDS)
        except Exception as exc:
            logger.warning("dispatch config cache.set failed key=%s: %s", cache_key, exc)
        return raw

    @classmethod
    def _invalidate(cls, kind: str, identity: str) -> None:
        try:
            cache.delete(cls._cache_key(kind, identity))
        except Exception as exc:
            logger.warning("dispatch config cache.delete failed kind=%s identity=%s: %s", kind, identity, exc)

    @classmethod
    def get_queue(cls, namespace: str) -> dict:
        from backend.db_periodic_task.models import DispatchQueueSettings

        return cls._get_raw(
            "queue",
            namespace,
            lambda: DispatchQueueSettings.objects.filter(namespace=namespace).values_list("config", flat=True).first()
            or {},
        )

    @classmethod
    def get_task(cls, task_key: str) -> dict:
        from backend.db_periodic_task.models import DispatchTaskSettings

        return cls._get_raw(
            "task",
            task_key,
            lambda: (
                DispatchTaskSettings.objects.filter(task_key=task_key).values_list("config", flat=True).first() or {}
            ),
        )

    @classmethod
    def invalidate_queue(cls, namespace: str) -> None:
        cls._invalidate("queue", namespace)

    @classmethod
    def invalidate_task(cls, task_key: str) -> None:
        cls._invalidate("task", task_key)
