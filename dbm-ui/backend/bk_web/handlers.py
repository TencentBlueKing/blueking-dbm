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
import json
import logging
from typing import Optional

from django.conf import settings
from django.http import Http404, JsonResponse
from django.utils.translation import ugettext as _
from rest_framework import exceptions, status

from backend.exceptions import AppBaseException, ErrorCode

logger = logging.getLogger("root")


def format_validation_message(detail):
    """格式化drf校验错误信息"""

    if isinstance(detail, list):
        message = "; ".join(["{}: {}".format(k, v) for k, v in enumerate(detail)])
    elif isinstance(detail, dict):
        messages = []
        for k, v in detail.items():
            if isinstance(v, list):
                try:
                    messages.append("{}: {}".format(k, ",".join(v)).replace("non_field_errors:", ""))
                except TypeError:
                    messages.append("{}: {}".format(k, _("部分列表元素的参数不合法，请检查")))
            elif isinstance(v, dict):
                messages.append(format_validation_message(v))
            else:
                messages.append("{}: {}".format(k, v))
        message = ";".join(messages)
    else:
        message = detail

    return message


def drf_exception_handler(exc, context):
    """
    自定义错误处理方式
    """
    logger.exception(getattr(exc, "message", exc))
    request = context["request"]

    if request.method == "GET":
        request_params = request.query_params
    else:
        if "multipart/form-data" in request.headers.get("Content-Type", ""):
            request_params = {"storages": str(getattr(request, "FILES"))}
        else:
            request_params = request.data

    logger.error(
        _("捕获未处理异常, 请求URL->{}, 请求方法->{} 请求参数->{}").format(request.path, request.method, json.dumps(request_params))
    )
    # 专门处理 404 异常，直接返回前端，前端处理
    if isinstance(exc, Http404):
        return JsonResponse(_error(404, str(exc)))

    # # 专门处理 403 异常，直接返回前端，前端处理
    # if isinstance(exc, exceptions.PermissionDenied):
    #     return HttpResponse(exc.detail, status='403')

    # 特殊处理 rest_framework ValidationError
    if isinstance(exc, exceptions.ValidationError):
        return JsonResponse(_error(100, format_validation_message(exc.detail)))

    if isinstance(exc, (exceptions.NotAuthenticated, exceptions.AuthenticationFailed)):
        return JsonResponse(
            status=status.HTTP_401_UNAUTHORIZED,
            data=_error(
                status.HTTP_401_UNAUTHORIZED,
                _("用户未登录或登录态失效，请重新登录"),
                # ugly: 后端关注前端窗口尺寸
                # TODO 考虑通过版本或者其他方式, 由前端自行消化 width 和 height
                data={"login_url": {"plain": settings.LOGIN_PLAIN_URL}, "width": 700, "height": 510},
            ),
        )

    # 处理 rest_framework 的异常
    if isinstance(exc, exceptions.APIException):
        return JsonResponse(_error(exc.status_code, exc.detail))

    # 处理 Data APP 自定义异常
    if isinstance(exc, AppBaseException):
        _msg = _("【APP 自定义异常】{message}, code={code}, args={args}").format(
            message=exc.message, code=exc.code, args=exc.args, data=exc.data, errors=exc.errors
        )
        logger.exception(_msg)
        return JsonResponse(_error(exc.code, exc.message, exc.data, exc.errors))

    # 判断是否在debug模式中,
    # 在这里判断是防止阻止了用户原本主动抛出的异常
    if settings.DEBUG:
        return None

    # 非预期异常
    error = getattr(exc, "message", exc)
    logger.exception(error)
    request = context["request"]
    logger.error(
        _("捕获未处理异常, 请求URL->[{}], 请求方法->[{}] 请求参数->[{}]").format(
            request.path, request.method, request.query_params if request.method == "GET" else request.data
        )
    )
    return JsonResponse(_error(500, _("系统错误，请联系管理员({error})").format(error=error)))


def _error(code: int = 0, message: str = "", data: Optional[dict] = None, errors: Optional[list] = None):
    if len(str(code)) == 3:
        code = f"{ErrorCode.PLAT_CODE}{ErrorCode.WEB_CODE}{code}"
    message = f"{message}（{code}）"
    # 错误码的类型为int，保持成功码和失败码的类型一致
    code = int(code)
    return {"result": False, "code": code, "data": data, "message": message, "errors": errors}
