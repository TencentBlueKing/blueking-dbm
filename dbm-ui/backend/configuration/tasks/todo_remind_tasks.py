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
import concurrent.futures
import logging
import time
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Dict

from blueapps.account.models import User
from celery import shared_task
from django.db.models import Count, Q
from django.utils import timezone
from django.utils.translation import gettext as _

from backend import env
from backend.components import BKMonitorV3Api
from backend.configuration.constants import (
    DAILY_TODO_REMIND_DEFAULT,
    DBM_USER_TODO_TYPE_MAP_DEFAULT,
    DBType,
    SystemSettingsEnum,
)
from backend.configuration.models import DBAdministrator, SystemSettings
from backend.core.notify.constants import MsgType
from backend.core.notify.handlers import BkChatApi, BkChatHandler, CmsiHandler
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

CATEGORY_MAP = {
    DBType.MySQL.value: "storage",
    DBType.TenDBCluster.value: "storage",
    DBType.Sqlserver.value: "storage",
    DBType.Redis.value: "memory",
    DBType.MongoDB.value: "memory",
    DBType.Oracle.value: "memory",
    DBType.Es.value: "big_data",
    DBType.Kafka.value: "big_data",
    DBType.Doris.value: "big_data",
    DBType.Hdfs.value: "big_data",
    DBType.Pulsar.value: "big_data",
}

REMIND_TITLE = _("「DBM」：每日待办提醒")

TODO_DIR = f"{env.BK_SAAS_HOST}/ticket-self-todo"

# MASS_CONTEXT_TEMPLATE = _("\n以下 DBA 有待办事项待处理：\n\n{}\n\n共 {} 人，{} 项待办\n")
MASS_CONTEXT_TEMPLATE = _("\n本条消息涉及DBA：{} 人\n待办总数：{}条\n\n{}\n")

# ONE_ON_ONE_CONTEXT_TEMPLATE = _("\n你有以下待办事项待处理：\n\n{}\n")
ONE_ON_ONE_CONTEXT_TEMPLATE = _("\nHi，{}\n\n您在「DBM」共有 {} 条待办待处理：\n\n{}\n\n")


