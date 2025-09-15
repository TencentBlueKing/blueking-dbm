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

"""
CMSI API Mock数据
用于测试通知相关功能
"""

# CMSI API 支持的消息类型
CMSI_MSG_TYPES = [
    {"type": "mail", "label": "邮件", "is_active": True},
    {"type": "sms", "label": "短信", "is_active": True},
    {"type": "voice", "label": "语音", "is_active": True},
    {"type": "weixin", "label": "微信", "is_active": True},
    {"type": "rtx", "label": "企微", "is_active": True},
    {"type": "wecom_robot", "label": "企微机器人", "is_active": True},
]

# CMSI API 发送消息成功响应
CMSI_SEND_MSG_SUCCESS_RESPONSE = {"result": True, "code": 0, "message": "success", "data": {"task_id": "12345"}}

# CMSI API 发送消息失败响应
CMSI_SEND_MSG_FAILURE_RESPONSE = {"result": False, "code": 1, "message": "发送失败", "data": None}
