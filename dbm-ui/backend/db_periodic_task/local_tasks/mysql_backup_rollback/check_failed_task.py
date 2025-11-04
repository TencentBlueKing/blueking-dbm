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
from collections import defaultdict
from typing import List

from django.utils.translation import gettext as _

from backend import env
from backend.configuration.constants import DBType
from backend.configuration.models import DBAdministrator
from backend.core.notify.handlers import CmsiHandler
from backend.db_periodic_task.models import MySQLBackupRecoverTask, TaskStatus
from backend.env import MYSQL_BACKUPRECOVER_BIZ_ID

logger = logging.getLogger("root")


def get_time_range():
    """
    获取查询时间范围：前天10:30到今天10:30
    """
    today = datetime.datetime.now()
    # 今天的10:30
    end_time = today.replace(hour=10, minute=30, second=0, microsecond=0)
    # 前天的10:30
    start_time = end_time - datetime.timedelta(days=2)

    return start_time, end_time


def truncate_text(text: str, max_length: int = 100) -> str:
    """
    截断文本，避免过长

    @param text: 原始文本
    @param max_length: 最大长度
    @return: 截断后的文本
    """
    if not text:
        return ""
    if len(text) <= max_length:
        return text
    return text[:max_length] + "..."


def build_task_url(task_id: str) -> str:
    """
    构建任务详情URL

    @param task_id: 任务ID
    @return: 任务详情URL
    """
    # 去掉 BK_SAAS_HOST 末尾的斜杠（如果有）
    saas_host = env.BK_SAAS_HOST.rstrip("/")
    url = f"{saas_host}/{MYSQL_BACKUPRECOVER_BIZ_ID}/task-history/detail/{task_id}?from=taskHistoryList"
    return url


def format_failed_tasks_message(failed_tasks_by_biz: dict) -> str:
    """
    格式化失败任务消息

    @param failed_tasks_by_biz: 按业务分组的失败任务
    @return: 格式化后的消息内容
    """
    content = ""

    for bk_biz_id, tasks in failed_tasks_by_biz.items():
        # 获取DBA
        dbas = DBAdministrator().get_biz_db_type_admins(bk_biz_id, DBType.MySQL)
        dba = dbas[0] if dbas else "None"

        # 为每个失败的任务生成一条记录
        for task in tasks:
            cluster_domain = task.cluster_domain or "N/A"
            task_id = task.task_id

            # 构建任务链接
            task_url = build_task_url(task_id)
            task_link = f"[{_('任务详情')}]({task_url})"

            # 格式化消息行
            content += _("{}   {}   {}   <@{}>\n").format(bk_biz_id, cluster_domain, task_link, dba)

    return content


def cut_content(content: str) -> List[str]:
    """
    将content按照不超过1024字符进行分割，防止内容超限

    @param content: 原始内容
    @return: 分割后的内容列表
    """
    split_contents = content.split("\n")
    max_len = 1024

    contents = []
    current_content = ""
    for index, msg in enumerate(split_contents):
        if msg:
            current_content += msg + "\n"
        if len(current_content) > max_len or index == len(split_contents) - 1:
            contents.append(current_content)
            current_content = ""

    return contents


def check_mysql_backup_exercise_failed():
    """
    检查MySQL备份演练失败任务并推送通知
    """
    # 检查环境变量
    if not env.MYSQL_CHATID:
        logger.error(_("环境变量MYSQL_CHATID未设置"))
        return
    if not env.WECOM_ROBOT:
        logger.error(_("环境变量WECOM_ROBOT未设置"))
        return

    # 获取时间范围
    start_time, end_time = get_time_range()
    logger.info(_("查询演练失败任务，时间范围: {} 至 {}").format(start_time, end_time))

    # 查询失败的任务
    try:
        failed_tasks = MySQLBackupRecoverTask.objects.filter(
            task_status=TaskStatus.RECOVER_FAILED, create_at__range=(start_time, end_time)
        ).order_by("bk_biz_id", "create_at")
    except Exception as e:
        logger.error(_("查询演练失败任务异常: {}").format(e))
        return

    if not failed_tasks.exists():
        logger.info(_("没有发现演练失败的任务"))
        return

    # 按业务ID分组
    failed_tasks_by_biz = defaultdict(list)
    for task in failed_tasks:
        failed_tasks_by_biz[task.bk_biz_id].append(task)

    logger.info(_("发现 {} 个业务共 {} 个演练失败任务").format(len(failed_tasks_by_biz), failed_tasks.count()))

    # 格式化消息内容
    content = format_failed_tasks_message(failed_tasks_by_biz)
    content = content.rstrip("\n")

    if not content:
        logger.info(_("没有需要推送的内容"))
        return

    # 分割消息（如果太长）
    chat_ids = env.MYSQL_CHATID.split(",")
    cut_msgs = cut_content(content)

    # 推送消息
    for msg in cut_msgs:
        title = _("【DBM】MySQL备份演练失败情况")
        # 添加处理说明
        handle_instruction = _(
            "\n\n**处理说明**：\n" "- 任务因演练失败已被忽略，继续执行后续任务\n" "- 查看详细错误：点击任务详情链接，展开 [恢复数据] 节点查看任务日志\n" "- 或从巡检报告中查看具体错误信息"
        )
        full_msg = _("【DBM】MySQL备份演练失败情况 {}\n\nbk_biz_id   集群域名   任务详情   DBA\n{}{}").format(
            datetime.date.today(), msg, handle_instruction
        )
        try:
            CmsiHandler(title, full_msg, chat_ids).send_wecom_robot()
            logger.info(_("成功推送演练失败通知"))
        except Exception as e:
            logger.error(_("推送演练失败通知异常: {}").format(e))
