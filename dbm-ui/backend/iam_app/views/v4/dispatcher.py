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

import base64
import json
import logging
from typing import Dict, List

from django.core.cache import cache
from django.http import JsonResponse
from iam.contrib.django.dispatcher import DjangoBasicResourceApiDispatcher
from iam.resource.utils import FancyDict, Page, get_filter_obj

from backend import env
from backend.components.iamv4.client import IAMV4Api

logger = logging.getLogger("root")

# 系统AuthToken的缓存，IAM回调的Basic认证用它做密码
AUTH_TOKEN_CACHE_KEY = "iam_v4_system_auth_token"
AUTH_TOKEN_CACHE_TIME = 10 * 60

# V4的资源回调只有这两个method，V3的 list_attr / list_attr_value / list_instance_by_policy / search_instance 均已废弃
LIST_INSTANCE = "list_instance"
FETCH_INSTANCE_INFO = "fetch_instance_info"

DEFAULT_PAGE_SIZE = 20
# provider 支持的实例属性。IAM 还会要 id 与 _bk_iam_approvers_：前者 provider 总会返回，
# 后者本期不支持，两者都不能透传给 provider，否则会被当成模型字段拼进ORM查询
SUPPORTED_REQUIRES = ["display_name", "_bk_iam_path_"]


class IAMV4ResourceApiDispatcher(DjangoBasicResourceApiDispatcher):
    """
    IAM V4 资源回调分发器。

    V4与V3的回调机制一致（单一URL + 按 type/method 分发），provider 的实现可以完全复用，
    差异集中在协议细节：分页参数、属性字段名、响应结构和认证方式，全部在本类内消化。
    """

    def __init__(self, system: str):
        # V4的回调认证不依赖V3的IAM client，这里只需要系统ID
        super().__init__(iam=None, system=system)

    def _dispatch(self, request):
        request_id = request.META.get("HTTP_X_REQUEST_ID", "")

        # iam v4调用认证
        if not self._is_auth_allowed(request.META.get("HTTP_AUTHORIZATION", "")):
            logger.error("[iam_v4_callback] request(%s) auth failed", request_id)
            return self._error_response(401, "UNAUTHENTICATED", "basic auth failed", request_id)

        # 解析请求体：method、resource_type, 获取调用的provider
        try:
            data = json.loads(request.body)
        except Exception:  # pylint: disable=broad-except
            return self._error_response(400, "INVALID_ARGUMENT", "request body is not a valid json", request_id)

        method, resource_type = data.get("method"), data.get("type")
        if not method or not resource_type:
            return self._error_response(400, "INVALID_ARGUMENT", "method and type is required field", request_id)
        if resource_type not in self._provider:
            message = "unsupported resource type: {}".format(resource_type)
            return self._error_response(404, "NOT_FOUND", message, request_id)
        if method not in [LIST_INSTANCE, FETCH_INSTANCE_INFO]:
            return self._error_response(404, "NOT_FOUND", "unsupported method: {}".format(method), request_id)

        logger.info("[iam_v4_callback] request(%s): %s", request_id, data)
        provider, options = self._provider[resource_type], self._get_options(request)

        # v4只用实现两个方法: list_instance/fetch_instance
        try:
            if method == LIST_INSTANCE:
                result = provider.list_instance(self._list_instance_filter(data), self._page(data), **options)
                instances = self._normalize(result.results, ["display_name"])
                return self._success_response({"count": result.count, "results": instances}, request_id)
            elif method == FETCH_INSTANCE_INFO:
                requires = [item for item in (data.get("requires") or []) if item in SUPPORTED_REQUIRES]
                requires = requires or SUPPORTED_REQUIRES
                result = provider.fetch_instance_info(self._fetch_instance_filter(data, requires), **options)
                instances = self._normalize(result.to_list(), requires)
                return self._success_response(instances, request_id)
            else:
                return self._error_response(404, "NOT_FOUND", "unsupported method", request_id)
        except Exception as e:  # pylint: disable=broad-except
            logger.exception("[iam_v4_callback] request(%s) failed: %s", request_id, e)
            return self._error_response(500, "INTERNAL", str(e), request_id)

    @staticmethod
    def _is_auth_allowed(basic_auth: str) -> bool:
        """校验回调认证，格式为 Basic base64("bk_iam:{系统AuthToken}")"""
        if env.BK_IAM_SKIP:
            return True

        auth = basic_auth.strip().split()
        if len(auth) != 2 or auth[0].lower() != "basic":
            return False
        try:
            username, password = base64.b64decode(auth[1]).decode().split(":")
        except Exception:  # pylint: disable=broad-except
            return False
        if username != "bk_iam":
            return False

        token = cache.get(AUTH_TOKEN_CACHE_KEY)
        if token and password == token:
            return True

        # 比对不上时缓存可能已过期，重新拉取后再比对一次，避免IAM侧轮换token导致回调全部失败
        token = (IAMV4Api.retrieve_system_auth_token() or {}).get("auth_token")
        if not token:
            return False
        cache.set(AUTH_TOKEN_CACHE_KEY, token, AUTH_TOKEN_CACHE_TIME)
        return password == token

    @staticmethod
    def _page(data: Dict) -> Page:
        """V4的分页参数是 page/page_size，provider 用的是 limit/offset"""
        page_data = data.get("page") or {}
        page = int(page_data.get("page") or 1)
        page_size = int(page_data.get("page_size") or DEFAULT_PAGE_SIZE)
        return Page(limit=page_size, offset=(page - 1) * page_size)

    @staticmethod
    def _list_instance_filter(data: Dict) -> FancyDict:
        """
        V4的关键字字段是 keyword和parent(ancestors可选？)
        provider 同时读 search 和 keyword，这里补齐 search。
        """
        filter_obj = get_filter_obj(data.get("filter"), ["parent", "ancestors", "keyword"])
        filter_obj.search = filter_obj.keyword
        return filter_obj

    @staticmethod
    def _fetch_instance_filter(data: Dict, requires: List[str]) -> FancyDict:
        """V4把待查询的属性放在body的requires里，provider 读的是 filter.attrs"""
        filter_obj = get_filter_obj(data.get("filter"), ["ids"])
        filter_obj.attrs = requires
        return filter_obj

    @staticmethod
    def _normalize(instances: List[Dict], requires: List[str] = None) -> List[Dict]:
        """
        规整provider的返回：实例ID转字符串（部分provider直接返回了模型的整型主键），
        并按需要的属性裁剪，避免把模型字段名暴露给IAM
        """
        for instance in instances:
            if "id" in instance:
                instance["id"] = str(instance["id"])
        # 无属性返回全部
        if not requires:
            return instances
        # 指定属性要带上id。注意不能原地修改requires，调用方传入的可能是模块级常量
        keep_fields = {*requires, "id"}
        return [{key: value for key, value in i.items() if key in keep_fields} for i in instances]

    @staticmethod
    def _success_response(data, request_id: str) -> JsonResponse:
        response = JsonResponse({"data": data})
        response["X-Request-Id"] = request_id
        return response

    @staticmethod
    def _error_response(status: int, code: str, message: str, request_id: str) -> JsonResponse:
        """V4的失败响应是非2xx状态码 + error结构，与V3的固定200不同"""
        response = JsonResponse({"error": {"code": code, "message": message}}, status=status)
        response["X-Request-Id"] = request_id
        return response
