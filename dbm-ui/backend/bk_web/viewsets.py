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
import copy
import json
import re
from typing import Any, Dict, List, Optional, Tuple, Union

from blueapps.account.decorators import login_exempt
from django.conf import settings
from django.http import HttpResponse, QueryDict, StreamingHttpResponse
from django.utils.decorators import classonlymethod
from rest_framework import permissions, serializers, status, viewsets
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet

from backend import env
from backend.bk_web.constants import EXTERNAL_TICKET_TYPE_WHITELIST, IP_RE
from backend.components.dbconsole.client import DBConsoleApi
from backend.iam_app.dataclass.actions import ActionEnum
from backend.iam_app.handlers.drf_perm.base import RejectPermission
from backend.utils.basic import get_target_items_from_details


class GenericMixin:
    queryset = ""
    # 是否支持全局豁免
    global_login_exempt: bool = False
    # 权限动作映射表。如果权限映射逻辑复杂，可考虑覆写_get_custom_permissions
    action_permission_map: Dict[Union[Tuple[str], str], List[permissions.BasePermission]] = {}
    # ⚠️为了避免权限泄露，希望默认权限是永假来兜底，所以请定义好每个视图的权限类
    default_permission_class: List[permissions.BasePermission] = [RejectPermission()]

    @staticmethod
    def get_request_data(request, **kwargs) -> Dict[str, Any]:
        request_data = request.data.copy() or {}
        request_data.update(**kwargs)
        return request_data

    def get_action_permission_map(self) -> dict:
        return self.action_permission_map

    def get_default_permission_class(self) -> list:
        return self.default_permission_class

    def get_permission_class_with_action(self, action):
        for actions, custom_perms in self.get_action_permission_map().items():
            if action == actions or action in actions:
                return custom_perms
        return self.get_default_permission_class()

    @property
    def validated_data(self):
        """
        校验的数据
        """
        if self.request.method == "GET":
            data = self.request.query_params
        else:
            data = self.request.data

        # 从 esb 获取参数
        bk_username = self.request.META.get("HTTP_BK_USERNAME")
        bk_app_code = self.request.META.get("HTTP_BK_APP_CODE")

        data = data.copy()
        data.setdefault("bk_username", bk_username)
        data.setdefault("bk_app_code", bk_app_code)

        serializer = self.serializer_class or self.get_serializer_class()
        return self.params_validate(serializer, data)

    def params_validate(self, slz_cls, context: Optional[Dict] = None, init_params: Optional[Dict] = None, **kwargs):
        """
        检查参数是够符合序列化器定义的通用逻辑
        :param slz_cls: 序列化器
        :param context: 上下文数据，可在 View 层传入给 SLZ 使用（默认带有request和view）
        :param init_params: 初始参数，替换掉 request.query_params / request.data
        :param kwargs: 可变参数
        :return: 校验的结果
        """
        if init_params is None:
            # 获取 Django request 对象
            _request = self.request
            if _request.method in ["GET"]:
                req_data = copy.deepcopy(_request.query_params)
            else:
                req_data = _request.data
        else:
            req_data = init_params

        if kwargs:
            req_data.update(kwargs)

        # 增加slz的上下文
        slz_context = {"request": self.request, "view": self}
        if isinstance(context, dict):
            slz_context.update(context)

        # 参数校验，如不符合直接抛出异常
        slz = slz_cls(data=req_data, context=slz_context)
        slz.is_valid(raise_exception=True)

        # 用representation表示
        if kwargs.get("representation"):
            return slz.to_representation(slz.validated_data)

        return slz.validated_data

    # 权限类的设计
    def get_permissions(self):
        default_permissions = super().get_permissions()
        custom_permissions = self._get_custom_permissions()
        return [*default_permissions, *custom_permissions]

    def _get_custom_permissions(self):
        """用户自定义的permission类,由子类继承覆写"""
        return self.get_permission_class_with_action(self.action)

    @classmethod
    def _get_login_exempt_view_func(cls):
        # 需要豁免的接口方法与名字
        return {"post": [], "put": [], "get": [], "delete": []}

    @classonlymethod
    def as_view(cls, actions=None, **initkwargs):
        # 对透传接口增加登录豁免
        view_func = super().as_view(actions, **initkwargs)
        login_exempt_view_func = cls._get_login_exempt_view_func()
        # 存在一个豁免方法时，则将该视图函数进行豁免
        for method in login_exempt_view_func.keys():
            if cls.global_login_exempt or view_func.actions.get(method) in login_exempt_view_func[method]:
                return login_exempt(view_func)

        return view_func


