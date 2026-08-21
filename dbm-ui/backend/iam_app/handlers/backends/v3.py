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

from django.conf import settings
from django.utils.translation import gettext as _
from iam import MultiActionRequest, ObjectSet, Request, Resource, Subject, make_expression
from iam.apply.models import (
    ActionWithoutResources,
    ActionWithResources,
    Application,
    RelatedResourceType,
    ResourceInstance,
    ResourceNode,
)

from backend import env
from backend.iam_app.dataclass.actions import ActionEnum, ActionMeta
from backend.iam_app.dataclass.resources import ResourceEnum
from backend.iam_app.exceptions import ActionNotExistError, GetSystemInfoError
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

    def make_multi_request(
        self, username: str, actions: List[Union[ActionMeta, str]], resources: List[Resource] = None
    ) -> MultiActionRequest:
        resources = resources or []
        actions = [ActionEnum.get_action_by_id(action) for action in actions]
        multi_request = MultiActionRequest(
            system=env.BK_IAM_SYSTEM_ID,
            subject=Subject("user", username),
            actions=actions,
            resources=resources,
            environment=None,
        )

        return multi_request

    @classmethod
    def check_resource_is_local(cls, resources: List[Resource]) -> bool:
        """
        判断资源是否属于本系统
        """
        check_list = [resource.system == env.BK_IAM_SYSTEM_ID for resource in resources]
        return set(check_list) == {True}

    def _get_topo_resource(self, resource: Resource):
        """
        获取资源的拓扑信息资源
        """
        if not resource:
            return []

        bk_iam_path = f"{resource.attribute.get('_bk_iam_path_', '/')}{resource.type},{resource.id}/"
        topo_resources = []
        # 获取祖先的拓扑结构
        for topo in bk_iam_path.split("/")[1:-1][:-1]:
            rtype, rid = topo.split(",")
            topo_resources.append(ResourceEnum.get_resource_by_id(rtype).create_instance(rid))
        # 最后一级拓扑是自身
        topo_resources.append(resource)
        return topo_resources

    def make_application(
        self, action_ids: List[str], resources_list: List[List[Resource]] = None, system_id: str = env.BK_IAM_SYSTEM_ID
    ) -> Application:
        """
        构造Application，提供给get_apply_url参数
        :param action_ids: 动作列表id
        :param resources_list: 资源instance列表
        :param system_id: 系统ID
        """

        iam_actions: List[Union[ActionWithResources, ActionWithoutResources]] = []
        resources_list = resources_list or []

        for action_id in action_ids:
            related_resource_types = []
            try:
                action = ActionEnum.get_action_by_id(action_id)
                action_id = action.id
                related_resource_types = action.related_resource_types
            except ActionNotExistError:
                pass

            # 如果不存在related_resource_types, 则构造ActionWithoutResources
            if not related_resource_types:
                iam_actions.append(ActionWithoutResources(action_id))
                continue

            # 构造ActionWithResources
            iam_related_resources_types = []
            for index, resource_type in enumerate(related_resource_types):
                # 同一个资源类型可以包含多个资源
                instances = []
                for resources in resources_list:
                    resource = resources[index]
                    if resource.system != resource_type.system_id or resource.type != resource_type.id:
                        continue

                    # 补充资源的拓扑实例
                    resource_nodes = [
                        ResourceNode(r.type, r.id, r.attribute.get("name", r.id))
                        for r in self._get_topo_resource(resource)
                    ]
                    instances.append(ResourceInstance(resource_nodes))

                iam_related_resources_types.append(
                    RelatedResourceType(resource_type.system_id, resource_type.id, instances)
                )

            iam_actions.append(ActionWithResources(action_id, iam_related_resources_types))

        application = Application(system_id=system_id, actions=iam_actions)
        return application

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

    def multi_actions_is_allowed(
        self, username: str, actions: List[Union[ActionMeta, str]], resources: List[Resource]
    ):
        multi_request = self.make_multi_request(username, actions, resources)
        return self.call_with_retry(self.iam.resource_multi_actions_allowed, multi_request, default={})

    def batch_is_allowed(
        self, username: str, actions: List[Union[ActionMeta, str]], resources_list: List[List[Resource]]
    ):
        # TODO: 暂时屏蔽跨资源类型鉴权，SDK问题待排查
        if len(resources_list[0]) == 1 and self.check_resource_is_local(resources_list[0]):
            multi_request = self.make_multi_request(username, actions)
            batch_permission = self.call_with_retry(
                self.iam.batch_resource_multi_actions_allowed, multi_request, resources_list, default={}
            )
        # 如果资源不属于本系统，则只能单次调用allowed
        else:
            batch_permission = {}
            for index, resources in enumerate(resources_list):
                key = index if len(resources) > 1 else resources[0].id
                permission_info = self.multi_actions_is_allowed(username, actions, resources)
                if not permission_info:
                    permission_info = {action.id: False for action in actions}
                batch_permission[key] = permission_info
        return batch_permission

    def get_apply_url(
        self, action_ids: List[str], resources_list: List[List[Resource]] = None, system_id: str = env.BK_IAM_SYSTEM_ID
    ):
        application = self.make_application(action_ids, resources_list, system_id)
        # ok, message, url = self.iam.get_apply_url(application)
        ok, message, url = self.call_with_retry(self.iam.get_apply_url, application)
        if not ok:
            logger.error(f"iam generate apply url fail: {message}")
            return env.IAM_APP_URL

        return url

    def get_system_info(self):
        # ok, message, data = self._iam._client.query(settings.BK_IAM_SYSTEM_ID)
        ok, message, data = self.call_with_retry(self.iam._client.query, settings.BK_IAM_SYSTEM_ID)
        if not ok:
            raise GetSystemInfoError(_("获取系统信息错误：{message}").format(message))
        return data
