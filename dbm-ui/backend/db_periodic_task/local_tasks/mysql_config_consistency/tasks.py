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
import importlib
import logging
from typing import List

from blueapps.core.celery.celery import app
from celery.schedules import crontab
from django.core.cache import cache
from django.utils import timezone
from django.utils.translation import gettext as _

from backend.db_meta.enums import ClusterPhase
from backend.db_meta.models import Cluster
from backend.db_periodic_task.register import register_periodic_task

_config_mod = importlib.import_module("backend.db_periodic_task.local_tasks.mysql_config_consistency.config")
_checker_mod = importlib.import_module("backend.db_periodic_task.local_tasks.mysql_config_consistency.checker")
_span_mod = importlib.import_module("backend.db_periodic_task.local_tasks.context_manager")

MysqlConfigConsistencyConfig = _config_mod.MysqlConfigConsistencyConfig
SUPPORTED_CLUSTER_TYPES = _checker_mod.SUPPORTED_CLUSTER_TYPES
TEMP_CLUSTER_DOMAIN_RE = _checker_mod.TEMP_CLUSTER_DOMAIN_RE
check_single_cluster_config_consistency = _checker_mod.check_single_cluster_config_consistency
delete_inactive_cluster_reports = _checker_mod.delete_inactive_cluster_reports
delete_old_consistency_reports = _checker_mod.delete_old_consistency_reports
start_new_span = _span_mod.start_new_span

logger = logging.getLogger("celery")

WORKER_SOFT_TIME_LIMIT = 180
WORKER_HARD_TIME_LIMIT = 240
DISPATCH_LOCK_TTL = 3600


def _cluster_lock_key(schedule_date: str, cluster_id: int) -> str:
    return f"mysql_config_consistency:{schedule_date}:{cluster_id}"


def _list_candidate_cluster_ids(config: MysqlConfigConsistencyConfig) -> List[int]:
    qs = Cluster.objects.filter(
        cluster_type__in=SUPPORTED_CLUSTER_TYPES,
        phase=ClusterPhase.ONLINE.value,
    )
    if config.bizs_ignored:
        qs = qs.exclude(bk_biz_id__in=config.bizs_ignored)
    if config.clusters_ignored:
        qs = qs.exclude(id__in=config.clusters_ignored)

    cluster_ids: List[int] = []
    for cluster_id, domain in qs.order_by("id").values_list("id", "immute_domain"):
        if TEMP_CLUSTER_DOMAIN_RE.match((domain or "").lower()):
            continue
        cluster_ids.append(cluster_id)
    return cluster_ids


@register_periodic_task(run_every=crontab(day_of_week=0, hour=3, minute=15))
def mysql_config_consistency_check_task():
    """每周日凌晨 03:15 分发 MySQL / TenDBCluster 关键配置一致性巡检任务。"""
    config = MysqlConfigConsistencyConfig.from_settings()
    if not config.enabled:
        logger.info(_("MySQL 配置一致性巡检已禁用，跳过本次调度"))
        return

    delete_old_consistency_reports(days=config.retention_days)
    delete_inactive_cluster_reports()
    cluster_ids = _list_candidate_cluster_ids(config)
    if not cluster_ids:
        logger.info(_("MySQL 配置一致性巡检: 无待巡检集群"))
        return

    schedule_date = timezone.localdate().isoformat()
    total = len(cluster_ids)
    window = max(0, int(config.dispatch_window_seconds or 0))
    lock_ttl = max(DISPATCH_LOCK_TTL, window + WORKER_HARD_TIME_LIMIT + 600)
    dispatched = 0

    for idx, cluster_id in enumerate(cluster_ids):
        lock_key = _cluster_lock_key(schedule_date, cluster_id)
        if not cache.add(lock_key, 1, timeout=lock_ttl):
            logger.info(_("配置一致性巡检防重锁命中，跳过投递: cluster_id={}").format(cluster_id))
            continue

        countdown = int((idx * window) / total) if total > 1 and window > 0 else 0
        try:
            with start_new_span(run_cluster_config_consistency_check):
                run_cluster_config_consistency_check.apply_async(
                    args=[cluster_id, lock_key],
                    countdown=countdown,
                )
            dispatched += 1
        except Exception as exc:  # noqa: BLE001
            cache.delete(lock_key)
            logger.error(
                _("配置一致性巡检投递失败: cluster_id={} err={}").format(cluster_id, str(exc)),
                exc_info=True,
            )

    logger.info(_("MySQL 配置一致性巡检调度完成: 候选={}, 已投递={}").format(total, dispatched))


@app.task(soft_time_limit=WORKER_SOFT_TIME_LIMIT, time_limit=WORKER_HARD_TIME_LIMIT)
def run_cluster_config_consistency_check(cluster_id: int, lock_key: str = ""):
    """单集群关键配置一致性巡检 Worker。"""
    try:
        reports = check_single_cluster_config_consistency(cluster_id=cluster_id)
        logger.info(_("配置一致性巡检完成: cluster_id={} 产出报告数={}").format(cluster_id, len(reports)))
    except Exception as exc:  # noqa: BLE001
        logger.error(_("配置一致性巡检异常: cluster_id={} err={}").format(cluster_id, str(exc)), exc_info=True)
    finally:
        if lock_key:
            try:
                cache.delete(lock_key)
            except Exception as exc:  # noqa: BLE001
                logger.warning(_("释放配置一致性巡检锁失败: lock_key={} err={}").format(lock_key, str(exc)))
