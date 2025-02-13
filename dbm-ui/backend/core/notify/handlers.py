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
import re
import textwrap
from datetime import datetime, timedelta, timezone

from celery import shared_task
from django.utils.translation import gettext as _
from jinja2 import Environment

from backend import env
from backend.components import CmsiApi
from backend.components.bkchat.client import BkChatApi
from backend.configuration.constants import BizSettingsEnum
from backend.configuration.models import BizSettings
from backend.core.notify.constants import DEFAULT_BIZ_NOTIFY_CONFIG, MsgType
from backend.core.notify.exceptions import NotifyBaseException
from backend.core.notify.template import FAILED_TEMPLATE, FINISHED_TEMPLATE, TERMINATE_TEMPLATE, TODO_TEMPLATE
from backend.db_meta.models import AppCache
from backend.env import DEFAULT_USERNAME
from backend.exceptions import ApiResultError
from backend.ticket.builders import BuilderFactory
from backend.ticket.constants import TicketStatus, TicketType, TodoStatus
from backend.ticket.models import Flow, Ticket
from backend.ticket.todos import TodoActionType
from backend.utils.cache import func_cache_decorator

logger = logging.getLogger("root")


class BaseNotifyHandler:
    """
    通知基类
    """

    def __init__(self, title: str, content: str, receiver: list):
        """
        @param title: 通知标题
        @param content: 通知内容
        @param receiver: 接收者列表
        """
        self.title = title
        self.content = content
        self.receivers = receiver

    def send_msg(self, msg_type, context):
        """
        消息发送基础函数，由子类实现
        @param msg_type: 通知类型
        @param context: 通知上下文
        """
        raise NotImplementedError

    @classmethod
    def get_msg_type(cls):
        """支持消息发送类型，由子类实现"""
        raise NotImplementedError


class BkChatHandler(BaseNotifyHandler):
    """
    bkchat 处理类
    目前仅支持：企微，机器人两种模式
    """

    @classmethod
    def get_msg_type(cls):
        return [MsgType.WECOM_ROBOT.value, MsgType.RTX.value]

    @staticmethod
    def get_actions(msg_type, ticket):
        """获取bkchat操作按钮"""
        # TODO: 暂时去掉[待确认]按钮
        if not ticket or ticket.status not in [TicketStatus.APPROVE]:
            return []

        todo = ticket.todo_of_ticket.filter(status=TodoStatus.TODO).first()
        if not todo:
            return []

        # 增加回调按钮，执行和终止
        agree_action = {
            "name": _("同意") if ticket.status == TicketStatus.APPROVE else _("确认执行"),
            "color": "green",
            "callback_url": f"{env.BK_DBM_APIGATEWAY}/tickets/bkchat_process_todo/",
            "callback_data": {"action": TodoActionType.APPROVE.value, "todo_id": todo.id, "params": {}},
        }
        refuse_action = {
            "name": _("拒绝") if ticket.status == TicketStatus.APPROVE else _("终止单据"),
            "color": "red",
            "callback_url": f"{env.BK_DBM_APIGATEWAY}/tickets/bkchat_process_todo/",
            "callback_data": {
                "action": TodoActionType.TERMINATE.value,
                "todo_id": todo.id,
                "params": {"remark": _("使用「蓝鲸审批助手」终止单据")},
            },
        }
        return [agree_action, refuse_action]

    @staticmethod
    def get_title_color(phase):
        # 红色：已失败、已终止； 绿色：已完成；橙红色：其它
        if phase in [TicketStatus.FAILED, TicketStatus.TERMINATED]:
            return "red"
        elif phase in [TicketStatus.SUCCEEDED]:
            return "green"
        else:
            return "warning"

    def render_title_content(self, msg_type, title, content, phase, receivers):
        """重新渲染标题和内容样式，bkchat有特定要求"""
        # title 要加上样式
        title = re.sub(
            r"(?P<title>「DBM」：.+「[0-9]+?」)(?P<msg>.+)",
            r"\g<title><font color='{}'>\g<msg></font>".format(self.get_title_color(phase)),
            title,
        )
        # 终止提醒(如果有)也需要加上样式
        title = re.sub(
            r"(?P<time>.+?)(?P<msg> {})".format(_("前未处理将自动终止")), r"<font color='red'>\g<time></font> \g<msg>", title
        )

        # content要去掉点击详情，即最后一行，并且加上@通知人
        content = "\n".join(content.split("\n")[:-1])
        if msg_type == MsgType.WECOM_ROBOT:
            at_list = "".join([f"<@{staff}>" for staff in receivers])
            content += "\n" + at_list

        return title, content

    def send_msg(self, msg_type, context):
        ticket, phase, receivers = context["ticket"], context["phase"], context["receivers"]
        title, content = self.render_title_content(msg_type, self.title, self.content, phase, receivers)
        ticket_operators = ticket.get_current_operators()
        approvers = list(dict.fromkeys(ticket_operators["operators"] + ticket_operators["helpers"]))
        msg_info = {
            "title": title,
            # 处理人
            "approvers": approvers,
            # 微信消息时 receiver生效，不发群消息，群消息时，receive_group，不发送个人消息
            "receiver": self.receivers if msg_type == MsgType.RTX else [],
            "receive_group": self.receivers if msg_type == MsgType.WECOM_ROBOT else [],
            "summary": content,
            # 操作和详情按钮
            "actions": self.get_actions(msg_type, ticket),
            "click": {"click_url": ticket.url, "name": _("查看详情")},
        }
        BkChatApi.send_msg(msg_info, use_admin=True)


