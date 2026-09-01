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

from django.core.cache import cache

from backend.dbm_aiagent.mcp_tools.exceptions import DBMMcpBaseException

logger = logging.getLogger("root")

# 单机器任务的分布式锁缓存键模板。任务异步执行（脚本 60s 超时 + 调度延迟），
# 锁按 TTL 自动过期兜底释放，避免任务结束前同机器重复下发叠加扫描压力。
LOCK_CACHE_KEY_TPL = "dbm_aiagent:bkjob_lock:{name}:{bk_cloud_id}:{ip}"
# 锁存活时间：需覆盖脚本最长执行时间（约 60s）及作业平台下发/调度延迟，取 5 分钟
LOCK_TTL_SECONDS = 300


def acquire_host_locks(name: str, bk_cloud_id: int, ips: list[str], ttl: int = LOCK_TTL_SECONDS) -> list[str]:
    """
    对目标机器逐一加分布式锁，返回加锁成功的机器 IP 列表。

    任一台机器加锁失败（已有同名任务在执行），会回滚已加锁项并抛出异常，
    保证"要么整批放行、要么整批拒绝"，不会出现半批任务下发。
    cache 不可用（基础设施异常）时放行该机器，由脚本层 flock 兜底互斥。
    """
    locked: list[str] = []
    try:
        for ip in sorted(set(ips)):
            key = LOCK_CACHE_KEY_TPL.format(name=name, bk_cloud_id=bk_cloud_id, ip=ip)
            try:
                acquired = cache.add(key, "1", timeout=ttl)
            except Exception:  # noqa: BLE001 - cache 异常不应阻塞任务下发
                logger.warning("bkjob lock cache unavailable, skip lock for %s", key)
                continue
            if not acquired:
                raise DBMMcpBaseException(msg=f"machine {ip} has a running {name} task, please wait for it to finish")
            locked.append(ip)
    except Exception:
        # 回滚已加锁项，避免锁泄漏导致后续任务被永久拒绝
        for ip in locked:
            cache.delete(LOCK_CACHE_KEY_TPL.format(name=name, bk_cloud_id=bk_cloud_id, ip=ip))
        raise
    return locked


def release_host_locks(name: str, bk_cloud_id: int, ips: list[str]) -> None:
    """释放目标机器的任务锁（任务为异步执行，常规路径由 TTL 自动过期，无需显式释放）。"""
    for ip in sorted(set(ips)):
        try:
            cache.delete(LOCK_CACHE_KEY_TPL.format(name=name, bk_cloud_id=bk_cloud_id, ip=ip))
        except Exception:  # noqa: BLE001
            logger.warning("bkjob lock cache delete failed for %s", ip)
