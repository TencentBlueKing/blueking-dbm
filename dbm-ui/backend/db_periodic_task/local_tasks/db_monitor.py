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
import itertools
import json
import logging
from datetime import datetime, timedelta

from blueapps.core.celery.celery import app
from celery import shared_task
from celery.schedules import crontab
from django.core.cache import cache
from django.utils import timezone
from django.utils.translation import gettext as _

from backend import env
from backend.components import BKMonitorV3Api
from backend.configuration.constants import PLAT_BIZ_ID, DBType, SystemSettingsEnum
from backend.configuration.models import DBAdministrator, SystemSettings
from backend.core.notify.constants import MsgType
from backend.core.notify.handlers import BkChatHandler, CmsiHandler
from backend.db_meta.models import Cluster
from backend.db_monitor.constants import MONITOR_EVENTS
from backend.db_monitor.exceptions import DutyNoticeScheduleException
from backend.db_monitor.models import CollectInstance, DispatchGroup, DutyRule, MonitorPolicy, NoticeGroup
from backend.db_monitor.tasks import update_app_policy, update_dba_notice_group
from backend.db_periodic_task.constants import GET_AND_DELETE_SET_LUA
from backend.db_periodic_task.local_tasks.context_manager import start_new_span
from backend.db_periodic_task.local_tasks.register import register_periodic_task
from backend.db_periodic_task.utils import TimeUnit, calculate_countdown
from backend.exceptions import ApiResultError
from backend.flow.utils.cc_manage import operate_collector, parser_operate_collector_cache_key
from backend.utils.redis import RedisConn

logger = logging.getLogger("celery")


@register_periodic_task(run_every=crontab(hour="0", minute="0"))
def update_local_notice_group():
    """同步告警组"""
    dba_ids = DBAdministrator.objects.values_list("id", flat=True)
    count = len(dba_ids)
    # 同步 DBA 内置告警组
    for index, dba_id in enumerate(dba_ids):
        countdown = calculate_countdown(count=count, index=index, duration=8 * TimeUnit.HOUR)
        logger.info("dba_id({}) update notice group will be run after {} seconds.".format(dba_id, countdown))
        with start_new_span(update_dba_notice_group):
            update_dba_notice_group.apply_async(kwargs={"dba_id": dba_id}, countdown=countdown)

    # 同步非内置的，包含 CC 角色的告警组
    groups = NoticeGroup.objects.filter(receivers__contains=[{"type": "group"}], is_built_in=False)
    for group in groups:
        group.save_monitor_group()


@register_periodic_task(run_every=crontab(minute="*/5"))
def sync_plat_monitor_policy(action_id=None, db_type=None, force=False):
    """同步平台告警策略"""
    MonitorPolicy.sync_plat_monitor_policy(action_id=action_id, db_type=db_type, force=force)


@register_periodic_task(run_every=crontab(minute=0, hour="*/2"))
def sync_plat_dispatch_policy():
    """同步平台分派通知策略
    按照app_id->db_type来拆分策略：
        bk_biz_id=0: db_type=redis and policy=1,2,3 -> notify_group: 1
        bk_biz_id>0: db_type=redis and policy=1,2,3 and appid=6 -> notify_group: 2
    """

    logger.info("sync_plat_dispatch_policy started")
    biz_ids = NoticeGroup.objects.exclude(monitor_group_id=0).values_list("bk_biz_id", flat=True).distinct()
    count = len(biz_ids)
    # 同步平台/业务分派策略
    for index, bk_biz_id in enumerate(biz_ids):
        countdown = calculate_countdown(count=count, index=index, duration=2 * TimeUnit.HOUR)
        logger.info("biz({}) sync dispatch policy will be run after {} seconds.".format(bk_biz_id, countdown))
        with start_new_span(sync_biz_dispatch_policy):
            sync_biz_dispatch_policy.apply_async(kwargs={"bk_biz_id": bk_biz_id}, countdown=countdown)


@app.task
def sync_biz_dispatch_policy(bk_biz_id):
    latest_rules = DispatchGroup.get_rules(bk_biz_id)
    try:
        dispatch_group = DispatchGroup.objects.get(bk_biz_id=bk_biz_id)
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

            try:
                logger.info("sync_custom_monitor_policy: %s, %s, %s", bk_biz_id, expected_group, db_type)
                update_app_policy(bk_biz_id, expected_group, db_type)
            except Exception as e:
                logger.error("sync_custom_monitor_policy error: %s", e)


# TODO: 暂时去掉，cache没生效，频繁刷新
# @register_periodic_task(run_every=crontab(minute="*/5"))
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


@register_periodic_task(run_every=crontab(minute="*/1"))
def cycle_trigger_operator_collector():
    script = RedisConn.register_script(GET_AND_DELETE_SET_LUA)
    # 获取当前的任务列表并清空
    task_list = script(keys=["operate_collector"])
    for cache_key in task_list:
        # 获取采集下发相关信息
        bk_biz_id, db_type, machine_type, action = parser_operate_collector_cache_key(cache_key)
        # 获取当前任务缓存的实例ID，下发采集任务
        instance_id_to_host_id = script(keys=[cache_key])
        operate_collector(bk_biz_id, db_type, machine_type, instance_id_to_host_id, action)


