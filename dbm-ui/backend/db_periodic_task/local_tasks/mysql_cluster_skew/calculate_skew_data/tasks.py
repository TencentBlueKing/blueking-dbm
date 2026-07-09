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
import math

from celery.schedules import crontab
from django.core.cache import cache
from django.db.models.functions import Mod

from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster
from backend.db_periodic_task.local_tasks import register_periodic_task, start_new_span
from backend.db_periodic_task.local_tasks.mysql_cluster_skew.calculate_skew_data.skew_detect import (
    calculate_clusters_skew,
)
from backend.db_periodic_task.utils import TimeUnit, calculate_countdown
from backend.db_report.models.cluster_skew_detection import ClusterSkewDetection

logger = logging.getLogger("celery.mysql_cluster_skew.calculate_skew_data.task")


def _dispatch_cluster_skew_task(cluster_type: ClusterType, batch_size: int):
    """按集群类型分发倾斜检测 Celery 子任务。

    防雪崩策略：
    1. 分片：按 cluster id 取模将集群拆成多批，每批最多 batch_size 个，避免单次任务处理全量集群。
    2. 错峰：通过 calculate_countdown 将各批次随机平摊到 5 分钟窗口内执行，削峰填谷。
    3. 运行中跳过：投递前 cache.add 占位锁；若上一周期同批次任务尚未完成（锁未释放），跳过本次投递，
       防止任务堆积拖垮 worker / 监控查询。
       子任务结束后在 finally 中释放锁；apply_async 失败时也会主动 delete 锁。

    :param cluster_type: 集群类型（TenDBHA / TenDBCluster）
    :param batch_size: 每批处理的集群数量上限
    """
    try:
        ClusterSkewDetection.objects.using("doris").exists()
    except Exception:  # noqa
        logger.warning("dispatch skip, doris unavailable: cluster_type=%s", cluster_type.value)
        return

    clusters_q = Cluster.objects.filter(cluster_type=cluster_type)
    cluster_count = clusters_q.count()
    hash_cnt = math.ceil(cluster_count / batch_size)
    scheduled, skipped_lock, empty_batch = 0, 0, 0

    logger.info(
        "dispatch start: cluster_type=%s cluster_count=%d hash_cnt=%d batch_size=%d",
        cluster_type.value,
        cluster_count,
        hash_cnt,
        batch_size,
    )

    for hash_value in range(hash_cnt):
        lock_key = f"mysql_cluster_skew:{cluster_type.value}:{hash_value}"

        cluster_domains = list(
            clusters_q.annotate(id_hash_value=Mod("id", hash_cnt))
            .filter(id_hash_value=hash_value)
            .values_list("immute_domain", flat=True)
        )
        if not cluster_domains:
            empty_batch += 1
            logger.warning("empty batch: cluster_type=%s hash_value=%d", cluster_type.value, hash_value)
            continue

        countdown = calculate_countdown(count=hash_cnt, index=hash_value, duration=2 * TimeUnit.MINUTE)

        if not cache.add(lock_key, 1, timeout=3600):
            skipped_lock += 1
            logger.warning("batch skip, lock held: lock_key=%s cluster_count=%d", lock_key, len(cluster_domains))
            continue

        try:
            with start_new_span(calculate_clusters_skew):
                calculate_clusters_skew.apply_async(
                    args=[cluster_type.value, cluster_domains, lock_key],
                    countdown=countdown,
                )
            scheduled += 1
            logger.info(
                "batch scheduled: lock_key=%s hash_value=%d cluster_count=%d countdown=%ds",
                lock_key,
                hash_value,
                len(cluster_domains),
                countdown,
            )
        except Exception:  # noqa
            logger.exception(
                "batch schedule failed: lock_key=%s hash_value=%d cluster_count=%d",
                lock_key,
                hash_value,
                len(cluster_domains),
            )
            cache.delete(lock_key)

    logger.info(
        "dispatch done: cluster_type=%s scheduled=%d skipped_lock=%d empty_batch=%d total_hash=%d",
        cluster_type.value,
        scheduled,
        skipped_lock,
        empty_batch,
        hash_cnt,
    )


@register_periodic_task(run_every=crontab(minute="*/5"))
def calculate_tendbha_skew():
    dispatch_key = f"mysql_cluster_skew:dispatch:{ClusterType.TenDBHA.value}"
    if not cache.add(dispatch_key, 1, timeout=600):
        logger.warning("dispatch skip, lock held: %s", dispatch_key)
        return
    try:
        _dispatch_cluster_skew_task(ClusterType.TenDBHA, 20)
    except Exception:  # noqa
        logger.exception("dispatch failed: %s", dispatch_key)
        raise
    finally:
        cache.delete(dispatch_key)


@register_periodic_task(run_every=crontab(minute="*/5"))
def calculate_tendbcluster_skew():
    dispatch_key = f"mysql_cluster_skew:dispatch:{ClusterType.TenDBCluster.value}"
    if not cache.add(dispatch_key, 1, timeout=600):
        logger.warning("dispatch skip, lock held: %s", dispatch_key)
        return
    try:
        _dispatch_cluster_skew_task(ClusterType.TenDBCluster, 5)
    except Exception:  # noqa
        logger.exception("dispatch failed: %s", dispatch_key)
        raise
    finally:
        cache.delete(dispatch_key)
