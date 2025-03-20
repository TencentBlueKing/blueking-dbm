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

from django.utils.translation import ugettext as _

from backend.ticket.constants import TicketType

logger = logging.getLogger("flow")

# 初始化处理函数映射表
TICKET_TYPE_HANDLERS = {}


def create_ticket_handler(ticket_type: TicketType):
    """处理函数注册装饰器"""

    def decorator(func):
        # 统一转换为小写作为键
        key = ticket_type.lower()
        # 防止重复注册
        if key in TICKET_TYPE_HANDLERS:
            raise ValueError(_("重复注册的单据类型: {}".format(ticket_type)))
        # 注册到处理函数映射表
        TICKET_TYPE_HANDLERS[key] = func
        return func

    return decorator


def call_ticket_handler(ticket_type, **kwargs):
    """
    运行对应的单据类型
    @param ticket_type: 票据类型（不区分大小写）
    @param kwargs: 参数字典（需包含对应函数需要的参数）
    """
    handler = TICKET_TYPE_HANDLERS.get(ticket_type.lower())

    if not handler:
        logger.info(_("该单据类型未注册：{}, 不执行".format(ticket_type)))
        return

    # 动态调用处理函数并解参
    return handler(**kwargs)
