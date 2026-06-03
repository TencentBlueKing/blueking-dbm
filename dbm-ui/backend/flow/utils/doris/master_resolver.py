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

from django.core.cache import cache

from backend.db_meta.enums import ClusterType
from backend.flow.utils.doris.consts import CACHE_CLUSTER_MASTER

logger = logging.getLogger("flow")


def get_cluster_master(bk_biz_id: int, cluster_domain: str) -> str:
    """
    从监控缓存读取指定 Doris 集群的 master FE，返回 "ip:port"，未命中或缓存异常时返回 ""。

    cache 由 db_periodic_task.local_tasks.doris.sync_cluster_master 周期任务维护，
    value 结构为 {cluster_domain: "ip:port"}。

    本函数对调用方提供"软依赖"语义：任何缓存层异常（key miss / 空值 / 非法 JSON / 非 dict 结构）
    都会被收敛为返回 ""，由调用方走降级逻辑，避免缓存问题影响主流程。

    @param bk_biz_id: 业务 ID
    @param cluster_domain: 集群不变域名（即 Cluster.immute_domain）
    """
    cache_key = f"{CACHE_CLUSTER_MASTER}_{bk_biz_id}_{ClusterType.Doris.value}"
    raw = cache.get(cache_key)
    # key miss / 空串 / None / 空 bytes 等均视为未命中，避免 json.loads 抛 JSONDecodeError、TypeError
    if not raw:
        return ""

    try:
        cache_master_stats = json.loads(raw)
    except (TypeError, ValueError) as e:
        # ValueError 是 JSONDecodeError 的父类
        logger.warning("invalid doris master cache, key=%s, err=%s", cache_key, e)
        return ""

    if not isinstance(cache_master_stats, dict):
        logger.warning(
            "unexpected doris master cache type, key=%s, type=%s",
            cache_key,
            type(cache_master_stats),
        )
        return ""

    return cache_master_stats.get(cluster_domain) or ""
