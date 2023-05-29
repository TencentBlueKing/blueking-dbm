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
import functools
import types

from django.utils.translation import ugettext_lazy as _

from backend.exceptions import AppBaseException, ErrorCode


# permission接口的异常兜底，用来捕获特殊需要处理的异常
# TODO 暂时只是demo，后续需要更精细化异常处理
class PermExceptionHandler(object):
    def __init__(self, func):
        functools.wraps(func)(self)

    def __call__(self, *args, **kwargs):
        try:
            return self.__wrapped__(*args, **kwargs)

        except Exception as e:
            raise DBPermissionBaseException(e)

    def __get__(self, instance, owner):
        if instance is None:
            return self

        return types.MethodType(self, instance)


class DBPermissionBaseException(AppBaseException):
    MODULE_CODE = ErrorCode.DB_PERMISSION_CODE
    MESSAGE = _("权限模块异常")


class ExcelAuthorizeVerifyException(DBPermissionBaseException):
    MESSAGE = _("授权EXCEL表校验异常")


class ExcelCloneVerifyException(DBPermissionBaseException):
    MESSAGE = _("权限克隆EXCEL表校验异常")


class AuthorizeDataHasExpiredException(DBPermissionBaseException):
    MESSAGE = _("授权数据已过期")


class CloneDataHasExpiredException(DBPermissionBaseException):
    MESSAGE = _("权限克隆数据已过期")
