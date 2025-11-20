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

from celery.schedules import crontab

from backend.db_periodic_task.local_tasks import register_periodic_task
from backend.db_periodic_task.local_tasks.es_daily_check.es_cluster_status import check_es_status
from backend.db_periodic_task.local_tasks.es_daily_check.es_datanode_check import check_es_datanode
from backend.db_periodic_task.local_tasks.es_daily_check.es_domain_check import check_es_domain
from backend.db_periodic_task.local_tasks.es_daily_check.es_master_check import check_es_master
from backend.db_periodic_task.local_tasks.es_daily_check.es_version_check import check_es_version


@register_periodic_task(run_every=crontab(hour="8", minute="08"))
def es_status_task():
    """
    es集群状态
    """
    check_es_status()


@register_periodic_task(run_every=crontab(hour="8", minute="18"))
def es_master_task():
    """
    es master节点巡检
    """
    check_es_master()


@register_periodic_task(run_every=crontab(hour="8", minute="28"))
def es_version_task():
    """
    es版本巡检
    """
    check_es_version()


@register_periodic_task(run_every=crontab(hour="8", minute="38"))
def es_datanode_task():
    """
    es数据节点巡检
    """
    check_es_datanode()


@register_periodic_task(run_every=crontab(hour="8", minute="48"))
def es_domain_task():
    """
    es域名巡检
    """
    check_es_domain()
