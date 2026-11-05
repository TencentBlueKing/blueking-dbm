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
from dataclasses import asdict

from celery.schedules import crontab
from django.db.models import Q
from django.forms.models import model_to_dict
from django.utils.translation import gettext as _

from backend import env
from backend.db_meta.exceptions import DBMetaException
from backend.db_periodic_task.constants import FailoverDrillVersion
from backend.db_periodic_task.local_tasks import register_periodic_task
from backend.db_periodic_task.local_tasks.common.failover_drill_base import delete_old_failover_drill_records

from ...models import FailoverDrillConfig
from .failover_drill import (
    PROXYLESS_CLUSTER_TYPES,
    V1_DRILL_CLUSTER_TYPES,
    V2_DRILL_CLUSTER_TYPES,
    FailoverDrillTargetType,
    build_drill_targets,
)
from .failover_drill_unit import failover_drill_unit

logger = logging.getLogger("celery")


@register_periodic_task(run_every=crontab(day_of_month=1, hour=0, minute=0))
def delete_outdated_drill_records():
    """
    删除365天以前的Redis切换演练记录
    每月1号凌晨0点执行
    """
    total_deleted = 0
    target_types = sorted(set(V1_DRILL_CLUSTER_TYPES) | set(V2_DRILL_CLUSTER_TYPES))

    for cluster_type in target_types:
        try:
            deleted_count = delete_old_failover_drill_records([cluster_type], days_look_back=365)
            total_deleted += deleted_count
            logger.info(
                _("Deleted {} outdated redis failover drill records for cluster_type: {}").format(
                    deleted_count, cluster_type
                )
            )
        except Exception as e:
            logger.error(_("Failed to delete outdated records for cluster_type {}: {}").format(cluster_type, e))

    logger.info(_("Total deleted {} outdated redis failover drill records").format(total_deleted))


def dispatch_failover_drill(target_type: str):
    """
    按配置行分发演练：每行按自己的 version 独立演练，每个演练目标一个异步单元
    - v1 只演练 TendisCache（Twemproxy）集群
    - v2 演练所有支持自愈的 Redis 集群类型；没有接入层的类型跳过 proxy 演练
    """
    try:
        confs = list(
            FailoverDrillConfig.objects.filter(switch_flag=True).filter(
                Q(version=FailoverDrillVersion.V1.value, cluster_type__in=V1_DRILL_CLUSTER_TYPES)
                | Q(version=FailoverDrillVersion.V2.value, cluster_type__in=V2_DRILL_CLUSTER_TYPES)
            )
        )
    except Exception as e:
        raise DBMetaException(message=_("Unexpected error happened when reading FailoverDrillConf {}".format(e)))

    if not confs:
        logger.info(_("Redis容灾演练未配置或配置关闭 Bye~"))
        return

    logger.info(_("Start Redis {} failover drill".format(target_type)))
    for conf_obj in confs:
        if conf_obj.version == FailoverDrillVersion.V2 and not env.ENABLE_DBHA_V2:
            logger.info(_("ENABLE_DBHA_V2 未开启，跳过 v2 容灾演练配置 #{}".format(conf_obj.id)))
            continue
        if target_type == FailoverDrillTargetType.PROXY and conf_obj.cluster_type in PROXYLESS_CLUSTER_TYPES:
            logger.info(_("集群类型 {} 没有接入层，跳过 proxy 演练，配置 #{}".format(conf_obj.cluster_type, conf_obj.id)))
            continue

        conf = model_to_dict(conf_obj)
        conf["target_type"] = target_type
        logger.info(_("Configuration: {}".format(conf)))
        try:
            targets = build_drill_targets(conf)
        except Exception as e:
            logger.exception(_("生成演练目标失败，配置 #{}: {}".format(conf_obj.id, e)))
            continue

        for target in targets:
            failover_drill_unit.apply_async(args=(asdict(target), conf))


@register_periodic_task(run_every=crontab(hour=9, minute=0))
def proxy_failover_drill_task():
    """
    redis容灾演练定时任务 针对TendisCache集群的Proxy
    不能与Backend演练同时执行
    """
    dispatch_failover_drill(FailoverDrillTargetType.PROXY)


@register_periodic_task(run_every=crontab(hour=9, minute=30))
def redis_failover_drill_task():
    """
    redis容灾演练定时任务 针对TendisCache集群的Backend
    不能与Proxy演练同时执行
    """
    dispatch_failover_drill(FailoverDrillTargetType.BACKEND)
