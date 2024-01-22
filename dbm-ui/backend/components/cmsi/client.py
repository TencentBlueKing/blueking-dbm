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

from django.utils.translation import ugettext_lazy as _

from blue_krill.data_types.enum import EnumField, StructuredEnum

from ..base import BaseApi
from ..domains import CMSI_APIGW_DOMAIN


class _CmsiApi(BaseApi):
    MODULE = _("消息管理")
    BASE = CMSI_APIGW_DOMAIN

    class MsgType(str, StructuredEnum):
        SMS = EnumField("sms", _("短信"))
        WEIXIN = EnumField("weixin", _("微信"))
        MAIL = EnumField("mail", _("邮件"))
        VOICE = EnumField("voice", _("语音"))
        RTX = EnumField("rtx", _("企业微信"))
        WECOM_ROBOT = EnumField("wecom_robot", _("企业微信机器人"))

    def __init__(self):
        self.send_msg = self.generate_data_api(
            method="POST",
            url="send_msg/",
            description=_("通用消息发送"),
        )
        self.get_msg_type = self.generate_data_api(
            method="GET",
            url="get_msg_type/",
            description=_("查询通知类型"),
        )


CmsiApi = _CmsiApi()
