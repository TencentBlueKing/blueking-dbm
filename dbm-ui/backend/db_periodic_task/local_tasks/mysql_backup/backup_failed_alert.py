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
import time

import pytz
from django.utils import timezone

from backend.components.bkmonitorv3.client import BKMonitorV3EventApi
from backend.db_monitor.constants import MonitorEventType
from backend.db_monitor.dataclass import BaseEventBody, MonitorEvent
from backend.db_report.enums import MysqlBackupCheckSubType, ReportStateType
from backend.db_report.models import MysqlBackupCheckReport, MysqlBackupProgress


def mysql_backup_failed_alert():
    """mysql backup failed alert"""
    # 获取当天的凌晨时间戳
    # 这里等全网发布新版本后，都是用 utc，可去掉时区
    time_now = timezone.now().astimezone(pytz.timezone("Asia/Shanghai"))
    today_time_zero = time_now.replace(hour=0, minute=0, second=0, microsecond=0)

    today_time_zero_ms = int(today_time_zero.timestamp() * 1000 * 1000)
    failed_backups = MysqlBackupProgress.objects.filter(
        status="Failed", event_create_timestamp__gte=today_time_zero_ms
    ).order_by("bk_biz_id", "cluster_domain")

    for backup in failed_backups:
        dim = {
            "appid": backup.bk_biz_id,
            "cluster_domain": backup.cluster_domain,
            "instance_host": backup.backup_host,
            "instance_port": backup.backup_port,
            "instance_role": backup.mysql_role,
            "is_full_backup": backup.is_full_backup,
        }
        content = "{}\nevent_create_time_utc{}".format(
            backup.status_detail, int(backup.event_create_timestamp / 1000 / 1000)
        )
        event = MonitorEvent(
            event_name=MonitorEventType.MYSQL_BACKUP_FAILED,
            target=backup.backup_host,
            event=BaseEventBody(content=content),
            dimension=dim,
            timestamp=0,
        )
        time.sleep(0.01)  # 避免请求过快
        BKMonitorV3EventApi.send_event([event])

    # if failed_days >=2: call dba
    backup_inspect_failed = MysqlBackupCheckReport.objects.filter(
        state=ReportStateType.ABNORMAL.value,
        subtype=MysqlBackupCheckSubType.FullBackup.value,
        failed_days__gte=2,
        create_at__gte=today_time_zero,
    )
    for backup in backup_inspect_failed:
        dim = {"appid": backup.bk_biz_id, "cluster_domain": backup.cluster}

        event = MonitorEvent(
            event_name=MonitorEventType.MYSQL_BACKUP_INSPECT_FAILED,
            target=backup.cluster,
            event=BaseEventBody(content="failed days {}".format(backup.failed_days)),
            dimension=dim,
            timestamp=0,
        )
        time.sleep(0.01)  # 避免请求过快
        BKMonitorV3EventApi.send_event([event])
