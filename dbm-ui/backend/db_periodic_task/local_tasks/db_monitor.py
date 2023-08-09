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
import logging

from celery.schedules import crontab
from celery.task import periodic_task
from django.utils.translation import ugettext as _

from backend import env
from backend.components import BKMonitorV3Api
from backend.configuration.constants import DEFAULT_DB_ADMINISTRATORS
from backend.configuration.models import DBAdministrator
from backend.db_monitor.models import NoticeGroup
from backend.db_periodic_task.local_tasks import register_periodic_task

logger = logging.getLogger("celery")


@register_periodic_task(run_every=crontab(minute="*/2"))
def update_local_notice_group():
    """同步告警组"""

    now = datetime.datetime.now()
    logger.info("[local_notice_group] start update local group at: %s", now)

    platform_dbas = DBAdministrator.objects.filter(bk_biz_id=0)
    updated_groups, created_groups = 0, 0

    for dba in platform_dbas:
        # 跳过不需要同步的告警组
        if NoticeGroup.objects.filter(db_type=dba.db_type, dba_sync=False).exists():
            continue

        obj, updated = NoticeGroup.objects.update_or_create(
            defaults={"users": dba.users}, bk_biz_id=0, db_type=dba.db_type
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
            group_users = set(group.users + DEFAULT_DB_ADMINISTRATORS)
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