@shared_task
def send_duty_schedule(db_type):
    """发送轮值排班表"""

    def __format_arrange_str(rule, arranges):
        # 格式化排版表文本
        date_space = " " * 10  # 2000-01-01
        work_time_space = " " * (max([len(d["work_times"]) for d in arranges]) * 12)  # 00:00--23:59
        content = _("日期{}时段{}轮值人员").format(date_space, work_time_space)
        for arrange in arranges:
            arrange_str = f"{arrange['date']}  {','.join(arrange['work_times'])}  {','.join(arrange['members'])}"
            content += f"\n{arrange_str}"

        # 格式化标题
        now_date = f"{now.month}.{now.day}"
        after_now = now + timedelta(days=notice_after)
        after_date = f"{after_now.month}.{after_now.day}"
        title = _("[{} {}] {}-{} 轮值排班表").format(DBType.get_choice_label(db_type), rule.name, now_date, after_date)

        return title, content

    # 获取对应组件的轮值通知设置
    notice_cfg = SystemSettings.get_setting_value(SystemSettingsEnum.BKM_DUTY_NOTICE.value, default={}).get(db_type)
    if not notice_cfg:
        raise DutyNoticeScheduleException(_("轮值通知配置[{}]不存在").format(db_type))

    # 轮值通知天数包含今天，所以-1
    notice_after = notice_cfg["after"] - 1
    now = datetime.now(timezone.utc)

    # 获取有效的轮值规则
    duty_rules = DutyRule.objects.filter(db_type=db_type, is_enabled=True)
    for rule in duty_rules:
        # 获取排班表和接收人
        arranges = rule.get_date_schedule(date=now, after=notice_after)
        members = list(set(itertools.chain(*[a["members"] for a in arranges])))
        if not arranges:
            continue

        # 获取通知内容
        title, arrange_content = __format_arrange_str(rule, arranges)
        # 根据通知渠道进行通知
        msg_types = [msg_type for msg_type in notice_cfg["channels"] if notice_cfg["channels"][msg_type]]
        for msg_type in msg_types:
            receivers = members
            # 企业微信机器人通知，通知人群ID，加上@所有人
            if msg_type == MsgType.WECOM_ROBOT:
                receivers = [notice_cfg["channels"][msg_type]]
                arrange_content += _("\n<@所有人>")

            try:
                if msg_type in BkChatHandler.get_msg_type() and env.BKCHAT_APIGW_DOMAIN:
                    BkChatHandler(title, arrange_content, receivers).send_custom_msg()
                else:
                    CmsiHandler(title, arrange_content, receivers).send_msg(msg_type, context=None)
            except (ApiResultError, Exception) as e:
                logger.error("[%s]send_duty_schedule error: %s", msg_type, e)


@register_periodic_task(run_every=crontab(hour="0", minute="0"))
def sync_monitor_subscribe():
    """同步监控订阅"""

    # 拉取全量的告警订阅策略
    subscribe_list = BKMonitorV3Api.list_full_subscribe(bk_biz_id=env.DBA_APP_BK_BIZ_ID)
    metric_config = SystemSettings.get_setting_value(key=SystemSettingsEnum.BKM_SUBSCRIBE_METRIC, default={})

    # 获取用户订阅过的所有集群
    cluster_subscribe_map = {}
    for sub in subscribe_list:
        conditions_map = {c["field"]: c["value"] for c in sub["conditions"]}
        cluster_subscribe_map[conditions_map["tags.cluster_domain"][0]] = sub

    clusters = Cluster.objects.filter(immute_domain__in=list(set(cluster_subscribe_map.keys())))
    cluster_map = {c.immute_domain: c for c in clusters}

    # 获取所有需要删除和更新的订阅
    delete_subscribe_list = []
    update_subscribe_list = []
    for domain, sub in cluster_subscribe_map.items():
        if domain not in cluster_map:
            delete_subscribe_list.append(sub["id"])
            continue

        cluster = cluster_map[domain]
        metric_list = [m["id"] for m in metric_config.get(cluster.cluster_type, [])]
        metric_list = list(itertools.chain(*[x if isinstance(x, list) else [x] for x in metric_list]))

        for condition in sub["conditions"]:
            if condition["field"] != "alert.metric":
                continue
            if set(condition["value"]) == set(metric_list):
                continue
            condition["value"] = metric_list
            sub["sub_username"] = sub["username"]
            update_subscribe_list.append(sub)

    # 分批删除/更新订阅
    if delete_subscribe_list:
        BKMonitorV3Api.bulk_delete_subscribe({"bk_biz_id": env.DBA_APP_BK_BIZ_ID, "ids": delete_subscribe_list})

    if update_subscribe_list:
        BKMonitorV3Api.bulk_save_subscribe_in_batch(env.DBA_APP_BK_BIZ_ID, update_subscribe_list)
