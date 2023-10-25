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
import json
from collections import defaultdict
from typing import Any, Dict, List

from django.utils.translation import ugettext as _

from ...env import BK_IAM_SYSTEM_ID
from .actions import _all_actions
from .resources import ResourceEnum, _all_resources, _extra_instance_selections

IAM_SYSTEM_DEFINITION = {
    "operation": "upsert_system",
    "data": {
        "id": "bk_dbm",
        "name": "数据库管理",
        "name_en": "BK-DBM",
        "description": "数据库管理",
        "description_en": "BK-DBM",
        "clients": "bk_dbm,bk-dbm",
        "provider_config": {"host": "", "auth": "basic"},
    },
}


def generate_iam_migration_json():
    """
    根据dataclass的定义自动生成操作，操作组，资源和实例视图的json文件
    """
    iam_actions: List[Dict] = []
    iam_resources: List[Dict] = []
    iam_instance_selection: List[Dict] = []
    action_group_content: Dict[str, Any] = defaultdict(lambda: defaultdict(list))
    resource_creator_actions: Dict[str, List] = defaultdict(list)

    # 获取资源的json内容
    for resource in _all_resources.values():
        if resource.system_id != BK_IAM_SYSTEM_ID:
            continue

        iam_resources.append(resource.to_json())
        # 顺便获取实例视图的信息
        if getattr(resource, "resource_type_chain", None):
            chain = resource.resource_type_chain()
        else:
            chain, self_resource = [], resource
            while self_resource:
                chain.append({"system_id": self_resource.system_id, "id": self_resource.id})
                self_resource = self_resource.parent
            chain.reverse()
        iam_instance_selection.append(
            {
                "id": f"{resource.id}_list",
                "name": _("{} 列表".format(resource.name)),
                "name_en": f"{resource.id} list",
                "resource_type_chain": chain,
            }
        )

    # 补充资源的额外实例视图
    for resource in _extra_instance_selections:
        iam_instance_selection.append(resource.instance_selection())

    # 获取动作的json内容
    for action in _all_actions.values():
        iam_actions.append(action.to_json())
        # 顺便获取操作组的信息
        if action.subgroup:
            action_group_content[action.group][action.subgroup].append(action.id)
        elif action.group:
            action_group_content[action.group]["actions"].append(action.id)
        # 顺便获取资源关联操作，用于创建自动授权
        for related_resource in action.related_resource_types:
            # 不关联跨系统和特殊资源(dbtype)
            if related_resource.system_id != BK_IAM_SYSTEM_ID:
                continue
            if related_resource in [ResourceEnum.DBTYPE]:
                continue
            resource_creator_actions[related_resource.id].append(action.id)

    # 获取动作操作组的json内容
    iam_action_group = []
    for name, group in action_group_content.items():
        group_info = {
            "name": name,
            "name_en": name,
            "actions": [{"id": action} for action in group["actions"]],
            "sub_groups": [
                {"name": sub_name, "name_en": sub_name, "actions": [{"id": sub_action} for sub_action in sub_group]}
                for sub_name, sub_group in group.items()
                if sub_name != "actions"
            ],
        }
        iam_action_group.append(group_info)

    # 获取关联配置
    iam_resource_creator_actions = {
        "config": [
            {"id": res, "actions": [{"id": act, "required": True} for act in acts]}
            for res, acts in resource_creator_actions.items()
        ]
    }

    # 导出资源，动作，实例视图和操作组的json内容
    iam_json_content: List[Dict[str, Any]] = []
    # 导出 system定义
    iam_json_content.extend([IAM_SYSTEM_DEFINITION])
    # 导出 资源定义
    iam_json_content.extend([{"operation": "upsert_resource_type", "data": data} for data in iam_resources])
    # 导出 实例视图定义
    iam_json_content.extend(
        [{"operation": "upsert_instance_selection", "data": data} for data in iam_instance_selection]
    )
    # 导出 动作定义
    iam_json_content.extend([{"operation": "upsert_action", "data": data} for data in iam_actions])
    # 导出 动作管理组定义
    iam_json_content.append({"operation": "upsert_action_groups", "data": [data for data in iam_action_group]})
    # 导出 资源创建联动动作定义
    iam_json_content.append({"operation": "upsert_resource_creator_actions", "data": iam_resource_creator_actions})

    iam_migrate_json_path = "backend/iam_app/migration_json_files/initial—tmp.json"
    with open(iam_migrate_json_path, "w+") as f:
        f.write(json.dumps(iam_json_content, ensure_ascii=False, indent=4))
