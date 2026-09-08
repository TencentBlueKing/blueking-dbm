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
from abc import ABC, abstractmethod
from typing import List, Optional, Set, Tuple, Type

from django.core.cache import cache

logger = logging.getLogger("root")


class AlarmCallback(ABC):
    """
    告警回调基类，所有组件的告警回调套餐必须继承此基类并注册。

    使用方式：
        1. 继承 AlarmCallback
        2. 实现 callback() 方法，内部根据策略名等字段自行判断是否处理
        3. 定义 SUPPORTED_CLUSTER_TYPES 类属性，指定该回调类支持的集群类型集合
        4. 子类会自动注册到 _registry 中

    分发逻辑：
        AlarmCallback.dispatch(callback_data)
        会先从告警数据中解析 cluster_type（优先从 dimensions 获取，缺失时通过 cluster_domain 反查数据库），
        然后只分发给支持该 cluster_type 的回调子类。

    频率限制：
        在 STRATEGY_HANDLERS 的 condition 中通过 "ratelimit" 字段配置，格式为 "次数 / 小时数"。
        示例：
            "1 / 6"   — 首次触发后 6 小时内最多触发 1 次（冷却 6 小时）
            "2 / 24"  — 首次触发后 24 小时内最多触发 2 次
            "0 / 24"  — 不限频（默认）
        不配置 ratelimit 或配置为 "0 / N" 时，不做频率限制。
    """

    # 注册表：存储所有已注册的回调子类
    _registry: List[Type["AlarmCallback"]] = []

    # 子类需定义此属性，指定支持的集群类型值集合（字符串）。
    # 为空集合表示不限制，接受所有集群类型。
    SUPPORTED_CLUSTER_TYPES: Set[str] = set()

    def __init_subclass__(cls, **kwargs):
        """子类定义时自动注册到 registry"""
        super().__init_subclass__(**kwargs)
        # 只注册非抽象的具体实现类
        if not getattr(cls, "__abstractmethods__", None):
            AlarmCallback._registry.append(cls)

    @classmethod
    @abstractmethod
    def callback(cls, callback_data: dict) -> None:
        """
        执行告警回调处理逻辑。
        子类必须实现此方法，内部根据策略名等字段自行判断是否需要处理。

        :param callback_data: 告警回调数据
        """
        raise NotImplementedError

    @classmethod
    def supports_cluster_type(cls, cluster_type: Optional[str]) -> bool:
        """
        判断当前回调类是否支持给定的集群类型。
        如果 SUPPORTED_CLUSTER_TYPES 为空集合，表示不限制，接受所有类型。
        如果 cluster_type 为空（无法解析），也放行，由子类内部自行判断。
        """
        if not cls.SUPPORTED_CLUSTER_TYPES:
            return True
        if not cluster_type:
            return True
        return cluster_type in cls.SUPPORTED_CLUSTER_TYPES

    @classmethod
    def _resolve_cluster_type(cls, callback_data: dict) -> Optional[str]:
        """
        从告警回调数据中解析 cluster_type。
        优先从 dimensions 中获取，缺失时通过 cluster_domain 反查数据库。
        """
        callback_message = callback_data.get("callback_message", {})
        dimensions = callback_message.get("event", {}).get("dimensions", {})
        cluster_type = dimensions.get("cluster_type", "")
        cluster_domain = dimensions.get("cluster_domain", "")

        if not cluster_type and cluster_domain:
            try:
                from backend.db_meta.models import Cluster

                cluster = Cluster.objects.filter(immute_domain=cluster_domain).first()
                if cluster:
                    cluster_type = cluster.cluster_type
                    logger.info(
                        "[alarm_callback] Resolved cluster_type='%s' by cluster_domain='%s'",
                        cluster_type,
                        cluster_domain,
                    )
                else:
                    logger.warning(
                        "[alarm_callback] No cluster record found by cluster_domain='%s'; cluster_type cannot be resolved",
                        cluster_domain,
                    )
            except Exception as e:
                logger.exception("[alarm_callback] Failed to resolve cluster_type: %s", e)

        return cluster_type or None

    @staticmethod
    def _parse_ratelimit(ratelimit: str) -> Tuple[int, int]:
        """
        解析频率限制配置字符串。

        :param ratelimit: 格式为 "次数 / 小时数"，如 "2 / 24"、"0 / 24"
        :return: (max_count, hours) 元组
        :raises ValueError: 格式不合法时抛出
        """
        parts = ratelimit.split("/")
        if len(parts) != 2:
            raise ValueError(f"Invalid ratelimit format: '{ratelimit}', expected 'count / hours'")
        max_count = int(parts[0].strip())
        hours = int(parts[1].strip())
        if hours <= 0:
            raise ValueError(f"Ratelimit hours must be greater than 0: '{ratelimit}'")
        return max_count, hours

    @classmethod
    def _get_ratelimit_cache_key(cls, cluster_domain: str, handler_name: str, keyword: str, hours: int) -> str:
        """
        生成频率限制的 cache key。
        格式: alarm_cb_rl:{ClassName}:{handler_name}:{keyword}:{cluster_domain}:{hours}h

        key 不按自然时间切桶，而是从首次触发开始设置 TTL，形成冷却窗口。
        """
        return f"alarm_cb_rl:{cls.__name__}:{handler_name}:{keyword}:{cluster_domain}:{hours}h"

    @classmethod
    def _get_cooldown_seconds(cls, hours: int) -> int:
        """计算冷却窗口秒数，用作 cache key 的 TTL。"""
        return max(hours * 3600, 1)

    @classmethod
    def check_rate_limit(cls, cluster_domain: str, handler_name: str, keyword: str, ratelimit: str = "") -> bool:
        """
        检查指定 cluster_domain + handler_name + keyword 是否超过频率限制。

        :param cluster_domain: 集群域名
        :param handler_name: 处理函数名
        :param keyword: 匹配的策略关键字
        :param ratelimit: 频率限制配置，格式 "次数 / 小时数"，如 "2 / 24"。
                          空字符串或 "0 / N" 表示不限频。
        :return: True 表示允许执行，False 表示已超限需跳过
        """
        if not ratelimit:
            return True

        try:
            max_count, hours = cls._parse_ratelimit(ratelimit)
        except ValueError as e:
            logger.warning("[alarm_callback] Failed to parse rate limit config, allow request: %s", e)
            return True

        if max_count <= 0:
            # "0 / N" 表示不限频
            return True

        if not cluster_domain:
            # 没有 cluster_domain 无法做频率限制，放行
            return True

        cache_key = cls._get_ratelimit_cache_key(cluster_domain, handler_name, keyword, hours)
        ttl = cls._get_cooldown_seconds(hours)

        try:
            if cache.add(cache_key, 1, timeout=ttl):
                current_count = 1
            else:
                current_count = cache.incr(cache_key)

            if current_count > max_count:
                logger.warning(
                    "[alarm_callback] Rate limit exceeded: %s %s(keyword=%s) has triggered %d times "
                    "within %dh cooldown window since first trigger (limit %d), skip",
                    cluster_domain,
                    handler_name,
                    keyword,
                    current_count,
                    hours,
                    max_count,
                )
                return False

            logger.info(
                "[alarm_callback] Rate limit count: %s %s(keyword=%s) triggered %d times "
                "within %dh cooldown window since first trigger (limit %d)",
                cluster_domain,
                handler_name,
                keyword,
                current_count,
                hours,
                max_count,
            )
            return True
        except Exception as e:
            logger.exception("[alarm_callback] Rate limit check failed, allow request: %s", e)
            return True

    @classmethod
    def dispatch(cls, callback_data: dict) -> None:
        """
        将告警回调数据分发给支持对应 cluster_type 的处理器。
        先解析 cluster_type，再根据各子类的 SUPPORTED_CLUSTER_TYPES 过滤，
        只调用匹配的处理器。

        :param callback_data: 告警回调数据
        """
        cluster_type = cls._resolve_cluster_type(callback_data)
        logger.info("[alarm_callback] Resolved cluster_type='%s', start dispatching callback", cluster_type)

        for handler_cls in cls._registry:
            if not handler_cls.supports_cluster_type(cluster_type):
                logger.info(
                    "[alarm_callback] Skip handler %s: cluster_type='%s' is not in supported types %s",
                    handler_cls.__name__,
                    cluster_type,
                    handler_cls.SUPPORTED_CLUSTER_TYPES,
                )
                continue
            try:
                handler_cls.callback(callback_data)
            except Exception as e:
                logger.exception(f"[alarm_callback] processor {handler_cls.__name__} callback error: {e}")
