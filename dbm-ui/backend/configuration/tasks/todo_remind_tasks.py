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
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Dict

from blueapps.account.models import User
from celery import shared_task
from django.db.models import Count, Q
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from backend import env
from backend.components import BKMonitorV3Api
from backend.configuration.constants import (
    DAILY_TODO_REMIND_DEFAULT,
    DBM_USER_TODO_TYPE_MAP_DEFAULT,
    SystemSettingsEnum,
)
from backend.configuration.models import DBAdministrator, SystemSettings
from backend.core.notify.constants import MsgType
from backend.core.notify.handlers import BkChatHandler, CmsiHandler
from backend.db_report.enums import ReportStateType
from backend.db_report.register import db_report_maps
from backend.db_services.risk_memo.models.risk_memo import RiskMemo
from backend.ticket.constants import TICKET_TODO_STATUS_SET, TODO_RUNNING_STATUS, CountType, TodoStatus, TodoType
from backend.ticket.models import Ticket, Todo

logger = logging.getLogger("celery")

TODO_TYPE_CONTEXT = {
    "APPROVE": _("待审批"),
    "TODO": _("待执行"),
    "INNER_TODO": _("待继续"),
    "RESOURCE_REPLENISH": _("待补货"),
    "FAILED": _("失败待处理"),
    "TIMER": _("定时中"),
}

REMIND_TITLE = _("【DBM 每日待办提醒】")

TODO_DIR = f"{env.BK_SAAS_HOST}/ticket-self-todo"

MASS_CONTEXT_TEMPLATE = _("\n以下 DBA 有待办事项待处理：\n\n{}\n\n共 {} 人，{} 项待办\n\n前往处理 > {}")

ONE_ON_ONE_CONTEXT_TEMPLATE = _("\n你有以下待办事项待处理：\n\n{}\n\n前往处理 > {}")


class CalcPersonalTodoClass:
    @classmethod
    def get_ticket_todo_count(cls, username, infos):
        """获取单据代办"""
        exclude_values = {"MY_APPROVE", "SELF_MANAGE", "DONE"}
        count_map = {count_type: 0 for count_type in CountType.get_values() if count_type not in exclude_values}
        status_counts = (
            Ticket.objects.filter(
                status__in=TICKET_TODO_STATUS_SET,
                todo_of_ticket__operators__contains=username,
                todo_of_ticket__status__in=TODO_RUNNING_STATUS,
            )
            .distinct()
            .values_list("status", flat=True)
        )
        for sts, count in Counter(status_counts).items():
            sts = CountType.INNER_TODO.value if sts == "RUNNING" else sts
            count_map[TODO_TYPE_CONTEXT[sts]] = count
        new_count_map = {key: value for key, value in count_map.items() if value}
        return new_count_map

    @classmethod
    def get_inspect_todo_count(cls, username, infos):
        """获取巡检代办"""
        result_map: Dict[str, int] = defaultdict(int)
        now_date = datetime.now(timezone.utc).date()
        for db_type, report_classes in db_report_maps.items():
            total_count = 0
            # 获取用户的管理业务
            manage_bizs = [info["bk_biz_id"] for info in infos if db_type == info["db_type"]]
            for cls_ in report_classes:
                # 过滤当天的代办
                count = cls_.queryset.filter(
                    state=ReportStateType.ABNORMAL, update_at__gte=now_date, bk_biz_id__in=manage_bizs
                ).count()
                total_count += count
            result_map[db_type] = total_count
        new_result_map = {key: value for key, value in result_map.items() if value}
        return new_result_map

    @classmethod
    def get_cluster_disable_todo_count(cls, username, infos):
        """获取集群下架代办"""
        todos = Todo.objects.filter(
            status=TodoStatus.TODO, type=TodoType.CLUSTER_DISABLE, operators__contains=username
        )
        cluster_type_count = {}
        for todo in todos:
            if todo.context["db_type"] not in cluster_type_count:
                cluster_type_count[todo.context["db_type"]] = 1
            else:
                cluster_type_count[todo.context["db_type"]] += 1
        return cluster_type_count

    @classmethod
    def get_host_todo_count(cls, username, infos):
        """获取主机代办"""
        result = Todo.objects.filter(
            operators__contains=username, status="TODO", type__in=["RECYCLE_HOST", "FAULT_HOST"]
        ).aggregate(
            recycle_count=Count("id", filter=Q(type="RECYCLE_HOST")),
            fault_count=Count("id", filter=Q(type="FAULT_HOST")),
        )
        return result["recycle_count"] + result["fault_count"]

    @classmethod
    def get_alarm_todo_count(cls, username, infos):
        """获取告警代办"""

        now_time = int(datetime.now().timestamp())
        start_time = int((datetime.now() - timedelta(days=7)).timestamp())
        params = {
            "bk_biz_ids": [env.DBA_APP_BK_BIZ_ID],
            "page": 1,
            "page_size": 20,
            "start_time": start_time,
            "end_time": now_time,
        }
        biz_cluster_type_conditions = [
            f'(tags.appid : "{info["bk_biz_id"]}" AND labels: "DBM_{info["db_type"].upper()}")' for info in infos
        ]
        if not biz_cluster_type_conditions:
            return 0
        conditions = []
        biz_cluster_type_query_string = " OR ".join(set(biz_cluster_type_conditions))
        conditions.append(f"({biz_cluster_type_query_string})")
        params["query_string"] = " AND ".join(conditions)
        data = BKMonitorV3Api.search_alert(params)
        return data["overview"].get("count", 0)

    @classmethod
    def get_risk_memo_todo_count(cls, username, infos):
        """获取风险备忘录"""

        if not infos:
            return 0

        qs = Q()
        for info in infos:
            qs |= Q(bk_biz_id=info["bk_biz_id"], db_type=info["db_type"])

        if not qs.children:
            return 0
        count = RiskMemo.objects.filter(qs).filter(status="backlog").count()

        return count


