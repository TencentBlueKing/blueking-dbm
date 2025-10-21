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
import time
from collections import defaultdict

import pytz
from django.utils import timezone
from django.utils.translation import gettext as _

from backend.components.bkmonitorv3.client import BKMonitorV3EventApi
from backend.configuration.constants import SystemSettingsEnum
from backend.configuration.models import SystemSettings
from backend.core.notify.constants import MsgType
from backend.core.notify.handlers import BkChatHandler
from backend.db_monitor.constants import MonitorEventType
from backend.db_monitor.dataclass import BaseEventBody, MonitorEvent
from backend.db_monitor.exceptions import DutyNoticeScheduleException
from backend.db_report.enums import MysqlBackupCheckSubType, ReportStateType
from backend.db_report.models import MysqlBackupCheckReport, MysqlBackupProgress
from backend.exceptions import ApiResultError

logger = logging.getLogger("celery")


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

    failed_cluster = defaultdict(set)
    for backup in failed_backups:
        dim = {
            "appid": backup.bk_biz_id,
            "cluster_domain": backup.cluster_domain,
            "instance_host": backup.backup_host,
            "instance_port": backup.backup_port,
            "instance_role": backup.mysql_role,
            "is_full_backup": backup.is_full_backup,
        }
        k = "app={}, cluster={}".format(dim["appid"], dim["cluster_domain"])
        failed_cluster[k].add(backup.backup_host)
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

    db_type = "mysql"
    msg_type = MsgType.WECOM_ROBOT
    notice_cfg = SystemSettings.get_setting_value(SystemSettingsEnum.BKM_DUTY_NOTICE.value, default={}).get(db_type)
    if not notice_cfg:
        raise DutyNoticeScheduleException(_("巡检通知配置[{}]不存在").format(db_type))
    title = _("MySQL 备份失败")
    msg_content = ""
    batch_size = 30
    cnt = 0
    for k, v in failed_cluster.items():
        msg_content += "{}: {}\n".format(k, v)
        cnt += 1
        if cnt >= batch_size:
            if notice_cfg["enabled"]:
                receivers = [notice_cfg["channels"][msg_type]]
                msg_content += _("\n<@所有人>")
                try:
                    BkChatHandler(title, msg_content, receivers).send_custom_msg()
                except (ApiResultError, Exception) as e:
                    logger.error("[%s]send_inspect_result error: %s", msg_type, e)
            msg_content = ""
            cnt = 0
    if cnt > 0:
        if notice_cfg["enabled"]:
            receivers = [notice_cfg["channels"][msg_type]]
            msg_content += _("\n<@所有人>")
            try:
                BkChatHandler(title, msg_content, receivers).send_custom_msg()
            except (ApiResultError, Exception) as e:
                logger.error("[%s]send_inspect_result error: %s", msg_type, e)

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