class CmsiHandler(BaseNotifyHandler):
    """
    cmsi 处理类，dbm通知发送的标准类
    支持：企微，机器人，邮件，语音，微信
    """

    @classmethod
    @func_cache_decorator(cache_time=60 * 60 * 24)
    def get_msg_type(cls):
        return [s["type"] for s in CmsiApi.get_msg_type()]

    def _cmsi_send_msg(self, msg_type: str, **kwargs):
        """
        @param msg_type: 发送类型
        @param kwargs: 额外参数
        """
        msg_info = {
            "msg_type": msg_type,
            "receiver__username": ",".join(self.receivers),
            "title": self.title,
            "content": self.content,
        }
        msg_info.update(kwargs)
        CmsiApi.send_msg(msg_info)

    def send_mail(self, sender: str = None, cc: list = None):
        """
        @param sender: 发送人，可选
        @param cc: 抄送人列表，可选
        """
        kwargs = {}
        if sender:
            kwargs.update(sender=sender)
        if cc:
            kwargs.update(cc__username=",".join(cc))
        # 邮件的换行要用<br>的html
        self.content = self.content.replace("\n", "<br>")
        self._cmsi_send_msg(MsgType.MAIL, **kwargs)

    def send_voice(self):
        """发送语音消息"""
        self._cmsi_send_msg(MsgType.VOICE.value)

    def send_weixin(self):
        """发送微信消息"""
        self._cmsi_send_msg(MsgType.WEIXIN.value)

    def send_rtx(self):
        """发送企微消息"""
        self._cmsi_send_msg(MsgType.RTX.value)

    def send_sms(self):
        """发送短信消息"""
        # 短信消息没有标题参数，直接把标题和内容放在一起
        self.content = f"{self.title}\n{self.content}"
        self._cmsi_send_msg(MsgType.SMS.value)

    def send_wecom_robot(self):
        """企微机器人发送消息"""
        wecom_robot = {
            "type": "text",
            "text": {"content": self.content},
            "group_receiver": self.receivers,
        }
        # 机器人发送，则receiver__username要置为用户名/admin。TODO: 应该支持填会话ID or 填空的
        self.receivers = [DEFAULT_USERNAME]
        self._cmsi_send_msg(MsgType.WECOM_ROBOT.value, sender=env.WECOM_ROBOT, wecom_robot=wecom_robot)

    def send_msg(self, msg_type, context):
        getattr(self, f"send_{msg_type}")()


