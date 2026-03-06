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

from django.utils.translation import gettext_lazy as _

from ..base import BaseApi
from ..domains import CMSI_APIGW_DOMAIN


class _CmsiApi(BaseApi):
    MODULE = _("消息管理")
    BASE = CMSI_APIGW_DOMAIN

    # 消息类型映射定义
    @property
    def MSG_TYPE_MAP(self):
        from ...core.notify.constants import MsgType

        return {
            MsgType.VOICE.value: "send_voice",
            MsgType.SMS.value: "send_sms",
            MsgType.WEIXIN.value: "send_weixin",
            MsgType.MAIL.value: "send_mail",
        }

    def __init__(self):
        self.is_esb = self.is_esb()
        self.common_send_msg = self.generate_data_api(
            method="POST",
            url="send_msg/",
            description=_("通用消息发送"),
        )
        self.get_msg_type = self.generate_data_api(
            method="GET",
            url="get_msg_type/" if self.is_esb else "channels/",
            description=_("查询通知类型"),
        )
        self.send_voice = self.generate_data_api(
            method="POST",
            url="send_voice/",
            description=_("语音通知"),
        )
        self.send_sms = self.generate_data_api(
            method="POST",
            url="send_sms/",
            description=_("短信通知"),
        )
        self.send_weixin = self.generate_data_api(
            method="POST",
            url="send_weixin/",
            description=_("微信通知"),
        )
        self.send_mail = self.generate_data_api(
            method="POST",
            url="send_mail/",
            description=_("邮件通知"),
        )

    def get_msg_map(self):
        return {msg_type: getattr(self, method_name) for msg_type, method_name in self.MSG_TYPE_MAP.items()}

    def send_msg(self, params):
        if self.is_esb:
            return self.common_send_msg(params)
        msg_type = params.pop("msg_type")
        if not msg_type:
            raise (_("消息类型(msg_type)不能为空"))

        msg_map = self.get_msg_map()
        if msg_type not in msg_map:
            raise (_("不支持的消息类型: {}").format(msg_type))
        return msg_map[msg_type](params)


CmsiApi = _CmsiApi()
