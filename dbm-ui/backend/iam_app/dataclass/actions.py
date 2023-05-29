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
from dataclasses import asdict, dataclass
from typing import List, Union

from django.utils.translation import ugettext as _
from iam import Action

from backend.iam_app.dataclass.resources import ResourceEnum, ResourceMeta
from backend.iam_app.exceptions import ActionNotExistError


@dataclass
class ActionMeta(Action):
    """action 属性定义"""

    id: str
    name: str
    name_en: str
    type: str
    version: str
    related_resource_types: List[ResourceMeta] = None
    related_actions: List = None
    description: str = ""
    description_en: str = ""

    def __post_init__(self):
        super(ActionMeta, self).__init__(id=self.id)

    def to_json(self):
        return asdict(self)


class ActionEnum:
    """action 枚举类"""

    VIEW_BUSINESS = ActionMeta(
        id="view_business",
        name=_("业务访问"),
        name_en="View Business",
        type="view",
        version="1",
        related_actions=[],
        related_resource_types=[ResourceEnum.BUSINESS],
    )
    DB_MANAGE = ActionMeta(
        id="db_manage",
        name=_("数据库管理"),
        name_en="DB Manage",
        type="manage",
        version="1",
        related_actions=[],
        related_resource_types=[ResourceEnum.BUSINESS],
    )
    GLOBAL_MANAGE = ActionMeta(
        id="global_manage",
        name=_("平台管理"),
        name_en="Global Manage",
        type="manage",
        version="1",
        related_actions=[],
        related_resource_types=[],
    )

    @classmethod
    def get_action_by_id(cls, action_id: Union[(ActionMeta, str)]) -> ActionMeta:
        if isinstance(action_id, ActionMeta):
            return action_id
        if action_id not in cls.__dict__:
            raise ActionNotExistError(_("动作ID不存在: {}").format(action_id))
        return cls.__dict__[action_id]


_all_actions = {action.id: action for action in ActionEnum.__dict__.values() if isinstance(action, ActionMeta)}
