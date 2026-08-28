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
import time
from typing import Any, Dict, List, Union

from iam import Resource
from iam.eval.constants import KEYWORD_BK_IAM_PATH

from backend import env
from backend.components.iamv4.client import AUTH_BATCH_SIZE, AUTHORIZATION_EXPIRED_DAYS, IAMV4Api
from backend.iam_app.dataclass.actions import ActionEnum, ActionMeta
from backend.iam_app.dataclass.resources import ResourceEnum
from backend.iam_app.handlers.backends.base import IAMBackend
from backend.utils.basic import chunk_lists

logger = logging.getLogger("root")


class IAMV4Backend(IAMBackend):
    """基于 IAMV4Api 的 V4 鉴权后端"""

    # 资源实例ID为该值时表示这一资源类型的无限制授权
    ANY_RESOURCE_ID = "*"

    @staticmethod
    def make_resource(action: ActionMeta, resources: List[Resource]) -> Union[Dict, None]:
        """
        构造V4的鉴权资源。V4一个动作只关联一个资源类型，具体取哪个由资源类型自己决定：
        默认按类型匹配，业务DB类型这类合成资源则由业务与DB类型两个实例拼出
        """
        resource_type = action.get_related_resource_type_v4()
        if not resource_type or not resources:
            return None

        resource = resource_type.make_resource_v4(resources)
        if not resource:
            logger.warning("[iam_v4] action(%s) expects resource(%s) but not given", action.id, resource_type.id)
            return None

        auth_resource = {"id": str(resource.id)}
        bk_iam_path = (resource.attribute or {}).get(KEYWORD_BK_IAM_PATH)
        if bk_iam_path:
            auth_resource["attributes"] = {KEYWORD_BK_IAM_PATH: bk_iam_path}
        return auth_resource

    @staticmethod
    def get_ancestors(resource: Resource):
        # _bk_iam_path_ 只包含祖先链(从根到直接父级)，不含自身，直接按段解析即可
        bk_iam_path = (resource.attribute or {}).get(KEYWORD_BK_IAM_PATH, "/")
        ancestors = []
        for topo in bk_iam_path.split("/")[1:-1]:
            rtype, rid = topo.split(",")
            ancestors.append(
                {
                    "id": rid,
                    "type": rtype,
                }
            )
        return ancestors

    def is_allowed(self, username: str, action: ActionMeta, resources: List[Resource]) -> bool:
        # TODO: 这些动作的资源存在多平行父级，暂未注册到V4(见06文档B1)，先放行，待IAM支持拓扑后移除
        if action.is_disabled_v4():
            logger.warning("[iam_v4] action(%s) is not registered in V4, allowed by default", action.id)
            return True

        params = {"subject": {"type": "user", "id": username}, "action_id": action.id}
        # 无关资源类型的动作不传resource
        auth_resource = self.make_resource(action, resources)
        if auth_resource:
            params["resource"] = auth_resource

        data = self.call_with_retry(IAMV4Api.direct_auth, params=params, default=None)
        return bool((data or {}).get("allowed"))

    def policy_query(self, username: str, action: ActionMeta, obj_list: List[Union[int, str]]) -> List:
        """
        V4没有策略表达式，改为查出用户在该动作下有权限的资源实例，再与待判定的对象求交。
        仅支持顶层资源类型，DBM当前的调用都是业务维度
        """
        resource_type = action.get_related_resource_type_v4()
        if not resource_type:
            return []

        params = {"subject": {"type": "user", "id": username}, "action_id": action.id}
        # TODO: 该接口的分页与返回上限尚未明确(见06文档B2)，此处按无上限处理。
        #  若IAM侧存在默认截断，会表现为部分有权限的实例被判定为无权限
        authorized_resources = self.call_with_retry(IAMV4Api.list_authorized_resource, params=params, default=None)
        if not authorized_resources:
            return []

        # 接口一次返回该动作下所有资源类型的授权，取动作关联的那个
        allowed_ids = set()
        for item in authorized_resources:
            if item.get("type") == resource_type.id:
                allowed_ids.update(item.get("ids") or [])

        if self.ANY_RESOURCE_ID in allowed_ids:
            return list(obj_list)

        # 接口返回的实例ID是字符串，而调用方传入的可能是整型，按字符串比对但返回原始对象
        return [obj for obj in obj_list if str(obj) in allowed_ids]

    def grant_creator_actions(self, resource: Resource, creator: str) -> Any:
        """
        V4没有属性授权，改为把创建者授予该资源类型的创建者角色 + 该实例。
        未声明创建者角色的资源不做授权
        """
        creator_role = ResourceEnum.get_resource_by_id(resource.type).creator_role_v4
        if not creator_role:
            return None

        authorization = {
            "subject": {"type": "user", "id": creator},
            "role_id": creator_role,
            "related_resource_type_id": resource.type,
            "resources": [{"type": resource.type, "id": str(resource.id)}],
            "expired_at": int(time.time()) + AUTHORIZATION_EXPIRED_DAYS * 24 * 3600,
        }
        # 授权接口要求带上操作人。授权失败不重试，避免重复授权，也不影响资源创建的主流程
        try:
            result = IAMV4Api.add_authorization(params=[authorization], headers={"X-Bkiam-Operator": creator})
            logger.info("[grant_creator_actions] success, resource: %s, result: %s", resource.to_dict(), result)
            return result
        except Exception as e:  # pylint: disable=broad-except
            logger.exception("[grant_creator_actions] failed, resource: %s, error: %s", resource.to_dict(), e)
            return None

    def multi_actions_is_allowed(
        self, username: str, actions: List[Union[ActionMeta, str]], resources: List[Resource]
    ):
        result = {}
        not_disabled_v4_list = []
        for action in actions:
            if action.is_disabled_v4():
                logger.warning("[iam_v4] action(%s) is not registered in V4, allowed by default", action.id)
                result[action.id] = True
            else:
                not_disabled_v4_list.append(action)
        if not not_disabled_v4_list:
            return result

        subject = {"type": "user", "id": username}
        # 预置为无权限，请求失败或响应缺项时直接沿用
        result.update({action.id: False for action in not_disabled_v4_list})
        # 复用逐个资源对一批动作鉴权的逻辑
        for _, action_id, allowed in self._auth_by_actions(subject, not_disabled_v4_list, [resources]):
            result[action_id] = allowed

        return result

    def batch_is_allowed(
        self, username: str, actions: List[Union[ActionMeta, str]], resources_list: List[List[Resource]]
    ):
        subject = {"type": "user", "id": username}
        # 预置为无权限，请求失败或响应缺项时直接沿用
        result = {str(resources[0].id): {action.id: False for action in actions} for resources in resources_list}
        # 择数量少的一方做外层循环，另一方分片，请求数取决于少的那边
        if len(actions) > len(resources_list):
            auth_results = self._auth_by_actions(subject, actions, resources_list)
        else:
            auth_results = self._auth_by_resources(subject, actions, resources_list)

        for resource_id, action_id, allowed in auth_results:
            result[resource_id][action_id] = allowed
        return result

    def _auth_by_actions(self, subject, actions, resources_list):
        """逐个资源对一批动作鉴权，产出 (资源ID, 动作ID, 是否有权限)"""
        for resources in resources_list:
            resource = self.make_resource(actions[0], resources)
            for chunk in chunk_lists(actions, AUTH_BATCH_SIZE):
                params = {"subject": subject, "action_ids": [action.id for action in chunk]}
                # 动作不关联资源时不传，否则IAM会按资源维度校验
                if resource:
                    params["resource"] = resource
                data = self.call_with_retry(IAMV4Api.direct_auth_by_actions, params=params, default=[])
                for item in data:
                    yield str(resources[0].id), item["action_id"], item["allowed"]

    def _auth_by_resources(self, subject, actions, resources_list):
        """逐个动作对一批资源鉴权，产出 (资源ID, 动作ID, 是否有权限)"""
        for action in actions:
            for chunk in chunk_lists(resources_list, AUTH_BATCH_SIZE):
                resources = [self.make_resource(action, item) for item in chunk]
                params = {
                    "subject": subject,
                    "action_id": action.id,
                    "resources": [resource for resource in resources if resource],
                }
                data = self.call_with_retry(IAMV4Api.direct_auth_by_resources, params=params, default=[])
                for item in data:
                    yield str(item["resource_id"]), action.id, item["allowed"]

    def get_apply_url(
        self, action_ids: List[str], resources_list: List[List[Resource]] = None, system_id: str = env.BK_IAM_SYSTEM_ID
    ):
        params = {"system_id": system_id, "permissions": []}
        for action_id in action_ids:
            resource_info = []
            action = ActionEnum.get_action_by_id(action_id)
            action_id = action.id
            for resource in resources_list:
                if not resource:
                    continue
                ancestors = self.get_ancestors(resource[0])
                resource_info.append(
                    {
                        "id": resource[0].id,
                        "type": resource[0].type,
                        "ancestors": ancestors,
                    }
                )
            params["permissions"].append(
                {
                    "action_id": action_id,
                    "resources": resource_info,
                }
            )
        data = self.call_with_retry(IAMV4Api.generate_perm_apply_url, params=params, default={})
        return data.get("url", "")

    def get_system_info(self):
        params = {"fields": "system_info,resource_types,actions"}
        data = self.call_with_retry(IAMV4Api.share_retrieve_system, params=params, default={})
        return data