class CalcPersonalTodoClass:
    @classmethod
    def get_ticket_todo_count(cls, username, infos):
        """获取单据待办"""
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
        """获取巡检待办"""
        result_map: Dict[str, int] = defaultdict(int)
        now_date = datetime.now(timezone.utc).date()
        for db_type, report_classes in db_report_maps.items():
            total_count = 0
            # 获取用户的管理业务
            manage_bizs = [info["bk_biz_id"] for info in infos if db_type == info["db_type"]]
            for cls_ in report_classes:
                # 过滤当天的待办
                count = cls_.queryset.filter(
                    state=ReportStateType.ABNORMAL, update_at__gte=now_date, bk_biz_id__in=manage_bizs
                ).count()
                total_count += count
            result_map[db_type] = total_count
        new_result_map = {key: value for key, value in result_map.items() if value}
        return new_result_map

    @classmethod
    def get_cluster_disable_todo_count(cls, username, infos):
        """获取集群下架待办"""
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
        """获取主机待办"""
        result = Todo.objects.filter(
            operators__contains=username, status="TODO", type__in=["RECYCLE_HOST", "FAULT_HOST"]
        ).aggregate(
            recycle_count=Count("id", filter=Q(type="RECYCLE_HOST")),
            fault_count=Count("id", filter=Q(type="FAULT_HOST")),
        )
        return result["recycle_count"] + result["fault_count"]

    @classmethod
    def get_alarm_todo_count(cls, username, infos):
        """获取告警待办"""

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
        conditions.append('status: "ABNORMAL"')
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
    获取各个类型待办的模板
    """
    # 当传入是一个数量时，直接生成模板返回
    if isinstance(count, int):
        if count:
            return _("{text} {count}条").format(text=text, count=count)

    # 当传入的是一个字典时，则待办需要生成各类型的待办明细模板
    elif isinstance(count, dict):
        total = sum(count.values())
        if total:
            contexts = [f"{DBType.get_choice_label(type_)} {count}" for type_, count in count.items()]
            contexts = "，".join(contexts)
            return _("{text}：{total} 条（{contexts}）").format(text=text, total=total, contexts=contexts)
    return ""


def get_db_type_dba_group(user_infos, groups):
    """按组件性质划分dba人员组，对已经计算出结果的dba人员进行分组"""
    storage_set = groups.get("storage", set())
    memory_set = groups.get("memory", set())
    big_data_set = groups.get("big_data", set())

    storage_group = {}
    memory_group = {}
    big_data_group = {}
    other_group = {}

    # 人员划分到各自对应的组里， 目前分四个组
    for username, info in user_infos.items():
        if username in storage_set:
            storage_group[username] = info
        elif username in memory_set:
            memory_group[username] = info
        elif username in big_data_set:
            big_data_group[username] = info
        else:
            other_group[username] = info

    return [storage_group, memory_group, big_data_group, other_group]


def get_mass_context(user_infos, groups):
    """组装群聊的待办模板"""
    db_type_groups = get_db_type_dba_group(user_infos, groups)
    contexts = []
    # 按不同的组件架构发送通知
    for db_type_group in db_type_groups:
        all_total = 0
        max_len = 800
        user_contexts = ""
        receivers = []
        all_user_count = len(db_type_group)
        for username in db_type_group:
            all_user_count -= 1
            receivers.append(username)
            context_list = [context for context in db_type_group[username]["context_list"] if context]
            all_total += db_type_group[username]["count"]
            user_context = "，".join(context_list)
            user_contexts += f"{username}：{user_context}\n"

            if len(user_contexts) > max_len or all_user_count == 0:
                at_list = "".join([f"<@{staff}>" for staff in receivers])
                user_contexts += "\n" + at_list
                contexts.append(MASS_CONTEXT_TEMPLATE.format(len(receivers), all_total, user_contexts))
                receivers = []
                user_contexts = ""
                all_total = 0
    return contexts


def get_single_context(detail, username):
    """组装个人的待办模板"""
    context_list = detail["context_list"]
    context_list = [context for context in context_list if context]
    context = "\n".join(context_list)
    return ONE_ON_ONE_CONTEXT_TEMPLATE.format(username, detail.get("count"), context)


def get_dba_infos():
    """获取所有dba的信息"""
    admin_records = DBAdministrator.objects.all().values_list("bk_biz_id", "db_type", "users")
    dba_infos = defaultdict(list)

    for bk_biz_id, db_type, users in admin_records:
        if users:
            primary_user = users[0]

            dba_infos[primary_user].append({"bk_biz_id": bk_biz_id, "db_type": db_type, "users": users})

    return dict(dba_infos)


def send_msg(title, context, receivers, msg_type):
    logger.info(_("start send todo remind, receiver: {}").format(receivers))
    try:
        if msg_type in BkChatHandler.get_msg_type():
            msg_info = {
                "title": title,
                # 处理人
                "approvers": [],
                # 微信消息时 receiver生效，不发群消息，群消息时，receive_group，不发送个人消息
                "receiver": receivers if msg_type == MsgType.RTX else [],
                "receive_group": receivers if msg_type == MsgType.WECOM_ROBOT else [],
                "summary": context,
                # 操作和详情按钮
                "actions": [],
                "click": {"click_url": TODO_DIR, "name": _("前往处理")},
            }
            BkChatApi.send_ticket_msg(msg_info, use_admin=True)

        elif msg_type == MsgType.MAIL.value:
            context += '\n<p><a href="{}">{}</a></p>'.format(TODO_DIR, _("前往处理"))
            CmsiHandler(title, context, receivers).send_msg(MsgType.MAIL.value, context=None)

        logger.info(_("send todo remind succeed, receiver: {}".format(receivers)))
    except Exception as e:
        logger.error(_("send todo remind error, receivers: {}, error: {}").format(receivers, e))


def _process_user_chunk(
    user_chunk,
    dba_infos,
    user_todo_map,
    todo_types,
):
    """
    处理一批用户，返回该批次中的 dba 和非 dba 用户待办信息
    """
    local_dba = {}
    local_no_dba = {}

    for user in user_chunk:
        user_all_todo_info = {"count": 0, "context_list": []}
        is_dba = user.username in dba_infos

        todo_funcs = user_todo_map["dba" if is_dba else "ordinary"]

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

        if user_all_todo_info["count"]:
            if is_dba:
                local_dba[user.username] = user_all_todo_info
            else:
                local_no_dba[user.username] = user_all_todo_info

    return local_dba, local_no_dba


@shared_task
def send_todo_remind():

    # 获取待办通知配置， 未开启则不做处理
    todo_remind_conf = SystemSettings.get_setting_value(
        SystemSettingsEnum.DBM_DAILY_TODO_REMIND, default=DAILY_TODO_REMIND_DEFAULT
    )
    if not todo_remind_conf["is_enable"]:
        return

    # 没有通知方式也不做处理
    send_types = [conf["type"] for conf in todo_remind_conf["notice"]]
    if not send_types:
        return

    users = list(User.objects.all())
    user_todo_map = SystemSettings.get_setting_value(
        SystemSettingsEnum.DBM_USER_TODO_TYPE_MAP, default=DBM_USER_TODO_TYPE_MAP_DEFAULT
    )
    todo_types = user_todo_map["types"]
    dba_infos = get_dba_infos()
    # 将用户列表均匀分成10份（若不足10人则每人一份）
    num_threads = 10
    chunk_size = max(1, len(users) // num_threads)
    user_chunks = [users[i : i + chunk_size] for i in range(0, len(users), chunk_size)]

    dba_user = {}
    no_dba_user = {}
    # 多线程执行
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [
            executor.submit(_process_user_chunk, chunk, dba_infos, user_todo_map, todo_types) for chunk in user_chunks
        ]
        for future in concurrent.futures.as_completed(futures):
            local_dba, local_no_dba = future.result()
            dba_user.update(local_dba)
            no_dba_user.update(local_no_dba)

    # 如果有群里，则发送群聊消息
    if MsgType.WECOM_ROBOT.value in send_types:
        groups = defaultdict(set)
        # dba人员表按组件架构做分组
        for admin in DBAdministrator.objects.all():
            if not admin.users:
                continue
            category = CATEGORY_MAP.get(admin.db_type, "other")
            groups[category].update(admin.users)

        mass_contexts = get_mass_context(dba_user, groups)
        if mass_contexts:
            receivers = [
                conf["value"] for conf in todo_remind_conf["notice"] if conf["type"] == MsgType.WECOM_ROBOT.value
            ][0].split(",")
            for mass_context in mass_contexts:
                send_msg(REMIND_TITLE, mass_context, receivers, MsgType.WECOM_ROBOT)
                # 防止发送频率过快被限
                time.sleep(0.5)

        # 发送完群聊剔除对应的类型
        send_types.remove(MsgType.WECOM_ROBOT)

    if not send_types:
        return

    # 对剩下的通知类型进行通知，有待办的用户都会通知到
    dba_user.update(no_dba_user)
    for username in dba_user:
        ordinary_context = get_single_context(dba_user[username], username)
        if not ordinary_context:
            continue
        try:
            if MsgType.RTX.value in send_types:
                send_msg(REMIND_TITLE, ordinary_context, [username], MsgType.RTX)
            if MsgType.MAIL.value in send_types:
                send_msg(REMIND_TITLE, ordinary_context, [username], MsgType.MAIL)

        except Exception as e:
            logger.error("send todo remind error: {}".format(e))
