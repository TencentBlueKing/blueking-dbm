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

from backend.db_periodic_task.local_tasks import register_periodic_task
from backend.db_periodic_task.local_tasks.mysql_checksum.check_checksum import check_mysql_checksum

logger = logging.getLogger("celery")


@register_periodic_task(run_every=crontab(day_of_week="0,3,4,5,6", hour="3", minute="53"))
def check_checksum_task():
    """
    巡检前天的校验结果，存入db_report数据库。周六、周日数据库不校验数据。
    """
    logger.info("start mysql checksum check")
    check_mysql_checksum()
