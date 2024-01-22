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
import copy
import logging
from typing import Any, Dict

from backend.components import CmsiApi
from backend.configuration.constants import SystemSettingsEnum
from backend.configuration.models import SystemSettings
from backend.exceptions import ApiError

logger = logging.getLogger("root")


class CmsiHandler:
    """Cmsi发送信息常用处理函数"""

    @classmethod
    def send_msg(cls, msg: Dict[str, Any]):
        """发送信息，msg的定义和cmsi的send_msg所需内容一致，不过type可以多选，即一次性发送多个类型的信息"""
        support_msg_types = [s["type"] for s in CmsiApi.get_msg_type()]
        send_msg_types = msg.pop("msg_type", None) or SystemSettings.get_setting_value(
            key=SystemSettingsEnum.SYSTEM_MSG_TYPE.value, default=["weixin", "mail"]
        )
        for msg_type in send_msg_types:
            msg_info = {"msg_type": msg_type, **copy.deepcopy(msg)}
            # 如果是不支持的类型，则跳过
            if msg_type not in support_msg_types:
                continue
            # 如果是机器人，则将发送内容放在wecom_robot下
            if msg_type == CmsiApi.MsgType.WECOM_ROBOT:
                msg_info["wecom_robot"] = {
                    "type": "text",
                    "text": {"content": msg_info["content"]},
                    "receiver": msg_info["receiver__username"].split(","),
                    "group_receiver": msg_info["group_receiver"],
                }
            # 推送消息
            try:
                CmsiApi.send_msg(msg_info)
            except ApiError as err:
                logger.error(f"send message error, msg: {msg_info}, err:{err}")