def get_todo_context(count, text):
    """
    获取各个类型代办的模板
    """
    # 当传入是一个数量时，直接生成模板返回
    if isinstance(count, int):
        if count:
            return _("- {text} {count}条").format(text=text, count=count)

    # 当传入的是一个字典时，则代办需要生成各类型的代办明细模板
    elif isinstance(count, dict):
        total = sum(count.values())
        if total:
            contexts = [f"{type_} {count}" for type_, count in count.items()]
            contexts = "，".join(contexts)
            return _("- {text}：{total} 条（{contexts}）").format(text=text, total=total, contexts=contexts)
    return ""


def get_mass_context(user_infos):
    """组装群聊的代办模板"""
    all_total = 0
    user_contexts = ""
    for username in user_infos:
        context_list = [context.replace("- ", "") for context in user_infos[username]["context_list"] if context]
        all_total += user_infos[username]["count"]
        user_context = "，".join(context_list)
        user_contexts += f"{username}：{user_context}\n"

    if not all_total:
        return ""
    return MASS_CONTEXT_TEMPLATE.format(user_contexts, len(user_infos), all_total, TODO_DIR)


def get_single_context(detail):
    """组装个人的代办模板"""
    context_list = detail["context_list"]
    context_list = [context for context in context_list if context]
    context = "\n".join(context_list)
    return ONE_ON_ONE_CONTEXT_TEMPLATE.format(context, TODO_DIR)


def get_dba_infos():
    """获取所有dba的信息"""
    admin_records = DBAdministrator.objects.all().values_list("bk_biz_id", "db_type", "users")
    dba_infos = defaultdict(list)

    for bk_biz_id, db_type, users in admin_records:
        if users:
            primary_user = users[0]

            dba_infos[primary_user].append({"bk_biz_id": bk_biz_id, "db_type": db_type, "users": users})

    return dict(dba_infos)


@shared_task
def send_todo_remind():

    # 获取代办通知配置， 未开启则不做处理
    todo_remind_conf = SystemSettings.get_setting_value(
        SystemSettingsEnum.DBM_DAILY_TODO_REMIND, default=DAILY_TODO_REMIND_DEFAULT
    )
    if not todo_remind_conf["is_enable"]:
        return

    # 没有通知方式也不做处理
    send_types = [conf["type"] for conf in todo_remind_conf["notice"]]
    if not send_types:
        return

    users = User.objects.all()
    user_todo_map = SystemSettings.get_setting_value(
        SystemSettingsEnum.DBM_USER_TODO_TYPE_MAP, default=DBM_USER_TODO_TYPE_MAP_DEFAULT
    )
    todo_types = user_todo_map["types"]

    dba_user = {}
    no_dba_user = {}

    dba_infos = get_dba_infos()

    # 对每个用户进行代办查询，有代办则发送通知
    for user in users:
        user_all_todo_info = {"count": 0, "context_list": []}
        is_dba = True if user.username in dba_infos else False

        todo_funcs = user_todo_map["dba" if is_dba else "ordinary"]

        # 每个用户对应需要收集的代办信息，收集总数以及代办模板
        for todo_func in todo_funcs:
            func_name = f"get_{todo_func}_count"
            if not hasattr(CalcPersonalTodoClass, func_name):
                continue

            count_info = getattr(CalcPersonalTodoClass, func_name)(user.username, dba_infos.get(user.username, []))
            if isinstance(count_info, int):
                user_all_todo_info["count"] += count_info
            elif isinstance(count_info, dict):
                user_all_todo_info["count"] += sum(count_info.values())
            user_all_todo_info["context_list"].append(get_todo_context(count_info, todo_types[todo_func]))

        # 如果没有代办数量则跳过
        if not user_all_todo_info["count"]:
            continue

        if is_dba:
            dba_user[user.username] = user_all_todo_info
        else:
            no_dba_user[user.username] = user_all_todo_info

    # 如果有群里，则发送群聊消息
    if MsgType.WECOM_ROBOT.value in send_types:
        mass_context = get_mass_context(dba_user)
        if mass_context:
            receivers = [
                conf["value"] for conf in todo_remind_conf["notice"] if conf["type"] == MsgType.WECOM_ROBOT.value
            ][0].split(",")
            BkChatHandler(REMIND_TITLE, mass_context, receivers).send_custom_msg()

        # 发送完群聊剔除对应的类型
        send_types.remove(MsgType.WECOM_ROBOT)

    if not send_types:
        return

    # 对剩下的通知类型进行通知，有代办的用户都会通知到
    dba_user.update(no_dba_user)
    for username in dba_user:
        ordinary_context = get_single_context(dba_user[username])
        if not ordinary_context:
            continue
        if MsgType.RTX.value in send_types:
            BkChatHandler(REMIND_TITLE, ordinary_context, [username]).send_custom_msg()
        if MsgType.MAIL.value in send_types:
            CmsiHandler(REMIND_TITLE, ordinary_context, [username]).send_msg(MsgType.MAIL.value, context=None)
