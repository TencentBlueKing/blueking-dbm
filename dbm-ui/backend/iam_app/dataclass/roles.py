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

from dataclasses import dataclass
from typing import Dict, List

from django.utils.translation import gettext as _

from backend.iam_app.constans import RoleActionLabel
from backend.iam_app.dataclass.actions import ActionMeta, _all_actions


@dataclass
class RoleMeta:
    """
    IAM V4 角色定义。

    V4 用角色承载了V3的常用操作(common_actions)、操作依赖(related_actions)和用户组授权三类语义，
    用户在IAM上申请的是角色而非单个操作。角色的动作统一由 RoleActionLabel 标签圈定。
    """

    label: RoleActionLabel
    description: str = ""

    @property
    def id(self) -> str:
        return self.label.value

    @property
    def name(self) -> str:
        return str(RoleActionLabel.get_choice_label(self.label))

    def get_actions(self) -> List[ActionMeta]:
        """角色包含的动作，未同步到V4的动作不纳入"""
        return [
            action
            for action in _all_actions.values()
            if not action.is_disabled_v4() and self.label in action.role_labels_v4
        ]

    def to_json_v4(self) -> Dict:
        # 角色内动作的授权维度只能是动作自身关联的资源类型，不能填祖先，无关资源的动作则为空
        actions = [
            {"id": action.id, "resource_type_id": action.to_json_v4()["resource_type_id"]}
            for action in self.get_actions()
        ]
        return {
            "id": self.id,
            "name": self.name,
            "description": str(self.description or self.name),
            "actions": actions,
        }


class RoleEnum:
    """role 枚举类"""

    BIZ_READ_ONLY = RoleMeta(RoleActionLabel.BIZ_READ_ONLY, _("业务下各集群的查看权限"))
    RESOURCE_MANAGE = RoleMeta(RoleActionLabel.RESOURCE_MANAGE, _("资源池、资源规格与标签的管理权限"))

    # 创建者角色，资源创建后由 ResourceMeta.creator_role_v4 指向并授予创建者
    MYSQL_CREATOR = RoleMeta(RoleActionLabel.MYSQL_CREATOR, _("对自己创建的MySQL集群的管理权限"))


# 角色的动作列表不允许为空，无动作的角色不注册到IAM
_all_roles = {
    role.id: role for role in RoleEnum.__dict__.values() if isinstance(role, RoleMeta) and role.get_actions()
}
