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
from typing import Dict, Set

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
    WECOM_GROUP_MAX_USERS_PER_MSG,
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
    "CONFIRM_PENDING": _("待确认修改"),
    "FAILED": _("失败待处理"),
    "TIMER": _("定时中"),
}

REMIND_TITLE = _("「DBM」：每日待办提醒")

TODO_DIR = f"{env.BK_SAAS_HOST}/ticket-self-todo"

ONE_ON_ONE_CONTEXT_TEMPLATE = _("\nHi，{}\n\n您在「DBM」共有 {} 条待办待处理：\n\n{}\n\n")

# 群消息模板
GROUP_HEADER_TEMPLATE = _("DBA：{user_count} 人，待办 {todo_count} 条")
GROUP_USER_TODO_TEMPLATE = _("{username}（{count} 条）：{details}")
GROUP_USER_EMPTY_TEMPLATE = _("{username}：{empty_text}")
GROUP_LINK_TEMPLATE = _("{text}：{url}")
TODO_EMPTY_TEXT = _("待办已清空")

USER_TODO_SEPARATOR = "\n\u200b\n"

# 计算待办的并发线程数
CALC_TODO_THREAD_NUM = 10


class CalcPersonalTodoClass:
    @classmethod
    def get_ticket_todo_count(cls, username, infos):
        """获取单据待办"""
        status_counts = (
            Ticket.objects.filter(
                status__in=TICKET_TODO_STATUS_SET,
                todo_of_ticket__operators__contains=username,
                todo_of_ticket__status__in=TODO_RUNNING_STATUS,
            )
            .distinct()
            .values_list("status", flat=True)
        )
        result_map = defaultdict(int)
        for sts, count in Counter(status_counts).items():
            # RUNNING 归并到「待继续」
            sts = CountType.INNER_TODO.value if sts == "RUNNING" else sts
            # 新增的单据状态未必能及时补到文案映射里，兜底用枚举文案/状态值，避免整个提醒任务失败
            if sts in TODO_TYPE_CONTEXT:
                label = TODO_TYPE_CONTEXT[sts]
            elif sts in CountType.get_values():
                label = CountType.get_choice_label(sts)
            else:
                label = sts
            result_map[label] += count
        return dict(result_map)

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

        # 主负责的业务：DBA 人员列表的第一个是该用户
        biz_cluster_type_conditions = [
            f'(tags.appid : "{dba.bk_biz_id}" AND labels: "DBM_{dba.db_type.upper()}")'
            for dba in DBAdministrator.objects.filter(users__contains=username)
            if dba.users and dba.users[0] == username
        ]
        if not biz_cluster_type_conditions:
            return 0

        now = datetime.now()
        params = {
            "bk_biz_ids": [env.DBA_APP_BK_BIZ_ID],
            "page": 1,
            "page_size": 20,
            "start_time": int((now - timedelta(days=7)).timestamp()),
            "end_time": int(now.timestamp()),
        }
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
    获取各个类型待办的模板，群消息与个人消息共用
    """
    # 当传入是一个数量时，直接生成模板返回
    if isinstance(count, int):
        if count:
            return _("{text} {count} 条").format(text=text, count=count)

    # 当传入的是一个字典时，则待办需要生成各类型的待办明细模板
    elif isinstance(count, dict):
        total = sum(count.values())
        if total:
            contexts = [f"{DBType.get_choice_label(type_)} {count}" for type_, count in count.items()]
            contexts = "，".join(contexts)
            return _("{text} {total} 条（{contexts}）").format(text=text, total=total, contexts=contexts)
    return ""


def get_db_type_dba_map() -> Dict[str, Set[str]]:
    """获取 数据库组件类型 -> 当前 DBA 人员 的映射

    按组件类型跨业务合并（含 bk_biz_id 为 0 的平台默认 DBA 记录）。
    每次发送时实时读取，人员变更从下一次提醒自动生效。
    """
    db_type_dba_map: Dict[str, Set[str]] = defaultdict(set)
    for db_type, users in DBAdministrator.objects.values_list("db_type", "users"):
        if not users or db_type not in DBType.get_values():
            continue
        db_type_dba_map[db_type].update(users)
    return db_type_dba_map


def resolve_rule_dba_users(rule, db_type_dba_map) -> Set[str]:
    """计算单条群通知规则圈定的 DBA 人员（所选组件当前 DBA 的并集）"""
    users = set()
    for db_type in rule.get("components") or []:
        db_type_users = db_type_dba_map.get(db_type)
        if db_type_users is None:
            # 组件当前没有任何 DBA 配置时跳过，不影响同规则内其他组件
            logger.warning(_("todo remind rule component has no dba: {}").format(db_type))
            continue
        users.update(db_type_users)
    return users


def get_dba_infos():
    """获取所有dba的信息：username -> 该 DBA 作为 DBA 负责的全部组件"""
    dba_infos = defaultdict(list)
    for bk_biz_id, db_type, users in DBAdministrator.objects.values_list("bk_biz_id", "db_type", "users"):
        if not users:
            continue
        for username in users:
            dba_infos[username].append({"bk_biz_id": bk_biz_id, "db_type": db_type, "users": list(users)})

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


def calc_user_todo(username, dba_infos, user_todo_map, todo_types):
    """计算单个用户的待办信息

    注意：待办范围只与人有关，与群通知规则里圈人的组件无关。
    DBA 按其负责的全部组件统计待办，非 DBA 只统计普通待办类型。
    """
    user_component_infos = dba_infos.get(username, [])
    todo_funcs = user_todo_map["dba" if user_component_infos else "ordinary"]

    user_todo_info = {"count": 0, "context_list": []}
    for todo_func in todo_funcs:
        func = getattr(CalcPersonalTodoClass, f"get_{todo_func}_count", None)
        if func is None:
            continue
        try:
            count_info = func(username, user_component_infos)
        except Exception:
            # 单个待办类型统计失败不影响该用户其它类型，更不影响整批提醒
            logger.exception("calc todo count error, username: %s, todo_func: %s", username, todo_func)
            continue
        if isinstance(count_info, int):
            user_todo_info["count"] += count_info
        elif isinstance(count_info, dict):
            user_todo_info["count"] += sum(count_info.values())

        context = get_todo_context(count_info, todo_types.get(todo_func, todo_func))
        if context:
            user_todo_info["context_list"].append(context)

    return user_todo_info


def _calc_user_todo_chunk(usernames, dba_infos, user_todo_map, todo_types):
    """处理一批用户的待办计算，返回该批次所有用户的待办信息（含待办为 0 的用户）"""
    return {username: calc_user_todo(username, dba_infos, user_todo_map, todo_types) for username in usernames}


def calc_user_todos(usernames, dba_infos, user_todo_map, todo_types):
    """多线程计算一批用户的待办，返回 username -> 待办信息"""
    usernames = list(usernames)
    if not usernames:
        return {}

    num_threads = min(CALC_TODO_THREAD_NUM, len(usernames))
    chunk_size = max(1, len(usernames) // num_threads)
    user_chunks = [usernames[index : index + chunk_size] for index in range(0, len(usernames), chunk_size)]

    user_todo_infos = {}
    with concurrent.futures.ThreadPoolExecutor(max_workers=num_threads) as executor:
        futures = [
            executor.submit(_calc_user_todo_chunk, chunk, dba_infos, user_todo_map, todo_types)
            for chunk in user_chunks
        ]
        for future in concurrent.futures.as_completed(futures):
            user_todo_infos.update(future.result())

    return user_todo_infos


def get_group_context(user_items):
    """组装单条群消息，user_items: [(username, 待办信息)]"""
    todo_total = sum(user_info["count"] for _, user_info in user_items)

    user_contexts = []
    receivers = []
    for username, user_info in user_items:
        if user_info["count"]:
            receivers.append(username)
            user_contexts.append(
                GROUP_USER_TODO_TEMPLATE.format(
                    username=username,
                    count=user_info["count"],
                    details="，".join(user_info["context_list"]),
                )
            )
        else:
            user_contexts.append(GROUP_USER_EMPTY_TEMPLATE.format(username=username, empty_text=TODO_EMPTY_TEXT))

    contexts = [GROUP_HEADER_TEMPLATE.format(user_count=len(user_items), todo_count=todo_total)]
    # 一人一块，相邻两个用户之间空一行
    contexts.append(USER_TODO_SEPARATOR.join(user_contexts))
    # 只 @ 本条消息中待办条数大于 0 的人
    if receivers:
        contexts.append(" ".join(f"<@{staff}>" for staff in receivers))
    contexts.append(GROUP_LINK_TEMPLATE.format(text=_("前往处理"), url=TODO_DIR))

    return "\n{}\n".format("\n\n".join(contexts))


def get_group_contexts(user_items):
    """按待办条数从多到少排列，每 WECOM_GROUP_MAX_USERS_PER_MSG 人一条消息"""
    sorted_user_items = sorted(user_items, key=lambda item: (-item[1]["count"], item[0]))
    return [
        get_group_context(sorted_user_items[index : index + WECOM_GROUP_MAX_USERS_PER_MSG])
        for index in range(0, len(sorted_user_items), WECOM_GROUP_MAX_USERS_PER_MSG)
    ]


def get_single_context(detail, username):
    """组装个人的待办模板"""
    context_list = detail["context_list"]
    context_list = [context for context in context_list if context]
    context = "\n".join(context_list)
    return ONE_ON_ONE_CONTEXT_TEMPLATE.format(username, detail.get("count"), context)


@shared_task
def send_todo_remind():

    # 获取待办通知配置， 未开启则不做处理
    todo_remind_conf = SystemSettings.get_setting_value(
        SystemSettingsEnum.DBM_DAILY_TODO_REMIND, default=DAILY_TODO_REMIND_DEFAULT
    )
    if not todo_remind_conf.get("is_enable"):
        return

    # 群通知规则：每条规则配置一个企微群 + 待办人员范围（数据库组件）
    wecom_group_rules = todo_remind_conf.get("wecom_group_rules") or []
    # 个人通知渠道（企微群聊已由群通知规则接管，不再走个人通知）
    personal_types = [
        conf["type"] for conf in todo_remind_conf.get("notice") or [] if conf["type"] != MsgType.WECOM_ROBOT.value
    ]
    if not personal_types and not wecom_group_rules:
        return

    user_todo_map = SystemSettings.get_setting_value(
        SystemSettingsEnum.DBM_USER_TODO_TYPE_MAP, default=DBM_USER_TODO_TYPE_MAP_DEFAULT
    )
    todo_types = user_todo_map["types"]
    dba_infos = get_dba_infos()

    # 待办人员范围以每次发送时的最新组件 DBA 关系计算
    db_type_dba_map = get_db_type_dba_map() if wecom_group_rules else {}
    rule_dba_users = [(rule, resolve_rule_dba_users(rule, db_type_dba_map)) for rule in wecom_group_rules]

    # 只计算需要通知的用户：群规则圈定的 DBA + 个人通知开启时的全量用户
    target_usernames = set()
    for _rule, dba_users in rule_dba_users:
        target_usernames.update(dba_users)
    if personal_types:
        target_usernames.update(User.objects.values_list("username", flat=True))

    user_todo_infos = calc_user_todos(target_usernames, dba_infos, user_todo_map, todo_types)

    # 1. 按群通知规则发送群消息
    for rule, dba_users in rule_dba_users:
        chat_id = rule["chat_id"]
        if not dba_users:
            logger.info("wecom group {} has no dba, skip this time".format(chat_id))
            continue

        user_items = [
            (username, user_todo_infos.get(username) or {"count": 0, "context_list": []}) for username in dba_users
        ]
        for group_context in get_group_contexts(user_items):
            send_msg(REMIND_TITLE, group_context, [chat_id], MsgType.WECOM_ROBOT)
            # 防止发送频率过快被限
            time.sleep(0.5)

    # 2. 个人通知：有待办的用户都会通知到
    if not personal_types:
        return

    for username, user_todo_info in user_todo_infos.items():
        if not user_todo_info["count"]:
            continue
        ordinary_context = get_single_context(user_todo_info, username)
        if not ordinary_context:
            continue
        try:
            if MsgType.RTX.value in personal_types:
                send_msg(REMIND_TITLE, ordinary_context, [username], MsgType.RTX)
            if MsgType.MAIL.value in personal_types:
                send_msg(REMIND_TITLE, ordinary_context, [username], MsgType.MAIL)

        except Exception as e:
            logger.error("send todo remind error: {}".format(e))
