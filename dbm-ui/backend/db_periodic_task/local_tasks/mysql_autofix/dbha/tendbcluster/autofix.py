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
from typing import Dict, List

from backend.db_meta.enums import MachineType
from backend.db_monitor.models import MySQLDBHAEvent
from backend.db_periodic_task.local_tasks.mysql_autofix.dbha.tendbcluster.remote_autofix import replace_remote
from backend.db_periodic_task.local_tasks.mysql_autofix.dbha.tendbcluster.spider_autofix import replace_spider

logger = logging.getLogger("celery.mysql_dbha_autofix")


def autofix(cluster_ids: List[int], events_by_machine_type: Dict[str, List[MySQLDBHAEvent]]):
    logger.info(
        "[tendbcluster.autofix] cluster_ids=%s, machine_types=%s", cluster_ids, list(events_by_machine_type.keys())
    )

    if MachineType.SPIDER in events_by_machine_type:
        logger.info("[tendbcluster.autofix] dispatching replace_spider, cluster_ids=%s", cluster_ids)
        replace_spider(
            cluster_ids=cluster_ids,
            machine_type=MachineType.SPIDER,
            events=events_by_machine_type[str(MachineType.SPIDER.value)],
        )

    if MachineType.REMOTE in events_by_machine_type:
        logger.info("[tendbcluster.autofix] dispatching replace_remote, cluster_ids=%s", cluster_ids)
        replace_remote(
            cluster_ids=cluster_ids,
            machine_type=MachineType.REMOTE,
            events=events_by_machine_type[str(MachineType.REMOTE.value)],
        )
