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
import datetime
import glob
import json
import logging
import os

from celery.schedules import crontab
from django_redis import get_redis_connection

from backend import env
from backend.components import BKMonitorV3Api
from backend.configuration.constants import DEFAULT_DB_ADMINISTRATORS, PLAT_BIZ_ID
from backend.configuration.models import DBAdministrator
from backend.db_monitor.constants import MONITOR_EVENTS_PREFIX, TPLS_ALARM_DIR, TargetPriority
from backend.db_monitor.exceptions import BkMonitorSaveAlarmException
from backend.db_monitor.models import DispatchGroup, MonitorPolicy, NoticeGroup
from backend.db_monitor.tasks import update_app_policy

from .register import register_periodic_task

logger = logging.getLogger("celery")


@register_periodic_task(run_every=crontab(minute="*/2"))
def update_local_notice_group():
    """同步告警组"""

    now = datetime.datetime.now()
    logger.info("[local_notice_group] start update local group at: %s", now)

    dbas = DBAdministrator.objects.all()
    updated_groups, created_groups = 0, 0

    for dba in dbas:
        receiver_users = dba.users or DEFAULT_DB_ADMINISTRATORS

        try:
            group_name = f"{dba.get_db_type_display()}_DBA"
            logger.info("[local_notice_group] update_or_create notice group: %s", group_name)

            obj, created = NoticeGroup.objects.update_or_create(
                defaults={
                    "name": group_name,
                    "receivers": [{"id": user, "type": "user"} for user in receiver_users],
                },
                bk_biz_id=dba.bk_biz_id,
                db_type=dba.db_type,
                is_built_in=True,
            )

            if created:
                created_groups += 1
            else:
                updated_groups += 1
        except Exception as e:
            logger.error("[local_notice_group] update_or_create notice group error: %s", e)
            continue

    logger.info(
        "[local_notice_group] finish update local group end: %s, create_cnt: %s, update_cnt: %s",
        datetime.datetime.now() - now,
        created_groups,
        updated_groups,
    )


@register_periodic_task(run_every=crontab(minute="*/5"))
def sync_plat_monitor_policy():
    """同步平台告警策略"""

    def get_bkm_strategy(name, bk_biz_id=env.DBA_APP_BK_BIZ_ID):
        res = BKMonitorV3Api.search_alarm_strategy_v3(
            {
                "page": 1,
                "page_size": 1,
                "conditions": [{"key": "name", "value": name}],
                "bk_biz_id": bk_biz_id,
                "with_notice_group": False,
                "with_notice_group_detail": False,
            },
            use_admin=True,
        )

        # 批量获取策略
        strategy_config_list = res["strategy_config_list"]
        return strategy_config_list[0] if strategy_config_list else None

    now = datetime.datetime.now()
    logger.warning("[sync_plat_monitor_policy] sync bkm alarm policy start: %s", now)

    # 逐个json导入，本地+远程
    updated_policies = 0
    alarm_tpls = glob.glob(os.path.join(TPLS_ALARM_DIR, "*.json"))

    for alarm_tpl in alarm_tpls:
        with open(alarm_tpl, "r") as f:
            template_dict = json.loads(f.read())

            # just for test
            # template_dict["name"] = template_dict["name"] + "-" + get_random_string(5)

            # patch template
            template_dict["details"]["labels"] = list(set(template_dict["details"]["labels"]))
            template_dict["details"]["name"] = template_dict["name"]
            template_dict["details"]["priority"] = TargetPriority.PLATFORM.value
            # 平台策略仅开启基于分派通知
            template_dict["details"]["notice"]["options"]["assign_mode"] = ["by_rule"]

            policy = MonitorPolicy(**template_dict)

        policy_name = policy.name
        logger.info("[sync_plat_monitor_policy] start sync bkm alarm policy: %s " % policy_name)
        try:
            synced_policy = MonitorPolicy.objects.get(
                bk_biz_id=policy.bk_biz_id, db_type=policy.db_type, name=policy_name
            )

            if synced_policy.version >= policy.version:
                logger.info("[sync_plat_monitor_policy] skip same version alarm: %s " % policy_name)
                continue

            for keeped_field in MonitorPolicy.KEEPED_FIELDS:
                setattr(policy, keeped_field, getattr(synced_policy, keeped_field))

            policy.details["id"] = synced_policy.monitor_policy_id
            logger.info("[sync_plat_monitor_policy] update bkm alarm policy: %s " % policy_name)
        except MonitorPolicy.DoesNotExist:
            # # 支持从监控反向同步
            # bkm_strategy = get_bkm_strategy(policy_name)
            # if bkm_strategy:
            #     policy.details = bkm_strategy
            #     logger.info("[sync_plat_monitor_policy] sync and update bkm alarm policy: %s " % policy_name)
            # else:
            #     logger.info("[sync_plat_monitor_policy] create bkm alarm policy: %s " % policy_name)
            logger.info("[sync_plat_monitor_policy] create bkm alarm policy: %s " % policy_name)

        try:
            # fetch targets/test_rules/notify_rules/notify_groups from parent details
            for attr, value in policy.parse_details().items():
                setattr(policy, attr, value)

            policy.save()
            updated_policies += 1
            logger.error("[sync_plat_monitor_policy] save bkm alarm policy success: %s", policy_name)
        except BkMonitorSaveAlarmException as e:
            logger.error("[sync_plat_monitor_policy] save bkm alarm policy failed: %s, %s ", policy_name, e)

    logger.warning(
        "[sync_plat_monitor_policy] finish sync bkm alarm policy end: %s, update_cnt: %s",
        datetime.datetime.now() - now,
        updated_policies,
    )


