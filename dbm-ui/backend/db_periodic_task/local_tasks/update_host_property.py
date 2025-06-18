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
from collections import defaultdict
from datetime import datetime, timedelta

from celery.schedules import crontab
from django.core.cache import cache
from django.utils.translation import ugettext as _

from backend.components import CCApi
from backend.db_dirty.models import DirtyMachine
from backend.db_meta.models import Machine
from backend.db_periodic_task.local_tasks.register import register_periodic_task
from backend.db_proxy.constants import DB_CLOUD_MACHINE_EXPIRE_TIME
from backend.utils.redis import RedisConn

logger = logging.getLogger("root")

DEFAULT_BK_EVENT_TYPES = ["update"]
DEFAULT_BK_FIELDS = [
    "idc_city_id",
    "idc_city_name",
    "bk_host_id",
    "bk_os_name",
    "bk_idc_area",
    "bk_idc_area_id",
    "sub_zone",
    "sub_zone_id",
    "rack",
    "rack_id",
    "bk_svr_device_cls_name",
    "idc_name",
    "idc_id",
    "svr_device_class",
]


# 需要更新主机的属性
def update_hosts(host_dict, update_map):
    machines_to_update = []

    for host_id, updates in update_map.items():
        host = host_dict.get(host_id)
        if not host:
            continue

        # 确定哪些字段确实需要更新
        updated_fields = {field: value for field, value in updates.items() if hasattr(host, field)}

        if updated_fields:
            for field, value in updated_fields.items():
                setattr(host, field, value)
            machines_to_update.append(host)

    return machines_to_update


@register_periodic_task(run_every=crontab(hour="*/1", minute=0))
def update_host_property():
    """
    更新主机属性：
    第一次拿前一小时的主机更新事件 后面用拿到更新事件的最后一条事件的bk_cursor继续监听获取事件
    """
    try:
        # 初始化请求参数
        params = {"bk_event_types": DEFAULT_BK_EVENT_TYPES, "bk_fields": DEFAULT_BK_FIELDS, "bk_resource": "host"}

        # 检查缓存中的游标
        machine_cursor = cache.get("machine_cursor")
        if not machine_cursor:
            now = datetime.now()
            one_hour_ago = now - timedelta(hours=1)
            params["bk_start_from"] = int(one_hour_ago.timestamp())
        else:
            params["bk_cursor"] = machine_cursor

        # 获取主机更新事件
        results = CCApi.check_host_event(params, use_admin=True)
        # 如果没有监听到事件， 直接返回
        if not results.get("bk_watched"):
            logger.info(_("没有监听到事件"))
            return

        events = results.get("bk_events", [])

        # 获取更新事件最后一条事件的cursor
        if events:
            last_cursor = events[-1].get("bk_cursor", "")
            if last_cursor:
                cache.set("machine_cursor", last_cursor)

        machine_fields = [
            ("bk_os_name", "bk_os_name"),
            ("bk_idc_area", "bk_idc_area"),
            ("bk_idc_area_id", "bk_idc_area_id"),
            ("bk_sub_zone", "sub_zone"),
            ("bk_sub_zone_id", "sub_zone_id"),
            ("bk_rack", "rack"),
            ("bk_rack_id", "rack_id"),
            ("bk_svr_device_cls_name", "bk_svr_device_cls_name"),
            ("bk_city_id", "idc_city_id"),
        ]

        dirty_machine_fields = [
            ("os_name", "bk_os_name"),
            ("city", "idc_city_name"),
            ("device_class", "svr_device_class"),
            ("sub_zone", "sub_zone"),
            ("rack_id", "rack_id"),
        ]

        host_updates = {
            event["bk_detail"]["bk_host_id"]: {
                field_name: event["bk_detail"].get(detail_name)
                for field_name, detail_name in machine_fields + dirty_machine_fields
            }
            for event in events
            if "bk_detail" in event and "bk_host_id" in event["bk_detail"]
        }

        # 获取需要更新的主机
        relevant_hosts = host_updates.keys()
        machines = {machine.bk_host_id: machine for machine in Machine.objects.filter(bk_host_id__in=relevant_hosts)}
        dirty_machines = {
            dirty_machine.bk_host_id: dirty_machine
            for dirty_machine in DirtyMachine.objects.filter(bk_host_id__in=relevant_hosts)
        }

        # 批量更新machine属性
        machines_to_update = update_hosts(machines, host_updates)
        if machines_to_update:
            Machine.objects.bulk_update(
                machines_to_update, fields=[field for field, _ in machine_fields if hasattr(Machine, field)]
            )

        dirty_machines_to_update = update_hosts(dirty_machines, host_updates)
        if dirty_machines_to_update:
            DirtyMachine.objects.bulk_update(
                dirty_machines_to_update,
                fields=[field for field, _ in dirty_machine_fields if hasattr(DirtyMachine, field)],
            )

    except Exception as e:
        logger.exception(f"Error during sync_update_host_property: {e}")


@register_periodic_task(run_every=crontab(hour=1, minute=0))
def sync_machine_ip_cache():
    """
    定期同步machine表来缓存ip
    注：这里缓存只用于存在性判断，并且接受漏判(目前用于reverse api的校验)
    """
    logger.info("begin to cache machine ips...")

    hosts = Machine.objects.all().values("bk_cloud_id", "ip")
    cloud__ips_map = defaultdict(list)
    for host in hosts:
        cloud__ips_map[host["bk_cloud_id"]].append(host["ip"])

    batch_size = 2000
    # 根据云区域分组缓存ip
    for cloud, ips in cloud__ips_map.items():
        tmp_cache_key = f"cache_cloud_machine_tmp_{cloud}"
        cache_key = f"cache_cloud_machine_{cloud}"

        for index in range(0, len(ips), batch_size):
            RedisConn.sadd(tmp_cache_key, *ips[index : index + batch_size])

        RedisConn.rename(tmp_cache_key, cache_key)
        RedisConn.expire(cache_key, DB_CLOUD_MACHINE_EXPIRE_TIME)

    logger.info("cache machine task is finished, number is %s", len(hosts))
