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
import json
import logging
import os

from blueapps.core.celery.celery import app
from celery.schedules import crontab
from django.core.cache import cache

from backend import env
from backend.configuration.constants import DEFAULT_DB_ADMINISTRATORS, PLAT_BIZ_ID, SystemSettingsEnum
from backend.configuration.models import DBAdministrator, SystemSettings
from backend.db_monitor.constants import DEFAULT_ALERT_NOTICE, MONITOR_EVENTS, TPLS_ALARM_DIR, TargetPriority
from backend.db_monitor.exceptions import BkMonitorSaveAlarmException
from backend.db_monitor.models import CollectInstance, DispatchGroup, MonitorPolicy, NoticeGroup
from backend.db_monitor.tasks import update_app_policy
from backend.db_periodic_task.local_tasks.register import register_periodic_task
from backend.db_periodic_task.utils import TimeUnit, calculate_countdown

logger = logging.getLogger("celery")


@register_periodic_task(run_every=crontab(minute="*/5"))
def update_local_notice_group():
    """同步告警组"""
    dba_ids = DBAdministrator.objects.values_list("id", flat=True)
    count = len(dba_ids)
    for index, dba_id in enumerate(dba_ids):
        countdown = calculate_countdown(count=count, index=index, duration=5 * TimeUnit.MINUTE)
        logger.info("dba_id({}) update notice group will be run after {} seconds.".format(dba_id, countdown))
        update_dba_notice_group.apply_async(kwargs={"dba_id": dba_id}, countdown=countdown)


@app.task
def update_dba_notice_group(dba_id: int):
    dba = DBAdministrator.objects.get(id=dba_id)
    receiver_users = dba.users or DEFAULT_DB_ADMINISTRATORS
    try:
        group_name = f"{dba.get_db_type_display()}_DBA"
        group_receivers = [{"id": user, "type": "user"} for user in receiver_users]
        logger.info("[local_notice_group] update_or_create notice group: %s", group_name)
        try:
            group = NoticeGroup.objects.get(bk_biz_id=dba.bk_biz_id, db_type=dba.db_type, is_built_in=True)
        except NoticeGroup.DoesNotExist:
            NoticeGroup.objects.create(
                name=group_name,
                receivers=group_receivers,
                details={"alert_notice": DEFAULT_ALERT_NOTICE},
                bk_biz_id=dba.bk_biz_id,
                db_type=dba.db_type,
                is_built_in=True,
            )
        else:
            group.name = group_name
            group.receivers = group_receivers
            if not group.details:
                group.details = {"alert_notice": DEFAULT_ALERT_NOTICE}
            group.save(update_fields=["name", "receivers", "details"])
    except Exception as e:
        logger.error("[local_notice_group] update_or_create notice group error: %s", e)


@register_periodic_task(run_every=crontab(minute="*/5"))
def sync_plat_monitor_policy():
    """同步平台告警策略"""
    skip_dir = "v1"
    now = datetime.datetime.now()
    logger.warning("[sync_plat_monitor_policy] sync bkm alarm policy start: %s", now)

    # 逐个json导入，本地+远程
    updated_policies = 0
    for root, dirs, files in os.walk(TPLS_ALARM_DIR):
        if skip_dir in dirs:
            dirs.remove(skip_dir)

        for alarm_tpl in files:
            with open(os.path.join(root, alarm_tpl), "r") as f:
                try:
                    template_dict = json.loads(f.read())
                    policy_name = template_dict["name"]
                    # db_type = template_dict["db_type"]
                except json.decoder.JSONDecodeError:
                    logger.error("[sync_plat_monitor_policy] load template failed: %s", alarm_tpl)
                    continue

                deleted = template_dict.pop("deleted", False)

                # just for test
                # policy_name = policy_name + "-" + get_random_string(5)

                # patch template
                template_dict["details"]["labels"] = list(set(template_dict["details"]["labels"]))
                template_dict["details"]["name"] = policy_name
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

                if deleted:
                    # print("[sync_plat_monitor_policy] delete old alarm: %s " % policy_name)
                    logger.info("[sync_plat_monitor_policy] delete old alarm: %s " % policy_name)
                    synced_policy.delete()
                    continue

                if synced_policy.version >= policy.version:
                    # print("[sync_plat_monitor_policy] skip same version alarm: %s " % policy_name)
                    logger.info("[sync_plat_monitor_policy] skip same version alarm: %s " % policy_name)
                    continue

                for keeped_field in MonitorPolicy.KEEPED_FIELDS:
                    setattr(policy, keeped_field, getattr(synced_policy, keeped_field))

                policy.details["id"] = synced_policy.monitor_policy_id
                # print("[sync_plat_monitor_policy] update bkm alarm policy: %s " % policy_name)
                logger.info("[sync_plat_monitor_policy] update bkm alarm policy: %s " % policy_name)
            except MonitorPolicy.DoesNotExist:
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
        bk_biz_id>0: db_type=redis and policy=1,2,3 and appid=6 -> notify_group: 2
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

    logger.info("sync_monitor_policy_events -> policy_event_counts = %s", event_counts)
    cache.set(MONITOR_EVENTS, json.dumps(event_counts))


# todo: 暂时去掉，cache没生效，频繁刷新
# @register_periodic_task(run_every=crontab(minute="*/5"))
def sync_monitor_collect_strategy():
    """
    同步监控采集项
    新增一个周期任务来做周期刷新，处理非DBM业务中的采集项
    """

    key = "unmanaged_biz"
    logger.info("sync_monitor_collect_strategy started")
    unmanaged_biz = set(
        SystemSettings.get_setting_value(SystemSettingsEnum.INDEPENDENT_HOSTING_BIZS.value, default=[])
    )
    cached_unmanaged_biz = set(cache.get(key, []))
    logger.info(
        "sync_monitor_collect_strategy: unmanaged_biz = %s, cached_unmanaged_biz = %s",
        unmanaged_biz,
        cached_unmanaged_biz,
    )
    if cached_unmanaged_biz == unmanaged_biz:
        logger.info("sync_monitor_collect_strategy skipped for: %s", unmanaged_biz)
        return

    logger.info("sync_monitor_collect_strategy update for: %s", unmanaged_biz)
    CollectInstance.sync_collect_strategy()
    cache.set(key, list(unmanaged_biz))
