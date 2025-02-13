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

from blueapps.account.models import User
from django.utils.translation import ugettext_lazy as _

from backend.constants import DEFAULT_SYSTEM_USER
from backend.ticket.constants import TODO_RUNNING_STATUS
from backend.ticket.exceptions import TodoDuplicateProcessException, TodoWrongOperatorException
from backend.ticket.models import Todo
from backend.utils.register import re_import_modules
from blue_krill.data_types.enum import EnumField, StructuredEnum

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

    def update_context(self, params):
        # 更新上下文信息
        if "remark" in params:
            self.todo.context.update(remark=params["remark"])
        self.todo.save(update_fields=["context"])

    @property
    def allow_superuser_process(self):
        # 是否允许超管操作，默认允许.
        return True

    def process(self, username, action, params):
        # 当状态已经被确认，则不允许重复操作
        if self.todo.status not in TODO_RUNNING_STATUS:
            raise TodoDuplicateProcessException(_("当前代办操作已经处理，不能重复处理！"))

        # 允许系统内置用户确认
        if username == DEFAULT_SYSTEM_USER:
            self._process(username, action, params)
            return
        # 允许超级用户和操作人确认
        is_superuser = User.objects.get(username=username).is_superuser and self.allow_superuser_process
        if not is_superuser and username not in self.todo.operators + self.todo.helpers:
            raise TodoWrongOperatorException(_("{}不在处理人: {}中，无法处理").format(username, self.todo.operators))

        # 执行确认操作
        self._process(username, action, params)
        self.update_context(params)

    def _process(self, username, action, params):
        """处理操作的具体实现"""
        raise NotImplementedError

    def deliver(self, username, action, params):
        """当前用户分派给其他指定用户"""
        processors, remark = params["processors"], params["remark"]

        # 剔除当前用户，并追加后续分派用户
        if username in self.todo.helpers:
            self.todo.helpers.remove(username)
            self.todo.helpers.extend(processors)
        elif username in self.todo.operators:
            self.todo.operators.remove(username)
            self.todo.operators.extend(processors)
        else:
            raise TodoWrongOperatorException(_("{}不是处理人或者协助人，无法进行分派").format(username))

        self.todo.save()
        self._deliver(username, processors, remark)

    def _deliver(self, username, processors, remark):
        """额外的分派逻辑，由子类独立实现"""
        pass


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


def register_all_todos():
    re_import_modules(path=os.path.dirname(__file__), module_path="backend.ticket.todos")


class TodoActionType(str, StructuredEnum):
    """
    待办操作类型
    """

    APPROVE = EnumField("APPROVE", _("确认执行"))
    TERMINATE = EnumField("TERMINATE", _("终止单据"))
    DELIVER = EnumField("DELIVER", _("分派代办"))


@dataclass
class BaseTodoContext:
    flow_id: int
    ticket_id: int

    def to_dict(self):
        return asdict(self)
