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

from backend.db_periodic_task.local_tasks import register_periodic_task

from .cluster_apply_destroy import get_city_list
from .failover_drill_unit import ha_failover_drill_unit, spider_failover_drill_unit

logger = logging.getLogger("celery")


@register_periodic_task(run_every=crontab(minute=3, hour=10))
def mysql_failover_drill_task():
    """
    mysql回档演练定时任务
    上架
    容灾演练（触发dbha）
    下架
    @return:
    """
    logger.info("start mysql failover drill")
    city_list = get_city_list()
    # 不同城市的容灾任务
    for city in city_list:
        # 异步任务 每个城市 不同集群类型
        ha_failover_drill_unit.apply_async(args=(city,))


@register_periodic_task(run_every=crontab(minute=3, hour=10))
def spider_failover_drill_task():
    """
    spider回档演练定时任务
    上架
    容灾演练（触发dbha）
    下架
    @return:
    """
    logger.info("start spider failover drill")
    city_list = get_city_list()
    # 不同城市的容灾任务
    for city in city_list:
        # 异步任务 每个城市
        spider_failover_drill_unit.apply_async(args=(city,))
