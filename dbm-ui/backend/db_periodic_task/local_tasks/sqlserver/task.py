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

from backend.db_periodic_task.local_tasks.register import register_periodic_task
from backend.db_periodic_task.local_tasks.sqlserver.backup_file_check import CheckBackupInfo
from backend.db_periodic_task.local_tasks.sqlserver.check_app_setting_data import CheckAppSettingData

logger = logging.getLogger("celery")


@register_periodic_task(run_every=crontab(minute=30, hour=6))
def check_instance_app_setting():
    """
    检查实例的元数据表(app_setting)是否正常
    每条凌晨6点30分执行
    """
    CheckAppSettingData().check_task()


@register_periodic_task(run_every=crontab(minute=00, hour=15))
def check_backup_info():
    """
    检查集群的备份信息的巡检报告
    每条下午15点执行
    """
    CheckBackupInfo().check_task()
