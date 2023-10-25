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
from typing import Any, Dict, Optional

from blueapps.account.decorators import login_exempt
from django.utils.decorators import classonlymethod
from rest_framework import serializers, status, viewsets
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet, ReadOnlyModelViewSet


class GenericMixin:
    queryset = ""
    # 是否支持全局豁免
    global_login_exempt = False

    @staticmethod
    def get_request_data(request, **kwargs) -> Dict[str, Any]:
        request_data = request.data.copy() or {}
        request_data.update(**kwargs)
        return request_data

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
        # TODO: ⚠️为了避免权限泄露，希望默认权限是永假来兜底，所以请写每一个视图的时候都覆写该方法
        # return [RejectPermission()]
        return []

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


class ReadOnlyAuditedModelViewSet(ReadOnlyModelViewSet, GenericMixin):
    pass
