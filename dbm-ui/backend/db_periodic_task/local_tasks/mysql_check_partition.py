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
import datetime
import logging

from celery.schedules import crontab
from django.utils.translation import ugettext as _

from backend import env
from backend.components import CmsiApi
from backend.components.cmsi.handler import CmsiHandler
from backend.components.mysql_partition.client import DBPartitionApi
from backend.configuration.constants import DBType
from backend.configuration.models import DBAdministrator
from backend.db_periodic_task.local_tasks import register_periodic_task

logger = logging.getLogger("root")


@register_periodic_task(run_every=crontab(day_of_week="*", hour="14", minute="30"))
def mysql_check_partition():
    """
    mysql巡检分区执行日志
    """
    try:
        para = {"days": 1}
        logs = DBPartitionApi.check_log(para)
    except Exception as e:  # pylint: disable=broad-except
        logger.error(_("分区服务check_log接口异常: {}").format(e))
        return
    msg = {}
    content = ""
    content = _format_msg(logs["mysql_not_run"], DBType.MySQL, _("未执行"), content)
    content = _format_msg(logs["mysql_fail"], DBType.MySQL, _("失败"), content)
    content = _format_msg(logs["spider_not_run"], DBType.TenDBCluster, _("未执行"), content)
    content = _format_msg(logs["spider_fail"], DBType.TenDBCluster, _("失败"), content)
    content = content.rstrip("\n")
    if env.MYSQL_CHATID == "":
        logger.error(_("环境变量MYSQL_CHATID未设置"))
        return
    if env.WECOM_ROBOT == "":
        logger.error(_("环境变量WECOM_ROBOT未设置"))
        return
    chat_ids = env.MYSQL_CHATID.split(",")
    if content:
        msg.update(
            {
                "receiver__username": "admin",
                "group_receiver": chat_ids,
                "content": _("【DBM】分区表异常情况 {} \n业务名称 bk_biz_id DB类型 失败/未执行 数量 DBA 策略ID\n{}").format(
                    datetime.date.today(), content
                ),
                "msg_type": [CmsiApi.MsgType.WECOM_ROBOT.value],
                "sender": env.WECOM_ROBOT,
            }
        )
        CmsiHandler.send_msg(msg)
    return


def _format_msg(logs: list, db_type: str, fail_type: str, content: str):
    """
    生成指定格式的信息
    """
    if logs:
        for biz_msg in logs:
            dbas = DBAdministrator().get_biz_db_type_admins(biz_msg["bk_biz_id"], DBType.MySQL)
            dba = "None"
            if dbas:
                dba = dbas[0]
            content = _(
                "{}{}   {}   {}   {}   {}   <@{}>   {}\n".format(
                    content,
                    biz_msg["db_app_abbr"],
                    biz_msg["bk_biz_id"],
                    db_type,
                    fail_type,
                    biz_msg["cnt"],
                    dba,
                    biz_msg["ids"],
                )
            )
    return content
