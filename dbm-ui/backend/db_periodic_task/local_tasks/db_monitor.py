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
from django.utils.crypto import get_random_string
from django.utils.translation import ugettext as _

from backend import env
from backend.components import BKMonitorV3Api
from backend.configuration.constants import DEFAULT_DB_ADMINISTRATORS
from backend.configuration.models import DBAdministrator
from backend.db_monitor.constants import TPLS_ALARM_DIR, TargetLevel, TargetPriority
from backend.db_monitor.models import MonitorPolicy, NoticeGroup
from backend.db_periodic_task.local_tasks import register_periodic_task

# logger = logging.getLogger("celery")
logger = logging.getLogger("root")


@register_periodic_task(run_every=crontab(minute="*/2"))
def update_local_notice_group():
    """同步告警组"""

    now = datetime.datetime.now()
    logger.info("[local_notice_group] start update local group at: %s", now)

    dbas = DBAdministrator.objects.all()
    updated_groups, created_groups = 0, 0

    for dba in dbas:
        # 跳过不需要同步的告警组
        if NoticeGroup.objects.filter(db_type=dba.db_type, is_built_in=True, dba_sync=False).exists():
            continue

        obj, updated = NoticeGroup.objects.update_or_create(
            defaults={"receivers": dba.users}, bk_biz_id=dba.bk_biz_id, db_type=dba.db_type, is_built_in=True
        )

        if updated:
            updated_groups += 1
        else:
            created_groups += 1

    logger.info(
        "[local_notice_group] finish update local group end: %s, create_cnt: %s, update_cnt: %s",
        datetime.datetime.now() - now,
        created_groups,
        updated_groups,
    )


@register_periodic_task(run_every=crontab(minute="*/3"))
def update_remote_notice_group():
    """同步告警组"""

    now = datetime.datetime.now()
    logger.info("[remote_notice_group] start update remote group start: %s", now)

    groups = NoticeGroup.objects.filter(dba_sync=True)

    updated_groups = 0
    for group in groups:
        try:
            logger.info("[remote_notice_group] update remote group: %s " % group.db_type)
            group_users = set(group.receivers + DEFAULT_DB_ADMINISTRATORS)
            group_params = {
                "bk_biz_id": env.DBA_APP_BK_BIZ_ID,
                "notice_receiver": [{"type": "user", "id": user} for user in group_users],
                "name": f"{group.get_db_type_display()}_DBA_{group.bk_biz_id}",
                "notice_way": {"1": ["rtx", "voice"], "2": ["rtx"], "3": ["rtx"]},
                "webhook_url": "",
                "message": _("DBA系统专用"),
                "wxwork_group": {},
            }

            # update or create
            if group.monitor_group_id:
                group_params["id"] = group.monitor_group_id

            res = BKMonitorV3Api.save_notice_group(group_params)
            group.monitor_group_id = res["id"]
            group.save()

            updated_groups += 1
        except Exception as e:  # pylint: disable=wildcard-import
            logger.error("[remote_notice_group] update remote group error: %s (%s)", group.db_type, e)

    logger.info(
        "[remote_notice_group] finish update remote group end: %s, update_cnt: %s",
        datetime.datetime.now() - now,
        updated_groups,
    )


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


@register_periodic_task(run_every=crontab(minute="*/3"))
def sync_plat_monitor_policy():
    """TODO: 同步平台告警策略"""

    now = datetime.datetime.now()
    logger.warning("[sync_plat_monitor_policy] sync bkmonitor alarm start: %s", now)

    # 逐个json导入，本地+远程
    updated_policies = 0
    alarm_tpls = os.path.join(TPLS_ALARM_DIR, "*.json")
    # todo: just for test
    for alarm_tpl in glob.glob(alarm_tpls)[20:40]:
        with open(alarm_tpl, "r") as f:
            template_dict = json.loads(f.read())

            # todo: just for test
            template_dict["name"] = template_dict["name"] + "-" + get_random_string(5)

            # patch template
            template_dict["details"]["labels"] = list(set(template_dict["details"]["labels"]))
            template_dict["details"]["name"] = template_dict["name"]
            template_dict["details"]["priority"] = TargetPriority.PLATFORM.value

            policy = MonitorPolicy(**template_dict)

        # try:
        policy_name = policy.name
        logger.info("[sync_plat_monitor_policy] start sync bkm alarm: %s " % policy_name)
        try:
            policy = MonitorPolicy.objects.get(bk_biz_id=policy.bk_biz_id, db_type=policy.db_type, name=policy_name)

            if policy.is_synced:
                logger.info("[sync_plat_monitor_policy] skip synced bkm alarm: %s " % policy_name)
                continue

            policy.details["id"] = policy.monitor_strategy_id
            logger.info("[sync_plat_monitor_policy] update bkm alarm: %s " % policy.db_type)
        except MonitorPolicy.DoesNotExist:
            # 支持从监控反向同步
            bkm_strategy = get_bkm_strategy(policy_name)
            if bkm_strategy:
                policy.details = bkm_strategy
                logger.info("[sync_plat_monitor_policy] sync and update bkm alarm: %s " % policy.db_type)
            else:
                logger.info("[sync_plat_monitor_policy] create bkm alarm: %s " % policy.db_type)

        # 新建导入补充
        create = False if policy.details.get("id") else True
        if create:
            # fetch targets/test_rules/notify_rules/notify_groups from parent details
            for attr, value in policy.parse_details().items():
                setattr(policy, attr, value)

        policy.save()
        updated_policies += 1

        # except Exception as e:  # pylint: disable=wildcard-import
        #     logger.error("[sync_plat_monitor_policy] sync bkm alarm exception: %s (%s)", policy.db_type, e)

    logger.warning(
        "[sync_plat_monitor_policy] finish sync bkm alarm end: %s, update_cnt: %s",
        datetime.datetime.now() - now,
        updated_policies,
    )
