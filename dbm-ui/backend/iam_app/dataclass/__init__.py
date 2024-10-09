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
import logging
import os
import re
import time
from collections import defaultdict
from typing import Any, Dict, List

from django.conf import settings
from django.utils.translation import ugettext as _

from backend import env
from backend.db_meta.models import AppCache

from ..constans import CommonActionLabel
from ..exceptions import BaseIAMError
from ..handlers.client import IAM
from ..handlers.permission import Permission
from .actions import _all_actions
from .resources import ResourceEnum, ResourceMeta, _all_resources, _extra_instance_selections

logger = logging.getLogger("root")

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


def generate_iam_migration_json(json_name: str = ""):
    """
    根据dataclass的定义自动生成操作，操作组，资源和实例视图的json文件
    """
    iam_actions: List[Dict] = []
    iam_resources: List[Dict] = []
    iam_instance_selection: List[Dict] = []
    action_group_content: Dict[str, Any] = defaultdict(lambda: defaultdict(list))
    common_actions_content: Dict[str, List] = defaultdict(list)
    resource_creator_actions: Dict[str, List] = defaultdict(list)

    # 获取资源的json内容
    for resource in _all_resources.values():
        if resource.system_id != env.BK_IAM_SYSTEM_ID:
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
        # 顺便获取常用操作分类信息
        for label in action.common_labels:
            common_actions_content[label].append(action.id)
        # 顺便获取资源关联操作，用于创建自动授权。目前仅支持动作关联一种资源
        if len(action.related_resource_types) != 1:
            continue
        related_resource = action.related_resource_types[0]
        # 不关联跨系统和特殊资源(dbtype)
        if related_resource.system_id != env.BK_IAM_SYSTEM_ID:
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

    # 获取常用动作的json内容
    iam_common_actions = []
    for label, common_actions in common_actions_content.items():
        common_info = {
            "name": CommonActionLabel.get_choice_label(label),
            "name_en": label,
            "actions": [{"id": id} for id in common_actions],
        }
        iam_common_actions.append(common_info)

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
    iam_json_content.append({"operation": "upsert_action_groups", "data": iam_action_group})
    # 导出 常用操作配置定义
    iam_json_content.append({"operation": "upsert_common_actions", "data": iam_common_actions})
    # 导出 资源创建联动动作定义
    iam_json_content.append({"operation": "upsert_resource_creator_actions", "data": iam_resource_creator_actions})

    # 获取dbm在iam完整的注册json
    dbm_iam_json = {"system_id": env.BK_IAM_SYSTEM_ID, "operations": iam_json_content}

    json_name = json_name or "initial—tmp.json"
    iam_migrate_json_path = os.path.join(settings.BASE_DIR, f"backend/iam_app/migration_json_files/{json_name}")
    with open(iam_migrate_json_path, "w+") as f:
        f.write(json.dumps(dbm_iam_json, ensure_ascii=False, indent=4))


def generate_resource_topo_auth(res_actions: list, bk_biz_id: int = None, bk_biz_name=None):
    bk_biz_id = bk_biz_id or "{{biz_id}}"
    bk_biz_name = bk_biz_name or "{{biz_name}}"

    def get_resource_path_info(resource: ResourceMeta):
        if ResourceEnum.BUSINESS not in [resource, resource.parent]:
            paths = []
        else:
            paths = [[{"system": "bk_cmdb", "type": "biz", "id": bk_biz_id, "name": bk_biz_name}]]
        return {"system": resource.system_id, "type": resource.id, "paths": paths}

    resources__actions_map: Dict[str, List[str]] = defaultdict(list)
    resource_topo_auth_content: List[Dict[str, Any]] = []

    # 聚合相同资源的动作
    for action in res_actions:
        resource_ids = ",".join([resource.id for resource in action.related_resource_types])
        resources__actions_map[resource_ids].append(action.id)

    # 对每种聚合的资源生成迁移json，其中resource的path规则:
    # 1. 资源本身或者父类包含biz，则path固定为:
    # [{"system": "bk_cmdb", "type": "biz", "id": "{{biz_id}}", "name": "{{biz_name}}"}] --> 业务顶层
    # 2. 资源不包含父类，则固定为[] --> 即无限制
    for resource_ids, action_ids in resources__actions_map.items():
        # 生成resource的迁移信息
        resource_metas = [ResourceEnum.get_resource_by_id(id) for id in resource_ids.split(",")]
        resource_infos = [get_resource_path_info(resource) for resource in resource_metas]
        # 生成action的迁移信息
        action_infos = [{"id": id} for id in action_ids]
        resource_topo_auth_content.append(
            {"system": env.BK_IAM_SYSTEM_ID, "actions": action_infos, "resources": resource_infos}
        )

    return resource_topo_auth_content


