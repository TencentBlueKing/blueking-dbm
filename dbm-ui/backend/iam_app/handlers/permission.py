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
from functools import wraps
from typing import Any, Callable, Dict, List, Tuple, Union

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
from backend.iam_app.dataclass.resources import ResourceEnum, ResourceMeta, _all_resources
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

        self.is_superuser = User.objects.filter(username=self.username, is_superuser=True).exists()
        self._iam = self.get_iam_client()

    @classmethod
    def get_iam_client(cls):
        if env.BK_IAM_SKIP:
            return DummyIAM(env.APP_CODE, env.SECRET_KEY, env.BK_IAM_INNER_HOST, env.BK_COMPONENT_API_URL)

        return IAM(
            env.APP_CODE, env.SECRET_KEY, bk_apigateway_url=env.BK_IAM_APIGATEWAY, api_version=env.BK_IAM_API_VERSION
        )

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

        # 如果是超级管理员，则检查通过
        if self.is_superuser:
            return True

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

    def multi_actions_is_allowed(
        self, actions: List[Union[ActionMeta, str]], resources: List[Resource], is_raise_exception: bool = False
    ) -> Dict[str, bool]:
        """
        对一批动作的一个资源进行批量鉴权
        :param actions: 待鉴权的动作列表, 格式为[action1, action2, ...]
        :param resources: 待鉴权的资源列表, 格式为[resource1]
        :param is_raise_exception: 鉴权失败时是否抛出异常
        """
        multi_request = self.make_multi_request(actions, resources)
        try:
            permission_list = self._iam.resource_multi_actions_allowed(multi_request)
        except AuthAPIError as e:
            logger.exception(f"IAM AuthAPIError: {e}")
            permission_list = {action.id: False for action in actions}

        is_all_permission_allowed = True
        for permission in permission_list.values():
            is_all_permission_allowed &= permission

        if not is_all_permission_allowed and is_raise_exception:
            data, url = self.get_apply_data(actions, resources)
            actions_name = ", ".join([action.name for action in actions])
            raise PermissionDeniedError(actions_name, data, url)

        return permission_list

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

        if env.BK_IAM_SKIP or self.is_superuser:
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

    def _get_topo_resource(self, resource: Resource):
        """
        获取资源的拓扑信息资源
        """
        if not resource:
            return []

        bk_iam_path = f"{resource.attribute.get('_bk_iam_path_', '/')}{resource.system},{resource.type},{resource.id}/"
        topo_resources = []
        for topo in bk_iam_path.split("/")[1:-1]:
            __, rtype, rid = topo.split(",")
            topo_resources.append(ResourceEnum.get_resource_by_id(rtype).create_instance(rid))
        return topo_resources

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

    def _grant_actions(self, resource, application, grant_func, raise_exception=True):
        grant_result = None
        try:
            grant_result = grant_func(application, self.bk_token, self.username)
            logger.info(f"[grant_creator_action] Success! resource: {resource.to_dict()}, result: {grant_result}")
        except Exception as e:
            logger.exception(f"[grant_creator_action] Failed! resource: {resource.to_dict()}, result: {e}")

            if raise_exception:
                raise e

        return grant_result

    def grant_creator_actions(self, resource: Resource, creator: str = None):
        """
        新建实例关联权限授权
        :param resource: 资源实例
        :param creator: 资源创建者
        :return:
        """
        application = {
            "system": resource.system,
            "type": resource.type,
            "id": resource.id,
            "name": resource.attribute.get("name", resource.id) if resource.attribute else resource.id,
            "creator": creator or self.username,
        }
        return self._grant_actions(resource, application, self._iam.grant_resource_creator_actions)

    def grant_creator_actions_attr(self, resource: Resource, creator: str = None):
        """
        新建实例属性关联权限授权
        :param resource: 资源实例
        :param creator: 资源创建者
        :return:
        """
        attributes = [
            {"id": attr_id, "name": attr_id, "values": [{"id": attr_value, "name": attr_value}]}
            for attr_id, attr_value in resource.attribute.items()
        ]
        application = {
            "system": resource.system,
            "type": resource.type,
            "creator": creator or self.username,
            "attributes": attributes,
        }
        return self._grant_actions(resource, application, self._iam.grant_resource_creator_action_attributes)

    @classmethod
    def insert_permission_field(
        cls,
        response,
        actions: List[ActionMeta],
        resource_meta: ResourceMeta,
        id_field: Callable = lambda item: item["id"],
        data_field: Callable = lambda data_list: data_list,
        always_allowed: Callable = lambda item: False,
        many: bool = True,
    ):
        """
        视图函数数据返回后，插入权限相关字段
        @param response: 视图执行的response
        @param actions: 动作列表
        @param resource_meta: 资源类型
        @param id_field: 从结果集获取ID字段的方式
        @param data_field: 从response.data中获取结果集的方式
        @param always_allowed: 满足一定条件进行权限豁免
        @param many: 是否为列表数据
        """
        result_list = data_field(response.data)
        if not many:
            result_list = [result_list]

        resources = [
            [resource_meta.create_instance(instance_id=id_field(item))] for item in result_list if id_field(item)
        ]

        if not resources:
            return response

        permission_result = Permission().batch_is_allowed(actions, resources)

        for item in result_list:
            item.setdefault("permission", {})
            origin_instance_id = id_field(item)
            if not origin_instance_id:
                # 如果拿不到实例ID，则不处理
                continue
            instance_id = str(origin_instance_id)
            item["permission"].update(permission_result[instance_id])

            if always_allowed(item):
                # 权限豁免
                for action_id in item["permission"]:
                    item["permission"][action_id] = True

        return response

    @classmethod
    def insert_external_permission_field(
        cls, response, actions: List[ActionMeta], resource_meta: Union[ResourceMeta, None], resource_id: Any
    ):
        """
        视图函数返回后，在数据外部同层插入权限字段。认为资源通常是一种类型的一个(比如业务)或者没有(比如全局操作)
        如果一个动作关联多种资源类型，请自定义实现（较为复杂暂不考虑）
        eg: 大数据返回节点列表，外部的permission字段表示是否有这个集群的操作权限
        {
            "permission": {"op": true},
            "count": 10,
            "results": [....]
            "xxx": "xxx"
        }
        如果没有分页结构，则直接在每个列表元素中插入权限字段
        """
        permission_result = {}
        actions_with_resource = [action for action in actions if action.related_resource_types]
        actions_without_resource = [action for action in actions if not action.related_resource_types]

        if actions_with_resource:
            resources = [resource_meta.create_instance(instance_id=resource_id)]
            permission_result.update(Permission().multi_actions_is_allowed(actions_with_resource, resources))

        if actions_without_resource:
            client = Permission()
            permission_result.update(
                {action.id: client.is_allowed(action, resource_id) for action in actions_without_resource}
            )

        if isinstance(response.data, list):
            response.data = [{"permission": permission_result, **d} for d in response.data]
        elif isinstance(response.data, dict):
            response.data.setdefault("permission", {})
            response.data["permission"].update(permission_result)

        return response

    @classmethod
    def decorator_permission_field(
        cls,
        actions: List[ActionMeta],
        resource_meta: ResourceMeta,
        id_field: Callable = lambda item: item["id"],
        data_field: Callable = lambda data_list: data_list,
        always_allowed: Callable = lambda item: False,
        many: bool = True,
    ):
        def wrapper(view_func):
            @wraps(view_func)
            def wrapped_view(*args, **kwargs):
                response = view_func(*args, **kwargs)
                return cls.insert_permission_field(
                    response,
                    actions,
                    resource_meta,
                    id_field,
                    data_field,
                    always_allowed,
                    many,
                )

            return wrapped_view

        return wrapper

    @classmethod
    def decorator_external_permission_field(
        cls, actions: List[ActionMeta], resource_meta: Union[ResourceMeta, None], param_field: Callable
    ):
        def wrapper(view_func):
            @wraps(view_func)
            def wrapped_view(*args, **kwargs):
                response = view_func(*args, **kwargs)
                # 补充request信息和视图类为kwargs
                kwargs = {**args[1].data, **args[1].query_params.dict(), "view_class": args[0], **kwargs}
                resource = None if resource_meta is None else param_field(kwargs)
                return cls.insert_external_permission_field(response, actions, resource_meta, resource)

            return wrapped_view

        return wrapper