@register_periodic_task(run_every=crontab(minute="*/5"))
def sync_plat_dispatch_policy():
    """同步平台分派通知策略
    按照app_id->db_type来拆分策略：
        bk_biz_id=0: db_type=redis and policy=1,2,3 -> notify_group: 1
        bk_biz_id>0: db_type=redis and policy=1,2,3 and app_id=6 -> notify_group: 2
    """

    logger.info("sync_plat_dispatch_policy started")
    # 同步平台/业务分派策略
    for bk_biz_id in NoticeGroup.objects.exclude(monitor_group_id=0).values_list("bk_biz_id", flat=True).distinct():
        latest_rules = DispatchGroup.get_rules(bk_biz_id)
        try:
            dispatch_group = DispatchGroup.objects.get(bk_biz_id=bk_biz_id)
            # 暂时只需比对db_type有没有增减，没有，则无需处理
            # if len(latest_rules) != len(dispatch_group.rules):
            logger.info("sync_plat_dispatch_policy: update biz_rules(%s)\n %s \n", bk_biz_id, latest_rules)
            dispatch_group.rules = latest_rules
            dispatch_group.save()
        except DispatchGroup.DoesNotExist:
            logger.info("sync_plat_dispatch_policy: create biz_rules(%s)\n %s \n", bk_biz_id, latest_rules)
            dispatch_group = DispatchGroup(bk_biz_id=bk_biz_id, rules=latest_rules)
            dispatch_group.save()


@register_periodic_task(run_every=crontab(minute="*/5"))
def sync_custom_monitor_policy():
    """同步自定义监控策略的告警组设置
    1. 提取各业务各db类型的最新"业务dba"告警组
    2. 逐个业务逐个db类型比对:
    """

    logger.info("sync_custom_monitor_policy started")
    cloned_policies = MonitorPolicy.objects.exclude(bk_biz_id=PLAT_BIZ_ID)
    bk_biz_ids = cloned_policies.values_list("bk_biz_id", flat=True).distinct()

    for bk_biz_id in bk_biz_ids:
        plat_groups = NoticeGroup.get_groups(PLAT_BIZ_ID, id_name="id")
        expected_groups = NoticeGroup.get_groups(bk_biz_id, id_name="id")

        # 逐个db类型更新
        for db_type in cloned_policies.filter(bk_biz_id=bk_biz_id).values_list("db_type", flat=True).distinct():
            plat_group = plat_groups.get(db_type)
            expected_group = expected_groups.get(db_type, plat_group)

            logger.info("sync_custom_monitor_policy: %s, %s, %s", bk_biz_id, expected_group, db_type)
            update_app_policy(bk_biz_id, expected_group, db_type)


@register_periodic_task(run_every=crontab(minute="*/5"))
def sync_monitor_policy_events():
    """
    同步各监控策略的告警事件数量
    """

    logger.info("sync_monitor_policy_events started")

    event_counts = {}
    for bk_biz_id in MonitorPolicy.objects.values_list("bk_biz_id", flat=True).distinct():
        monitor_policy_ids = list(
            MonitorPolicy.objects.filter(bk_biz_id=bk_biz_id).values_list("monitor_policy_id", flat=True).distinct()
        )

        bk_biz_id = bk_biz_id or env.DBA_APP_BK_BIZ_ID
        biz_event_counts = MonitorPolicy.bkm_search_event(
            bk_biz_ids=[bk_biz_id], strategy_id=monitor_policy_ids, days=14
        )
        event_counts.update(biz_event_counts)

    # {strategy_id: { bk_biz_id: count }}
    r = get_redis_connection("default")

    # delete all monitor_events
    for key in r.keys(f"{MONITOR_EVENTS_PREFIX}|*"):
        r.delete(key)

    # update latest monitor_events
    for monitor_policy_id, policy_event_counts in event_counts.items():
        r.hset(f"{MONITOR_EVENTS_PREFIX}|{monitor_policy_id}", mapping=policy_event_counts)
