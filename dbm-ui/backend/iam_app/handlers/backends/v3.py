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

import logging
from collections import defaultdict
from typing import Any, Dict, List, Tuple, Union

from iam import ObjectSet, Request, Resource, Subject, make_expression

from backend import env
from backend.iam_app.dataclass.actions import ActionMeta
from backend.iam_app.dataclass.resources import ResourceEnum
from backend.iam_app.handlers.backends.base import IAMBackend

logger = logging.getLogger("root")

# 已授权过的资源属性。属性授权是一条规则覆盖创建者名下所有同类资源，无需按实例重复授权
_granted_resource_attrs: Dict[str, List[Tuple]] = defaultdict(list)


class IAMV3Backend(IAMBackend):
    """基于 bk-iam SDK 的 V3 鉴权后端"""

    # 资源实例的专用字段，不参与属性授权的规则
    EXCLUDED_GRANT_ATTRS = ["_bk_iam_path_", "id", "name"]

    def __init__(self, iam_client):
        self.iam = iam_client

    def make_request(self, username: str, action: ActionMeta, resources: List[Resource]) -> Request:
        return Request(
            system=env.BK_IAM_SYSTEM_ID,
            subject=Subject("user", username),
            action=action,
            resources=resources,
            environment=None,
        )

    def is_allowed(self, username: str, action: ActionMeta, resources: List[Resource]) -> bool:
        request = self.make_request(username, action, resources)
        return bool(self.call_with_retry(self.iam.is_allowed, request, default=False))

    def policy_query(self, username: str, action: ActionMeta, obj_list: List[Union[int, str]]) -> List:
        """V3拉取动作的策略表达式，在本地对每个对象逐一求值"""
        request = self.make_request(username, action, resources=None)
        policies = self.call_with_retry(self.iam._do_policy_query, request, default=None)
        if not policies:
            return []

        expression = make_expression(policies)
        allowed_objs = []
        for obj in obj_list:
            iam_obj = ObjectSet()
            iam_obj.add_object(ResourceEnum.BUSINESS.id, {"id": str(obj)})
            if self.iam._eval_expr(expression, iam_obj):
                allowed_objs.append(obj)
        return allowed_objs

    def grant_creator_actions(self, resource: Resource, creator: str) -> Any:
        """
        V3走属性授权：为 creator=xxx 这条规则授权，一次授权即覆盖该创建者名下所有同类资源，
        因此相同的属性组合只需要授权一次
        """
        attributes = {
            attr_id: value
            for attr_id, value in (resource.attribute or {}).items()
            if attr_id not in self.EXCLUDED_GRANT_ATTRS
        }
        attr_tuple = tuple(sorted(attributes.values()))
        if attr_tuple in _granted_resource_attrs[resource.type]:
            return None

        application = {
            "system": resource.system,
            "type": resource.type,
            "creator": creator,
            "attributes": [
                {"id": attr_id, "name": attr_id, "values": [{"id": value, "name": value}]}
                for attr_id, value in attributes.items()
            ],
        }
        try:
            result = self.iam.grant_resource_creator_action_attributes(application)
            _granted_resource_attrs[resource.type].append(attr_tuple)
            logger.info("[grant_creator_actions] success, resource: %s, result: %s", resource.to_dict(), result)
            return result
        except Exception as e:  # pylint: disable=broad-except
            logger.exception("[grant_creator_actions] failed, resource: %s, error: %s", resource.to_dict(), e)
            return None