class SystemViewSet(GenericMixin, viewsets.ViewSet, viewsets.GenericViewSet):
    """SaaS app 使用的 API ViewSet"""

    serializer_class = serializers.Serializer


class AuditedModelViewSet(GenericMixin, ModelViewSet):
    """记录数据插入信息的ModelViewSet类"""

    def perform_create(self, serializer):
        """创建时补充基础Model中的字段"""

        username = self.request.user.username
        return serializer.save(creator=username, updater=username)

    def perform_update(self, serializer):
        """更新时补充基础Model中的字段"""

        username = self.request.user.username
        return serializer.save(updater=username)

    def destroy(self, request, *args, **kwargs):
        """修改 destroy 的返回码为 200"""
        super(AuditedModelViewSet, self).destroy(request, *args, **kwargs)
        return Response(status=status.HTTP_200_OK)


class ReadOnlyAuditedModelViewSet(GenericMixin, ReadOnlyModelViewSet):
    pass


class ExternalProxyViewSet(viewsets.ViewSet):
    """外部代理路由视图"""

    def fill_request_headers(self, request, *args, **kwargs):
        # 如果是grafana的请求，则要带上X-Grafana-Org-Id
        if request.path.split("/")[2] == "grafana":
            return {"X-Grafana-Org-Id": request.headers.get("X-Grafana-Org-Id")}
        return None

    def after_response(self, request, response, *args, **kwargs):
        # 请求内部的dashboard url，但是host要替换为当前dbm的host
        if "/grafana/get_dashboard/" in request.path:
            data = response.json()["data"]
            data["url"] = f"{env.BK_SAAS_HOST}/grafana/{data['url'].split('grafana/')[1]}"
            for url_info in data["urls"]:
                url_info["url"] = f"{env.BK_SAAS_HOST}/grafana/{url_info['url'].split('grafana/')[1]}"
            return Response(data)
        if ".css" in request.path:
            return HttpResponse(response, headers={"Content-Type": "text/css"})

        # 仅转发，提前返回response
        if env.ENABLE_OPEN_EXTERNAL_PROXY:
            return HttpResponse(response)

        # 屏蔽iam申请的内部路由
        if "/iam/get_apply_data/" in request.path or "/iam/simple_get_apply_data/" in request.path:
            data = response.json()["data"]
            data["apply_url"] = env.IAM_APP_URL
            return Response(data)

        # 业务列表只展示有权限的业务
        if "/cmdb/list_bizs/" in request.path:
            data = [d for d in response.json()["data"] if d["permission"][ActionEnum.DB_MANAGE.id]]
            return Response(data)

        # 单据的相关操作只能展示白名单的单据类型，否则展示空
        if "/apis/tickets/" in request.path:
            data = response.json()["data"]
            ticket_type = get_target_items_from_details(data, match_keys=["ticket_type"])
            if not set(ticket_type).issubset(set(EXTERNAL_TICKET_TYPE_WHITELIST)):
                return Response()

        # 制品库地址得用外网链接
        if "/storage/create_bkrepo_access_token/" in request.path:
            data = response.json()["data"]
            data["url"] = settings.BKREPO_ENDPOINT_URL
            return Response(data)

        # 制品库临时下载接口以文件流返回
        if "/storage/generic/temporary/download/" in request.path:
            return StreamingHttpResponse(
                response.iter_content(),
                content_type="application/octet‑stream",
                headers={"Content-Disposition": 'attachment; filename="dump.tar.gz"'},
            )

        # 外部 API 转发请求，把 IP 替换为 *.*.*.*。适用于json响应
        if request.path.startswith("/external/apis/") and response.headers.get("Content-Type").startswith(
            "application/json"
        ):
            data = re.sub(IP_RE, "*.*.*.*", response.content.decode("utf-8"))
            return Response(json.loads(data))
        # for path in [
        #     "/timeseries/time_series/unify_query/",
        #     "/timeseries/graph_promql_query/",
        #     "/timeseries/grafana/query/",
        #     "/timeseries/grafana/query_log/",
        # ]:
        #     if request.path.endswith(path):
        #         # 外部 API 转发请求，把 IP 替换为 *.*.*.*
        #         data = re.sub(IP_RE, "*.*.*.*", response.content.decode("utf-8"))
        #         return Response(json.loads(data))

        return HttpResponse(response)

    def external_proxy(self, request, *args, **kwargs):
        params = request.data or request.query_params
        if isinstance(params, QueryDict):
            params._mutable = True
        headers = self.fill_request_headers(request, *args, **kwargs)
        resp = getattr(DBConsoleApi, request.method.lower())(url_path=kwargs["path"], params=params, headers=headers)
        return self.after_response(request, resp, *args, **kwargs)
