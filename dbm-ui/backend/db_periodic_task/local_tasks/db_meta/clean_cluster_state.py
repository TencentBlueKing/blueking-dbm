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

from celery.schedules import crontab

from backend.db_meta.api.cluster_state import ClusterStateService
from backend.db_periodic_task.local_tasks import register_periodic_task

logger = logging.getLogger("celery")


@register_periodic_task(run_every=crontab(hour=3, minute=30))
def clean_orphan_cluster_state():
    """
    兜底清理集群已不存在的状态行，正常情况下集群下架时已显式删除
    """
    cleaned = ClusterStateService.clear_orphans()
    logger.info("clean_orphan_cluster_state finished, cleaned %s clusters", cleaned)
