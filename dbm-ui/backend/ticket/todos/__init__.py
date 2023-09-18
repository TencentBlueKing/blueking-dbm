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
import importlib
import logging
import os
from dataclasses import asdict, dataclass
from typing import Callable

from blue_krill.data_types.enum import EnumField, StructuredEnum
from django.utils.translation import ugettext_lazy as _

from backend.ticket.models import Todo

logger = logging.getLogger("root")


class TodoActor:
    """
    待办执行器
    """

    todo_type = None

    def __init__(self, todo: Todo):
        self.todo = todo
        self.context = todo.context

    @classmethod
    def name(cls):
        return cls.__name__

    def process(self, username, action, params):
        """处理操作"""
        raise NotImplementedError


class TodoActorFactory:
    """待办执行器工厂"""

    registry = {}

    @classmethod
    def register(cls, todo_type: str) -> Callable:
        def inner_wrapper(wrapped_class: TodoActor) -> TodoActor:
            if todo_type in cls.registry:
                logger.warning(f"Processor [{todo_type}] already exists. Will replace it")
            cls.registry[todo_type] = wrapped_class
            return wrapped_class

        return inner_wrapper

    @classmethod
    def actor_cls(cls, todo_type: str):
        """获取构造器类"""
        if todo_type not in cls.registry:
            logger.warning(f"Todo Type: [{todo_type}] does not exist in the registry")
            raise NotImplementedError

        return cls.registry[todo_type]

    @classmethod
    def actor(cls, todo: Todo) -> TodoActor:
        """创建构造器实例"""
        todo_cls = cls.actor_cls(todo.type)
        return todo_cls(todo)


def register_all_todos(path=os.path.dirname(__file__), module_path="backend.ticket.todos"):
    """递归注册当前目录下所有的todo处理器"""
    for name in os.listdir(path):
        # 忽略无效文件
        if name.endswith(".pyc") or name in ["__init__.py", "__pycache__"]:
            continue

        if os.path.isdir(os.path.join(path, name)):
            register_all_todos(os.path.join(path, name), ".".join([module_path, name]))
        else:
            try:
                module_name = name.replace(".py", "")
                import_path = ".".join([module_path, module_name])
                importlib.import_module(import_path)
            except ModuleNotFoundError as e:
                logger.warning(e)


class ActionType(str, StructuredEnum):
    """
    待办操作类型
    """

    APPROVE = EnumField("APPROVE", _("确认执行"))
    TERMINATE = EnumField("TERMINATE", _("终止单据"))
    RESOURCE_REAPPLY = EnumField("RESOURCE_REAPPLY", _("资源重新申请"))


@dataclass
class BaseTodoContext:
    flow_id: int
    ticket_id: int

    def to_dict(self):
        return asdict(self)
