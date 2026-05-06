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
from typing import Type

from aidev_agent.services.command_handler import CommandHandler, CommandProcessor


def register_command(handler_class: Type[CommandHandler]) -> Type[CommandHandler]:
    """
    命令注册装饰器
    :param handler_class: 命令处理器类（必须有 command_name 属性）
    :return: 处理器类
    """
    # 检查类是否有 command_name 属性
    if not hasattr(handler_class, "command"):
        raise ValueError(f"Handler class {handler_class.__name__} must have 'command' attribute")

    # 检查名称不能有重复
    if handler_class.command in CommandProcessor._handlers:
        raise ValueError(f"Command {handler_class.command} already registered")

    # 注册到 CommandProcessor
    CommandProcessor.register_handler(handler_class.command, handler_class)
    return handler_class


command = register_command
