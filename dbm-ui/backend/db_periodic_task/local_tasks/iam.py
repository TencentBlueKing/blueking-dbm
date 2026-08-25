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

from celery import shared_task
from celery.schedules import crontab

from backend import env
from backend.configuration.constants import PLAT_BIZ_ID
from backend.configuration.models import DBAdministrator
from backend.db_periodic_task.local_tasks.context_manager import start_new_span
from backend.db_periodic_task.local_tasks.register import register_periodic_task
from backend.db_periodic_task.utils import TimeUnit, calculate_countdown
from backend.iam_app.dataclass import flush_groups_auth
from backend.iam_app.tasks import sync_dba_role

logger = logging.getLogger("root")


@shared_task
def async_flush_groups_auth():
    flush_groups_auth()


@register_periodic_task(run_every=crontab(day_of_week="1", hour="12", minute="0"))
def auto_flush_groups_auth_task():
    """定时每周一中午12点刷新用户组权限"""
    flush_groups_auth()
    logger.info("flush groups auth task finished")


# TODO: 刷新dba权限任务暂不注册
# @register_periodic_task(run_every=crontab(day_of_week="1", hour="4", minute="0"))
def renew_dba_role_auth_task():
    """
    定时每周一凌晨4点续期DBA的IAM角色授权。
    V4的授权最长365天，需周期性重新授权续期，同时兜底修复DBA变更时同步失败的记录
    """
    if not env.ENABLE_IAM_V4:
        logger.info("renew dba role auth task skipped, iam v4 disabled")
        return

    # 平台DBA在各业务下同样承担该组件的运维职责，续期时与业务DBA一并授权
    plat_dba_users = {dba.db_type: dba.users for dba in DBAdministrator.objects.filter(bk_biz_id=PLAT_BIZ_ID)}
    renew_targets = []
    for dba in DBAdministrator.objects.exclude(bk_biz_id=PLAT_BIZ_ID):
        users = sorted(set(dba.users) | set(plat_dba_users.get(dba.db_type, [])))
        if users:
            renew_targets.append((dba.bk_biz_id, dba.db_type, users))

    for index, (bk_biz_id, db_type, users) in enumerate(renew_targets):
        # 平摊到1小时内执行，避免大量授权请求集中打到IAM
        countdown = calculate_countdown(count=len(renew_targets), index=index, duration=TimeUnit.HOUR)
        with start_new_span(sync_dba_role):
            # old_users 传空表示只授权不撤销，人员增减由 DBA 变更时的同步负责
            sync_dba_role.apply_async(
                kwargs={"bk_biz_id": bk_biz_id, "db_type": db_type, "new_users": users, "old_users": []},
                countdown=countdown,
            )

    logger.info("renew dba role auth task finished, dispatched %s tasks", len(renew_targets))
