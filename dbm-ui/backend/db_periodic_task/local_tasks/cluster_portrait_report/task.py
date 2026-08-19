# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

集群画像报告生成 —— 定时任务入口。

设计要点 / 怎么做：
  - 本文件只做一件事：@register_periodic_task 注册 celery beat 触发点（每天凌晨 0 点）；
  - 分片 / 错峰 / 双层锁 / worker 全部下沉到各自实现文件；
  - 复用 ClusterPortraitDispatcher，触发点仅一行调用。
"""
import logging

from celery.schedules import crontab

from backend import env
from backend.db_periodic_task.local_tasks.cluster_portrait_report.portrait_report_mysql import portrait_dispatcher
from backend.db_periodic_task.local_tasks.register import register_periodic_task

logger = logging.getLogger("celery")


@register_periodic_task(run_every=crontab(minute=0, hour=0))
def generate_cluster_portrait_report():
    """集群画像报告生成 —— dispatcher 入口（每天凌晨 0 点触发）。

    功能说明：
      - 委托 portrait_dispatcher 完成灰度选取、错峰、防重锁、投递；
      - 覆盖 TenDBSingle / TenDBHA / TenDBCluster。

    :return: None
    """
    if not env.ENABLE_DBM_AI:
        logger.warning("ai not enabled")
        return

    portrait_dispatcher.dispatch()
