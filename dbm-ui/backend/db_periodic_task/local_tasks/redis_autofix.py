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
from django.utils import timezone as datetime

from backend.db_periodic_task.local_tasks.register import register_periodic_task
from backend.db_services.redis.autofix.bill import generate_autofix_ticket
from backend.db_services.redis.autofix.enums import AutofixItem, AutofixStatus
from backend.db_services.redis.autofix.models import RedisAutofixCore, RedisAutofixCtl
from backend.db_services.redis.autofix.watcher import (
    get_4_next_watch_ID,
    save_swithed_host_by_cluster,
    watcher_get_by_hosts,
)
from backend.utils.time import datetime2str

logger = logging.getLogger("celery")


@register_periodic_task(run_every=crontab(minute="*/1"))
def watch_dbha_switch():
    """监控DBHA切换日志列表"""

    try:
        onoff = RedisAutofixCtl.objects.get(ctl_name=AutofixItem.AUTOFIX_ENABLE.value)
        if onoff.ctl_value == "off":
            logger.info("hi and bye ^_^")
            return
    except RedisAutofixCtl.DoesNotExist:
        RedisAutofixCtl.objects.create(
            bk_cloud_id=0, bk_biz_id=0, ctl_value="off", ctl_name=AutofixItem.AUTOFIX_ENABLE.value
        ).save()
        return

    # 获取切换列表
    current_id, switch_hosts = watcher_get_by_hosts()
    if len(switch_hosts) == 0:
        RedisAutofixCtl.objects.filter(ctl_name=AutofixItem.DBHA_ID.value).update(
            ctl_value=current_id, update_at=datetime2str(datetime.datetime.now())
        )
        logger.info("no hosts switched , heartbeat update ! next sw_id: {}".format(current_id))
        return

    logger.info("query switch logs :: {}:{}".format(current_id, switch_hosts))
    next_id = get_4_next_watch_ID(current_id, switch_hosts)
    RedisAutofixCtl.objects.filter(ctl_name=AutofixItem.DBHA_ID.value).update(
        ctl_value=next_id, update_at=datetime2str(datetime.datetime.now())
    )
    # 以集群维度聚合 # AutofixStatus.AF_REQRES.value
    save_swithed_host_by_cluster(next_id, switch_hosts)


@register_periodic_task(run_every=crontab(minute="*/1"))
def start_autofix_flow():
    """请求自愈需要的资源"""

    try:
        fixlists = RedisAutofixCore.objects.filter(deal_status=AutofixStatus.AF_TICKET.value)
    except RedisAutofixCore.DoesNotExist:
        logger.info("waiting request resource items ... ")
        return
    if len(fixlists) == 0:
        logger.info("waiting request resource items ... ")
        return

    generate_autofix_ticket(fixlists)
