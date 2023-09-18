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

from django.conf import settings
from django.utils.translation import ugettext_lazy as _
from iam import IAM

from backend import env

logger = logging.getLogger("root")


class ErrorCode(object):
    # 平台错误码
    PLAT_CODE = "87"

    # 模块错误码
    WEB_CODE = "00"
    IAM_CODE = "99"
    JWT_CODE = "98"
    DB_META_CODE = "01"
    FLOW_CODE = "02"
    DB_SERVICE_CODE = "03"
    TICKET_CODE = "04"
    DB_CONFIG_CODE = "05"
    DB_MEDIUM_CODE = "06"
    CMDB_CODE = "07"
    TASK_FLOW_CODE = "08"
    DB_PERMISSION_CODE = "09"
    DB_TABLE_FILTER_CODE = "10"
    DB_PARTITION_CODE = "11"
    RESOURCE_POOL_CODE = "12"
    REDIS_DTS_CODE = "13"


class AppBaseException(Exception):
    MODULE_CODE = "00"
    ERROR_CODE = "500"
    MESSAGE = _("系统异常")
    MESSAGE_TPL = None

    def __init__(self, context=None, data=None, **kwargs):
        """
        @param {String} code 自动设置异常状态码
        """
        if context is None:
            context = {}

        self.errors = kwargs.get("errors")

        # 优先使用第三方系统的错误编码
        if kwargs.get("code"):
            self.code = kwargs["code"]
        else:
            self.code = "{}{}{}".format(ErrorCode.PLAT_CODE, self.MODULE_CODE, self.ERROR_CODE)

        if self.MESSAGE_TPL:
            try:
                context.update(kwargs)
                self.message = self.MESSAGE_TPL.format(**context)
            except Exception:
                self.message = context or self.MESSAGE
        else:
            self.message = context or self.MESSAGE

        # 当异常有进一步处理时，需返回data
        self.data = data

    def __str__(self):
        return "[{}] {}".format(self.code, self.message)

    @classmethod
    def get_all_exception(cls):
        exception_classes = []

        def get_sub_classes(sub_class):
            for _cls in sub_class.__subclasses__():
                exception_classes.append(_cls)
                if len(_cls.__subclasses__()):
                    get_sub_classes(_cls)

        get_sub_classes(cls)
        return exception_classes

    @classmethod
    def get_err_code_msg_map(cls):
        err_code_map = {}
        for except_class in cls.get_all_exception():
            try:
                cls_inst = except_class()
            except TypeError:
                # 忽略 __init__ 需要额外参数的异常类
                continue
            message = getattr(cls_inst, "MESSAGE", _("系统错误"))
            err_code_map[cls_inst.code] = message
        return err_code_map


class ApiError(AppBaseException):
    pass


class ValidationError(AppBaseException):
    MESSAGE = _("参数验证失败")
    ERROR_CODE = "001"


class ApiResultError(ApiError):
    MESSAGE = _("远程服务请求结果异常")
    ERROR_CODE = "002"


class ComponentCallError(AppBaseException):
    MESSAGE = _("组件调用异常")
    ERROR_CODE = "003"


class BizNotExistError(AppBaseException):
    MESSAGE = _("业务不存在")
    ERROR_CODE = "004"


class LanguageDoseNotSupported(AppBaseException):
    MESSAGE = _("语言不支持")
    ERROR_CODE = "005"


class PermissionDeniedError(AppBaseException):
    MESSAGE = _("权限不足")
    ERROR_CODE = "403"

    def __init__(self, context=None, data=None, **kwargs):
        # 传递构造permission
        try:
            permission = kwargs.get("permission")
            if permission:
                client = IAM(env.APP_CODE, env.SECRET_KEY, bk_apigateway_url=env.BK_IAM_APIGETEWAY)
                for action in permission.get("actions") or []:
                    action["name"] = action.get("name") or action.get("id")
                data = {
                    "permission": {
                        "system_id": permission.get("system_id"),
                        "system_name": permission.get("system_name") or permission.get("system_id"),
                        "actions": permission.get("actions") or [],
                    },
                    "apply_url": client.get_apply_url(permission, bk_username="admin")[2],
                }
        except Exception as err:
            # 构造权限中心URL失败
            logger.exception(err)
        super().__init__(context=context, data=data, **kwargs)


class ApiRequestError(ApiError):
    # 属于严重的场景，一般为第三方服务挂了，ESB调请检查组件健康状况用超时
    MESSAGE = _("服务不稳定，请检查组件健康状况")
    ERROR_CODE = "015"