def generate_iam_biz_maintain_json(label: str = CommonActionLabel.BIZ_MAINTAIN, json_name: str = ""):
    """
    根据dataclass的定义自动生成业务运维的用户组迁移json
    """
    res_actions = [action for action in _all_actions.values() if label in action.common_labels]
    biz_maintain_migrate_content = generate_resource_topo_auth(res_actions)

    # 生成json文件
    json_name = json_name or "biz_maintain_migrate.json"
    migrate_json_path = os.path.join(settings.BASE_DIR, f"backend/iam_app/migration_json_files/{json_name}")
    with open(migrate_json_path, "w+") as f:
        f.write(json.dumps(biz_maintain_migrate_content, ensure_ascii=False, indent=4))


def assign_auth_to_group(iam: IAM, biz: AppCache, group_id):
    """
    给单个用户组分配权限，这里的权限固定是DBA权限
    """
    biz_actions = [action for action in _all_actions.values() if action.group not in [_("全局设置"), _("资源管理")]]
    auth_contents = generate_resource_topo_auth(biz_actions, bk_biz_id=biz.bk_biz_id, bk_biz_name=biz.bk_biz_name)
    for auth_info in auth_contents:
        ok, message, data = iam._client.grant_user_group_actions(env.BK_IAM_SYSTEM_ID, group_id, data=auth_info)
        if not ok:
            raise BaseIAMError(_("用户组添加授权失败，错误信息: {}").format(message))


def assign_auth_to_dba(bk_biz_id: int, group_name: str, members: list):
    """
    给DBA分配iam权限，具体是：
    创建用户组 ---> 给用户组分配权限 ---> 成员加入用户组
    """
    biz = AppCache.objects.get(bk_biz_id=bk_biz_id)
    manager_id = env.BK_IAM_GRADE_MANAGER_ID
    iam = Permission.get_iam_client()

    # 创建用户组
    group_name = group_name or f"{biz.bk_biz_name}_DBA(#{biz.bk_biz_id})"
    group_data = {"groups": [{"name": group_name, "description": group_name}]}
    ok, message, data = iam._client.create_user_groups(env.BK_IAM_SYSTEM_ID, manager_id, data=group_data)
    if not ok:
        raise BaseIAMError(_("创建用户组失败，错误信息: {}").format(message))

    # 对用户组分配权限，动作不包含资源管理和全局设置
    group_id = data[0]
    assign_auth_to_group(iam, biz, data[0])

    # 对用户组添加成员，默认过期时间是1年
    expired_at = int(time.time() + 60 * 60 * 24 * 30 * 12)
    members = [{"type": "user", "id": member} for member in members]
    add_members_data = {"members": members, "expired_at": expired_at}
    ok, message, data = iam._client.add_user_group_members(env.BK_IAM_SYSTEM_ID, group_id, data=add_members_data)
    if not ok:
        raise BaseIAMError(_("用户组添加成员{}失败，错误信息: {}").format(members, message))


def flush_groups_auth():
    """
    刷新存量用户组权限
    """
    iam = Permission.get_iam_client()
    manager_id = env.BK_IAM_GRADE_MANAGER_ID

    # 查询包含DBA名称的用户组，默认不超过500
    params = {"name": "DBA", "page_size": 500, "page": 1}
    ok, message, data = iam._client.query_user_groups(env.BK_IAM_SYSTEM_ID, manager_id, data=params)
    if not ok:
        raise BaseIAMError(_("用户组查询失败，错误信息: {}").format(message))
    # 匹配{biz_name}_DBA(#{biz_id})这样格式的用户组
    dba_group_pattern = re.compile(r"^.*?_DBA\(#[0-9]*\)$")
    dba_groups = [group for group in data["results"] if dba_group_pattern.match(group["name"])]

    # 刷新权限
    for group in dba_groups:
        try:
            # 提取用户组ID和业务
            group_id, name = group["id"], group["name"]
            biz = AppCache.objects.get(bk_biz_name=name.split("_DBA")[0])
            # 分配权限
            assign_auth_to_group(iam, biz, group_id)
        except Exception as e:
            raise BaseIAMError(_("用户组{}刷新失败，错误信息:{}").format(group, e))
