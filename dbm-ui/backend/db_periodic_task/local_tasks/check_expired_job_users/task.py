"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

DBM 临时账号巡检定时任务入口。

设计要点 / 怎么做：
  - 本文件只做一件事：@register_periodic_task 注册 celery beat 触发点；
  - MySQL / SQLServer 巡检的分片 / 错峰 / 双层锁 / worker 全部下沉到各自实现文件；
  - 复用同一个通用分发器（dispatcher.ExpiredJobUserDispatcher），触发点仅一行调用。
"""
import logging

from celery.schedules import crontab

from backend.db_periodic_task.local_tasks.check_expired_job_users.check_expired_job_user_mysql import mysql_dispatcher
from backend.db_periodic_task.local_tasks.check_expired_job_users.check_expired_job_user_sqlserver import (
    sqlserver_dispatcher,
)
from backend.db_periodic_task.local_tasks.register import register_periodic_task

logger = logging.getLogger("celery")


@register_periodic_task(run_every=crontab(minute=00, hour=6))
def check_expired_job_users_for_mysql():
    """MySQL 临时账号巡检 —— dispatcher 入口（每天凌晨 6 点触发）。

    功能说明：
      - 委托 mysql_dispatcher 完成分片、错峰、双层锁、投递；
      - 覆盖 TenDBSingle / TenDBHA / TenDBCluster。

    :return: None
    边界：详见 ExpiredJobUserDispatcher 的 docstring
    """
    mysql_dispatcher.dispatch()


@register_periodic_task(run_every=crontab(minute=00, hour=8))
def check_expired_job_users_for_sqlserver():
    """SQLServer 临时账号巡检 —— dispatcher 入口（每天凌晨 8 点触发）。

    功能说明：
      - 委托 sqlserver_dispatcher 完成分片、错峰、双层锁、投递；
      - 覆盖 SqlserverSingle / SqlserverHA。

    :return: None
    边界：详见 ExpiredJobUserDispatcher 的 docstring
    """
    sqlserver_dispatcher.dispatch()
