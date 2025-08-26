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

from celery.schedules import crontab
from django.forms.models import model_to_dict
from django.utils.translation import ugettext as _

from backend.db_meta.enums import ClusterType
from backend.db_meta.exceptions import DBMetaException
from backend.db_periodic_task.local_tasks import register_periodic_task

from ...models import FailoverDrillConfig
from .failover_drill_unit import failover_drill_unit
from .utils import get_city_list

logger = logging.getLogger("celery")


@register_periodic_task(run_every=crontab(hour=9, minute=0))
def proxy_failover_drill_task():
    """
    redis容灾演练定时任务 针对TendisCache集群的Proxy
    不能与Backend演练同时执行
    """
    try:
        conf = FailoverDrillConfig.objects.get(cluster_type=ClusterType.TendisTwemproxyRedisInstance.value)
    except FailoverDrillConfig.DoesNotExist:
        logger.info(_("Redis容灾演练未配置 Bye~"))
        return
    except Exception as e:
        raise DBMetaException(message=_("Unexpected error happened when reading FailoverDrillConf {}".format(e)))

    if not conf.switch_flag:
        logger.info(_("Redis容灾演练配置关闭 Bye~"))
        return

    conf = model_to_dict(conf)
    conf["target_type"] = "proxy"

    logger.info(_("Start Redis proxy failover drill"))
    logger.info(_("Configuration: {}".format(conf)))
    city_list = get_city_list()
    for city in city_list:
        failover_drill_unit.apply_async(args=(city, conf))


@register_periodic_task(run_every=crontab(hour=9, minute=30))
def redis_failover_drill_task():
    """
    redis容灾演练定时任务 针对TendisCache集群的Backend
    不能与Proxy演练同时执行
    """
    try:
        conf = FailoverDrillConfig.objects.get(cluster_type=ClusterType.TendisTwemproxyRedisInstance.value)
    except FailoverDrillConfig.DoesNotExist:
        logger.info(_("Redis容灾演练未配置 Bye~"))
        return
    except Exception as e:
        raise DBMetaException(message=_("Unexpected error happened when reading FailoverDrillConf {}".format(e)))

    if not conf.switch_flag:
        logger.info(_("Redis容灾演练配置关闭 Bye~"))
        return

    conf = model_to_dict(conf)
    conf["target_type"] = "backend"

    logger.info(_("Start Redis backend failover drill"))
    logger.info(_("Configuration: {}".format(conf)))
    city_list = get_city_list()
    for city in city_list:
        failover_drill_unit.apply_async(args=(city, conf))
