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
import uuid
from typing import Callable

from django.conf import settings
from werkzeug.local import Local as _Local
from werkzeug.local import release_local

from backend.exceptions import AppBaseException

_local = _Local()


def new_request_id():
    return uuid.uuid4().hex


class Singleton:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not isinstance(cls._instance, cls):
            cls._instance = object.__new__(cls, *args, **kwargs)
        return cls._instance


class Local(Singleton):
    """Local 对象
    必须配合中间件 RequestProvider 使用
    """

    @property
    def request(self):
        """获取全局request对象"""
        request = getattr(_local, "request", None)
        return request

    @request.setter
    def request(self, value):
        """设置全局 request 对象"""
        _local.request = value

    @property
    def request_id(self):
        # celery 后台没有 request 对象
        if self.request:
            return getattr(self.request, "request_id", "")

        return new_request_id()

    def get_http_request_id(self):
        """从接入层获取 request_id，或者生成一个新的 request_id"""
        # 在从 header 中获取
        request_id = self.request.META.get(settings.REQUEST_ID_HEADER, "")
        if request_id:
            return request_id

        return new_request_id()

    def release(self):
        release_local(_local)


local = Local()


def activate_request(request, request_id=None):
    """
    激活request线程变量
    """
    if not request_id:
        request_id = new_request_id()
    request.request_id = request_id
    local.request = request
    return


def inject_request(func: Callable):
    try:
        request = local.request
    except AppBaseException:
        request = None

    def inner(*args, **kwargs):
        if request:
            activate_request(request)
        return func(*args, **kwargs)

    return inner
