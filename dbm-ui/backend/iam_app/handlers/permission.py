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
from django.utils.translation import gettext as _
from iam import IAM, DummyIAM, MultiActionRequest, Request, Resource, Subject
from iam.exceptions import AuthAPIError
from iam.iam import logger as iam_logger
from iam.meta import setup_action, setup_resource, setup_system
from iam.utils import gen_perms_apply_data

from backend import env
from backend.iam_app import tasks
from backend.iam_app.dataclass.actions import ActionEnum, ActionMeta, _all_actions
from backend.iam_app.dataclass.resources import ResourceEnum, ResourceMeta, _all_resources
from backend.iam_app.exceptions import PermissionDeniedError
from backend.iam_app.handlers.backends import get_iam_backend
from backend.utils.local import local

logger = logging.getLogger("root")
# 关闭iam的debug日志，加快请求速率 & 防止敏感信息泄露
iam_logger.setLevel(logging.ERROR)


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
        self.backend = get_iam_backend(self._iam)

    def _call(self, method: str, *args, **kwargs) -> Any:
        """
        鉴权后端的统一入口。
        TODO: 接入shadow影子对比时在此按采样率额外调用另一版本的后端并比对结果(见02文档J4)
        """
        result = getattr(self.backend, method)(*args, **kwargs)
        # 影子比对：在V3真实鉴权模式下，后台异步跑一次V4只打日志，不改变真实返回值
        tasks.dispatch_shadow(method, result, args, kwargs)
        return result

    @classmethod
    def get_iam_client(cls):
        tenant_id = getattr(env, "BK_TENANT_ID", "")
        if env.BK_IAM_SKIP:
            return DummyIAM(env.APP_CODE, env.SECRET_KEY, env.BK_IAM_APIGATEWAY, tenant_id)
        return IAM(env.APP_CODE, env.SECRET_KEY, env.BK_IAM_APIGATEWAY, tenant_id)

    def get_system_info(self):
        """
        获取权限中心注册的动作列表
        """
        data = self._call("get_system_info")
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

        permission = self._call("is_allowed", self.username, action, resources)

        if not permission and is_raise_exception:
            data, url = self.get_apply_data([action], [resources])
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

        # 如果是超级管理员 则检查通过
        if self.is_superuser:
            permission_list = {action.id: True for action in actions}
            return permission_list

        try:
            permission_list = self._call("multi_actions_is_allowed", self.username, actions, resources)
        except AuthAPIError as e:
            logger.exception(f"IAM AuthAPIError: {e}")
            permission_list = {action.id: False for action in actions}

        if not permission_list:
            permission_list = {action.id: False for action in actions}

        is_all_permission_allowed = True
        for permission in permission_list.values():
            is_all_permission_allowed &= permission

        if not is_all_permission_allowed and is_raise_exception:
            data, url = self.get_apply_data(actions, [resources])
            actions_name = ", ".join([action.name for action in actions])
            raise PermissionDeniedError(actions_name, data, url)

        return permission_list

    def batch_is_allowed(
        self,
        actions: List[Union[ActionMeta, str]],
        resources_list: List[List[Resource]],
        is_raise_exception: bool = False,
    ) -> Dict[str, Dict[str, bool]]:
        """
        对一批动作的一批资源进行批量鉴权
        :param actions: 待鉴权的动作列表, 格式为[action1, action2, ...]
        :param resources_list: 待鉴权的资源列表, 格式为[[resource1], [resources2], ...]
        :param is_raise_exception: 鉴权失败时是否抛出异常
        """

        # 如果是超级管理员 则检查通过
        if self.is_superuser:
            permission_list = {}
            for index, resources in enumerate(resources_list):
                key = index if len(resources) > 1 else resources[0].id
                permission_list[key] = {action.id: True for action in actions}
            return permission_list

        batch_permission = {}
        try:
            batch_permission = self._call("batch_is_allowed", self.username, actions, resources_list)
        except Exception as e:  # pylint: disable=broad-except
            logger.exception(f"IAM AuthAPIError: {e}")
            for index in range(len(resources_list)):
                batch_permission[str(index + 1)] = {action.id: False for action in actions}

        permission_list = itertools.chain(*[list(permission.values()) for permission in batch_permission.values()])
        is_all_permission_allowed = True
        for permission in permission_list:
            is_all_permission_allowed &= permission

        if not is_all_permission_allowed and is_raise_exception:
            data, url = self.get_apply_data(actions, resources_list)
            actions_name = ", ".join([action.name for action in actions])
            raise PermissionDeniedError(actions_name, data, url)

        return batch_permission

    def policy_query(self, action: Union[ActionMeta, str], obj_list: List[Union[int, str]]) -> List:
        """
        批量判断业务资源关联动作是否有权限
        :param action: 鉴权动作
        :param obj_list: 待鉴权对象
        :return 返回符合鉴权的对象
        """

        if env.BK_IAM_SKIP or self.is_superuser:
            return obj_list

        action = ActionEnum.get_action_by_id(action)
        return self._call("policy_query", self.username, action, obj_list)

    def get_apply_data(
        self, actions: List[Union[ActionMeta, str]], resources_list: List[List[Resource]] = None
    ) -> Tuple[Any, str]:
        """
        获取无权限交互数据和申请无权限跳转url
        :param actions: 动作列表
        :param resources_list: 资源列表
        """

        system_id = env.BK_IAM_SYSTEM_ID
        subject = Subject("user", self.username)
        self.setup_meta()

        resources_list = resources_list or []
        action_to_resources_list = []
        for action in actions:
            action = ActionEnum.get_action_by_id(action)
            if not action.related_resource_types:
                action_to_resources_list.append({"action": action, "resources_list": [[]]})
                continue

            # gen_perms_apply_data 要求单个 action 中对应的 resources_list 必须是同类型的 Resource
            # 因此这里默认就不去区分resources的类别了
            action_to_resources_list.append({"action": action, "resources_list": resources_list})

        data = gen_perms_apply_data(system_id, subject, action_to_resources_list)
        url = self._call("get_apply_url", actions, resources_list)

        return data, url

    def grant_creator_actions(self, resource: Resource, creator: str = None):
        """
        新建实例给创建者授权。V3走属性授权，V4走角色实例授权，差异由后端消化
        :param resource: 资源实例
        :param creator: 资源创建者
        """
        return self._call("grant_creator_actions", resource, creator or self.username)

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

        instance_ids = [id_field(item) for item in result_list if id_field(item)]
        resources_list = [[instance] for instance in resource_meta.batch_create_instances(instance_ids)]

        if not resources_list:
            return response

        permission_result = Permission().batch_is_allowed(actions, resources_list)
        false_actions_map = {action.id: False for action in actions}

        for item in result_list:
            item.setdefault("permission", {})
            origin_instance_id = id_field(item)
            if not origin_instance_id:
                # 如果拿不到实例ID，则不处理
                continue
            instance_id = str(origin_instance_id)
            item["permission"].update(permission_result.get(instance_id, false_actions_map))

            if always_allowed(item):
                # 权限豁免
                for action_id in item["permission"]:
                    item["permission"][action_id] = True

        return response

    @classmethod
    def insert_external_permission_field(
        cls,
        response,
        actions: List[ActionMeta],
        resource_meta: Union[ResourceMeta, List[ResourceMeta], None],
        resource_id: Any,
    ):
        """
        视图函数返回后，在数据外部同层插入权限字段。认为资源通常是一种类型的一个(比如业务)或者没有(比如全局操作)
        如果一个动作关联多种资源，则resource_meta是list，且resource_id是map --- 资源类型：资源ID
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

        # 对关联资源的动作鉴权
        if actions_with_resource:
            if isinstance(resource_meta, list) and len(resource_meta) > 1:
                resources = [meta.create_instance(instance_id=resource_id[meta.id]) for meta in resource_meta]
            else:
                resource_meta = resource_meta[0] if isinstance(resource_meta, list) else resource_meta
                resources = [resource_meta.create_instance(instance_id=resource_id)]
            permission_result.update(Permission().multi_actions_is_allowed(actions_with_resource, resources))

        # 对非关联资源的动作鉴权
        if actions_without_resource:
            client = Permission()
            permission_result.update(
                {action.id: client.is_allowed(action, resource_id) for action in actions_without_resource}
            )

        # 填充权限字段
        data_list = response.data if isinstance(response.data, list) else [response.data]
        for data in data_list:
            data.setdefault("permission", {})
            data["permission"].update(permission_result)

        return response

    @classmethod
    def decorator_permission_field(
        cls,
        actions: List[ActionMeta] = None,
        action_filed: Callable = lambda item: None,
        resource_meta: ResourceMeta = None,
        id_field: Callable = lambda item: item["id"],
        data_field: Callable = lambda data_list: data_list,
        always_allowed: Callable = lambda item: False,
        many: bool = True,
    ):
        """
        内嵌数据权限字段的装饰器，适用于列表每一项数据的权限字段
        """

        def wrapper(view_func):
            @wraps(view_func)
            def wrapped_view(*args, **kwargs):
                response = view_func(*args, **kwargs)

                kwargs = {**args[1].data, **args[1].query_params.dict(), "view_class": args[0], **kwargs}
                perm_actions = actions or action_filed(kwargs)
                if not perm_actions:
                    return response

                # 内嵌权限字段，默认值关联一种资源类型
                action_resource_meta = resource_meta or perm_actions[0].related_resource_types[0]
                return cls.insert_permission_field(
                    response,
                    perm_actions,
                    action_resource_meta,
                    id_field,
                    data_field,
                    always_allowed,
                    many,
                )

            return wrapped_view

        return wrapper

    @classmethod
    def decorator_external_permission_field(
        cls,
        actions: List[ActionMeta] = None,
        action_filed: Callable = lambda item: None,
        param_field: Callable = lambda item: None,
        resource_meta: Union[ResourceMeta, List[ResourceMeta], None] = None,
    ):
        """
        外嵌数据权限字段的装饰器，适用于列表的全局权限字段
        """

        def wrapper(view_func):
            @wraps(view_func)
            def wrapped_view(*args, **kwargs):
                response = view_func(*args, **kwargs)
                kwargs = {**args[1].data, **args[1].query_params.dict(), "view_class": args[0], **kwargs}

                # 获取鉴权动作
                perm_actions = actions or action_filed(kwargs)
                if not perm_actions:
                    return response

                # 获取鉴权的资源
                try:
                    if not resource_meta and not perm_actions[0].related_resource_types:
                        action_resource_meta = None
                    else:
                        action_resource_meta = resource_meta or perm_actions[0].related_resource_types
                    resource = None if not action_resource_meta else param_field(kwargs)
                    # 填充权限字段
                    return cls.insert_external_permission_field(response, perm_actions, action_resource_meta, resource)
                except Exception as e:
                    logger.error(_("填充权限字段失败：{}").format(e))
                    return response

            return wrapped_view

        return wrapper