class NotifyAdapter:
    """DBM通知适配器"""

    register_notify_class = [CmsiHandler, BkChatHandler]

    def __init__(self, ticket_id: int, deadline: int = None):
        """
        @param ticket_id: 单据ID
        """
        # 初始化单据，流程信息
        try:
            self.ticket = Ticket.objects.get(id=ticket_id)
        except (Ticket.DoesNotExist, Flow.DoesNotExist):
            raise NotifyBaseException(_("无法初始化通知适配器，无法找到此单据{}").format(ticket_id))

        # 当前阶段，对于运行中发通知的单据，实际上是【待继续】，这里做一次转换
        self.phase = TicketStatus.INNER_TODO if self.ticket.status == TicketStatus.RUNNING else self.ticket.status

        # 初始化通知人，集群额外信息
        self.bk_biz_id = self.ticket.bk_biz_id
        self.receivers = self.get_receivers()
        self.clusters = [cluster["immute_domain"] for cluster in self.ticket.details.pop("clusters", {}).values()]
        # 单据终止时间，用于终止提醒
        self.deadline = deadline

    @classmethod
    def get_support_msg_types(cls):
        # 获取当前环境下支持的通知类型
        # 所有的拓展方式都需要接入CMSI，所以直接返回CMSI支持方式即可
        # TODO: 暂不暴露微信的通知方式
        msg_types = CmsiApi.get_msg_type()
        msg_type_map = {msg["type"]: msg for msg in msg_types}
        msg_type_map[MsgType.WEIXIN.value]["is_active"] = False
        return list(msg_type_map.values())

    def get_notify_class(self, msg_type: str):
        # 根据通知类型获取通知类，以及通知所需的上下文
        if msg_type in [MsgType.WECOM_ROBOT, MsgType.RTX] and env.BKCHAT_APIGW_DOMAIN:
            context = {"ticket": self.ticket, "phase": self.phase, "receivers": self.get_receivers()}
            return BkChatHandler, context
        else:
            return CmsiHandler, {}

    def get_receivers(self):
        # 获取业务dba，业务协助人和提单人 三种角色
        biz_helpers = BizSettings.get_assistance(self.bk_biz_id)
        creator = [self.ticket.creator]
        # 待审批：审批人
        # 待执行、待补货、待确认、已失败、已完成、已终止：提单人、协助人
        # 暂不通知DBA
        if self.phase in [TicketStatus.PENDING]:
            receivers = creator
        elif self.phase in [TicketStatus.APPROVE]:
            itsm_builder = BuilderFactory.get_builder_cls(self.ticket.ticket_type).itsm_flow_builder(self.ticket)
            receivers = itsm_builder.get_approvers().split(",")
        else:
            receivers = creator + biz_helpers
        # 去重后返回
        return list(dict.fromkeys(receivers))

    def render_msg_template(self, msg_type: str):
        # 获取标题，在群机器人通知则加上@人
        title = _("「DBM」：您的{ticket_type}单据「{ticket_id}」{status}").format(
            ticket_type=TicketType.get_choice_label(self.ticket.ticket_type),
            ticket_id=self.ticket.id,
            status=TicketStatus.get_choice_label(self.phase),
        )

        # 渲染通知内容
        jinja_env = Environment()
        if self.phase in [TicketStatus.SUCCEEDED]:
            template = jinja_env.from_string(FINISHED_TEMPLATE)
        elif self.phase in [TicketStatus.FAILED]:
            template = jinja_env.from_string(FAILED_TEMPLATE)
        elif self.phase == TicketStatus.TERMINATED:
            template = jinja_env.from_string(TERMINATE_TEMPLATE)
        else:
            template = jinja_env.from_string(TODO_TEMPLATE)

        biz = AppCache.objects.get(bk_biz_id=self.bk_biz_id)
        ticket_operators = self.ticket.get_current_operators()
        payload = {
            "ticket_type": TicketType.get_choice_label(self.ticket.ticket_type),
            "biz_name": f"{biz.bk_biz_name}(#{self.bk_biz_id}, {biz.db_app_abbr})",
            "cluster_domains": ",".join(self.clusters),
            "remark": self.ticket.remark,
            "creator": self.ticket.creator,
            "submit_time": self.ticket.create_at.astimezone().strftime("%Y-%m-%d %H:%M:%S%z"),
            "update_time": self.ticket.update_at.astimezone().strftime("%Y-%m-%d %H:%M:%S%z"),
            "status": TicketStatus.get_choice_label(self.phase),
            "operators": ",".join(ticket_operators["operators"]),
            "helpers": ",".join(ticket_operators["helpers"]),
            "detail_address": self.ticket.url,
            "terminate_reason": self.ticket.get_terminate_reason(),
        }

        # 如果有终止时间，说明是一个终止提醒
        if self.deadline:
            timeout = datetime.now(timezone.utc) + timedelta(hours=self.deadline)
            timeout = timeout.astimezone().strftime("%Y-%m-%d %H:%M:%S%z")
            title += _("\n{} 前未处理将自动终止").format(timeout)

        content = textwrap.dedent(template.render(payload))
        return title, content

    def send_msg(self):
        # 获取单据通知设置，优先: 单据配置 > 业务配置 > 默认业务配置
        if self.phase in self.ticket.send_msg_config:
            send_msg_config = self.ticket.send_msg_config[self.phase]
        else:
            biz_notify_config = BizSettings.get_setting_value(
                self.bk_biz_id, key=BizSettingsEnum.NOTIFY_CONFIG, default=DEFAULT_BIZ_NOTIFY_CONFIG
            )
            send_msg_config = biz_notify_config[self.phase]

        send_msg_types = [msg_type for msg_type in send_msg_config if send_msg_config.get(msg_type)]

        for msg_type in send_msg_types:
            notify_class, context = self.get_notify_class(msg_type)

            if msg_type not in notify_class.get_msg_type():
                logger.warning(_("通知类{}不支持该类型{}的消息发送").format(notify_class, msg_type))
                continue

            # 获取通知内容，发送通知
            title, content = self.render_msg_template(msg_type)

            # 如果是群机器人通知，则接受者为群ID
            if msg_type == MsgType.WECOM_ROBOT:
                self.receivers = send_msg_config.get(MsgType.WECOM_ROBOT.value, [])

            try:
                notify_class(title, content, self.receivers).send_msg(msg_type, context=context)
            except (ApiResultError, Exception) as e:
                logger.error(_("[{}]消息发送失败，错误信息: {}").format(MsgType.get_choice_label(msg_type), e))


@shared_task
def send_msg(ticket_id: int, deadline: int = None):
    # 可异步发送消息，非阻塞路径默认不抛出异常
    NotifyAdapter(ticket_id, deadline).send_msg()
