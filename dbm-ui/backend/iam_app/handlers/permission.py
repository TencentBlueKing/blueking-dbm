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

import itertools
import logging
from typing import Any, Dict, List, Tuple, Union

from blueapps.account.models import User
from django.conf import settings
from django.utils.translation import ugettext as _
from iam import IAM, DummyIAM, MultiActionRequest, ObjectSet, Request, Resource, Subject, make_expression
from iam.apply.models import (
    ActionWithoutResources,
    ActionWithResources,
    Application,
    RelatedResourceType,
    ResourceInstance,
    ResourceNode,
)
from iam.exceptions import AuthAPIError
from iam.meta import setup_action, setup_resource, setup_system
from iam.utils import gen_perms_apply_data

from backend import env
from backend.iam_app.dataclass.actions import ActionEnum, ActionMeta, _all_actions
from backend.iam_app.dataclass.resources import ResourceEnum, _all_resources
from backend.iam_app.exceptions import ActionNotExistError, GetSystemInfoError, PermissionDeniedError
from backend.utils.local import local

logger = logging.getLogger("root")


class Permission(object):
    """
    权限中心鉴权和无权限申请的通用封装
    """

    def __init__(self, username: str = "", request=None):
        if username:
            self.username = username
            self.bk_token = ""
        else:
            try:
                request = request or local.request
            except Exception:
                raise ValueError("must provide `username` or `request` param to init")

            self.bk_token = request.COOKIES.get("bk_token", "")
            self.username = request.user.username

        self._iam = self.get_iam_client()

    @classmethod
    def get_iam_client(cls):
        if env.BK_IAM_SKIP:
            return DummyIAM(env.APP_CODE, env.SECRET_KEY, env.BK_IAM_INNER_HOST, env.BK_COMPONENT_API_URL)

        return IAM(env.APP_CODE, env.SECRET_KEY, bk_apigateway_url=env.BK_IAM_APIGATEWAY)

    def get_system_info(self):
        """
        获取权限中心注册的动作列表
        """
        ok, message, data = self._iam._client.query(settings.BK_IAM_SYSTEM_ID)
        if not ok:
            raise GetSystemInfoError(_("获取系统信息错误：{message}").format(message))
        return data

    @classmethod
    def setup_meta(cls):
        """
        初始化权限中心实体, 构造meta信息
        """

        if getattr(cls, "__setup", False):
            return

        # 系统
        systems = [
            {"system_id": env.BK_IAM_SYSTEM_ID, "system_name": env.BK_IAM_SYSTEM_NAME},
            {"system_id": "bk_cmdb", "system_name": _("配置平台")},
        ]

        for system in systems:
            setup_system(**system)

        # 资源
        for r in _all_resources.values():
            setup_resource(r.system_id, r.id, r.name)

        # 动作
        for action in _all_actions.values():
            setup_action(system_id=env.BK_IAM_SYSTEM_ID, action_id=action.id, action_name=action.name)

        cls.__setup = True

    @classmethod
    def make_resource_instance(cls, resource_type: str, instance_id: str) -> Resource:
        """
        根据资源类型和资源id生成资源实例
        :param resource_type: 资源类型
        :param instance_id: 资源实例ID
        """
        resource_meta = ResourceEnum.get_resource_by_id(resource_type)
        return resource_meta.create_instance(instance_id)

    @classmethod
    def batch_make_resource_instance(cls, resources: List[Dict]):
        """
        批量构造resource对象
        """
        return [cls.make_resource_instance(r["type"], r["id"]) for r in resources]

    def make_request(self, action: Union[ActionMeta, str], resources: List[Resource] = None) -> Request:
        """
        构造鉴权的通用request
        :param action: 动作ID or ActionMeta实例
        :param resources: 资源resource列表
        """

        request = Request(
            system=env.BK_IAM_SYSTEM_ID,
            subject=Subject("user", self.username),
            action=ActionEnum.get_action_by_id(action),
            resources=resources,
            environment=None,
        )

        return request

    def make_multi_request(
        self, actions: List[Union[ActionMeta, str]], resources: List[Resource] = None
    ) -> MultiActionRequest:
        """
        构造批量请求鉴权的通用request
        :param actions: 动作列表
        :param resources: 资源列表, 在这里一般为[]
        """

        resources = resources or []
        actions = [ActionEnum.get_action_by_id(action) for action in actions]
        multi_request = MultiActionRequest(
            system=env.BK_IAM_SYSTEM_ID,
            subject=Subject("user", self.username),
            actions=actions,
            resources=resources,
            environment=None,
        )

        return multi_request

    def is_allowed(
        self, action: Union[ActionMeta, str], resources: List[Resource], is_raise_exception: bool = False
    ) -> bool:
        """
        请求iam客户端进行鉴权
        :param: action: 动作ID or ActionMeta实例
        :param: resources: 资源resource列表
        :param: is_raise_exception: 当鉴权失败时是否抛出异常
        """

        action = ActionEnum.get_action_by_id(action)
        # 若action不关联任何资源，则将resources置为空
        if not action.related_resource_types:
            resources = []

        request = self.make_request(action, resources)
        try:
            permission = self._iam.is_allowed(request)
        except AuthAPIError as e:
            logger.exception(f"IAM AuthAPIError: {e}")
            permission = False

        if not permission and is_raise_exception:
            data, url = self.get_apply_data([action], resources)
            raise PermissionDeniedError(action.name, data, url)

        return permission

    def batch_is_allowed(
        self, actions: List[Union[ActionMeta, str]], resources: List[List[Resource]], is_raise_exception: bool = False
    ) -> Dict[str, Dict[str, bool]]:
        """
        对一批动作的一批资源进行批量鉴权
        :param actions: 待鉴权的动作列表, 格式为[action1, action2, ...]
        :param resources: 待鉴权的资源列表, 格式为[[resource1], [resources2], ...]
        :param is_raise_exception: 鉴权失败时是否抛出异常
        """

        multi_request = self.make_multi_request(actions)
        batch_permission = {}
        try:
            batch_permission = self._iam.batch_resource_multi_actions_allowed(multi_request, resources)
        except AuthAPIError as e:
            logger.exception(f"IAM AuthAPIError: {e}")
            for index in range(len(resources)):
                batch_permission[str(index + 1)] = {action.id: False for action in actions}

        permission_list = itertools.chain(*[list(permission.values()) for permission in batch_permission.values()])
        is_all_permission_allowed = True
        for permission in permission_list:
            is_all_permission_allowed &= permission

        if not is_all_permission_allowed and is_raise_exception:
            resources_list = list(itertools.chain(*resources))
            data, url = self.get_apply_data(actions, resources_list)
            actions_name = ", ".join([action.name for action in actions])
            raise PermissionDeniedError(actions_name, data, url)

        return batch_permission

    def policy_query(self, action: Union[ActionMeta, str], obj_list: List[Union[int, str]]) -> List:
        """
        :param action: 鉴权动作
        :param obj_list: 待鉴权对象
        :return 返回符合鉴权的对象
        """

        is_superuser = User.objects.filter(username=self.username, is_superuser=True).exists()
        if env.BK_IAM_SKIP or is_superuser:
            return obj_list

        # 获得策略数据
        try:
            request = self.make_request(action=action)
            policies = self._iam._do_policy_query(request)
        except AuthAPIError as e:
            logger.exception(f"IAM AuthAPIError: {e}")
            return []

        if not policies:
            return []

        # 将策略数据生成表达式，并根据表达式判断业务权限
        expression = make_expression(policies)
        allow_biz_list = []
        for obj in obj_list:
            iam_obj = ObjectSet()
            iam_obj.add_object(ResourceEnum.BUSINESS.id, {"id": str(obj)})

            is_allowed = self._iam._eval_expr(expression, iam_obj)
            if is_allowed:
                allow_biz_list.append(obj)

        return allow_biz_list

    def make_application(
        self, action_ids: List[str], resources: List[Resource] = None, system_id: str = env.BK_IAM_SYSTEM_ID
    ) -> Application:
        """
        构造Application，提供给get_apply_url参数
        :param action_ids: 动作列表id
        :param resources: 资源instance列表
        :param system_id: 系统ID
        """

        iam_actions: List[Union[ActionWithResources, ActionWithoutResources]] = []
        resources = resources or []

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
            for resource_type in related_resource_types:
                # 同一个资源类型可以包含多个资源
                instances = []
                for resource in resources:
                    if resource.system != resource_type.system_id or resource.type != resource_type.id:
                        continue

                    instances.append(
                        ResourceInstance(
                            [ResourceNode(resource.type, resource.id, resource.attribute.get("name", resource.id))]
                        )
                    )

                iam_related_resources_types.append(
                    RelatedResourceType(resource_type.system_id, resource_type.id, instances)
                )

            iam_actions.append(ActionWithResources(action_id, iam_related_resources_types))

        application = Application(system_id=system_id, actions=iam_actions)
        return application

    def get_apply_url(
        self, action_ids: List[str], resources: List[Resource] = None, system_id: str = env.BK_IAM_SYSTEM_ID
    ) -> str:
        """
        申请无权限跳转url
        :param action_ids: 动作列表id
        :param resources: 资源列表
        :param system_id: 系统ID
        """

        application = self.make_application(action_ids, resources, system_id)
        ok, message, url = self._iam.get_apply_url(application, self.bk_token, self.username)
        if not ok:
            logger.error(f"iam generate apply url fail: {message}")
            return env.IAM_APP_URL

        return url

    def get_apply_data(
        self, actions: List[Union[ActionMeta, str]], resources: List[Resource] = None
    ) -> Tuple[Any, str]:
        """
        获取无权限交互数据和申请无权限跳转url
        :param actions: 动作列表
        :param resources: 资源列表
        """

        system_id = env.BK_IAM_SYSTEM_ID
        subject = Subject("user", self.username)
        self.setup_meta()

        resources = resources or []
        action_to_resources_list = []
        for action in actions:
            action = ActionEnum.get_action_by_id(action)
            if not action.related_resource_types:
                action_to_resources_list.append({"action": action, "resources_list": [[]]})
                continue

            # gen_perms_apply_data 要求单个 action 中对应的 resources_list 必须是同类型的 Resource
            # 因此这里默认就不去区分resources的类别了
            action_to_resources_list.append({"action": action, "resources_list": [resources]})

        data = gen_perms_apply_data(system_id, subject, action_to_resources_list)
        url = self.get_apply_url(actions, resources)

        return data, url
