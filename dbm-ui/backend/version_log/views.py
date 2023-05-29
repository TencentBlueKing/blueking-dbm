# -*- coding: utf-8 -*-
"""
Tencent is pleased to support the open source community by making 蓝鲸智云PaaS平台社区版 (BlueKing PaaS Community
Edition) available.
Copyright (C) 2017-2021 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at
http://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""

import functools
import logging

from django.http import JsonResponse
from django.shortcuts import render
from django.utils.translation import ugettext_lazy as _

from backend.version_log import config
from backend.version_log.models import VersionLogVisited
from backend.version_log.utils import get_parsed_html, get_version_list

logger = logging.getLogger(__name__)


def latest_read_record(view_func):
    @functools.wraps(view_func)
    def wrapper(request, *args, **kwargs):
        visit_log_version = request.GET.get("log_version") or request.POST.get("log_version")
        if config.LATEST_VERSION_INFORM and visit_log_version == config.LATEST_VERSION:
            VersionLogVisited.objects.update_visit_version(request.user.username, visit_log_version)

        return view_func(request, *args, **kwargs)

    return wrapper


def version_logs_list(request):
    """获取版本日志列表"""
    version_list = get_version_list()
    if version_list is None:
        logger.error("MD_FILES_DIR not found. Current path is {}".format(config.MD_FILES_DIR))
        return JsonResponse({"result": False, "code": -1, "message": _("访问出错，请联系管理员。"), "data": None})
    response = {
        "result": True,
        "code": 0,
        "message": _("日志列表获取成功"),
        "data": version_list,
    }
    return JsonResponse(response)


@latest_read_record
def get_version_log_detail(request):
    """获取单条版本日志转换结果"""
    log_version = request.GET.get("log_version")
    html_text = get_parsed_html(log_version)
    if html_text is None:
        logger.error("md file not found or log version not valid. Log version is {}".format(log_version))
        response = {
            "result": False,
            "code": -1,
            "message": _("日志版本文件没找到，请联系管理员"),
            "data": None,
        }
        return JsonResponse(response)
    response = {"result": True, "code": 0, "message": _("日志详情获取成功"), "data": html_text}
    return JsonResponse(response)


def has_user_read_latest(request):
    """查询当前用户是否看过最新版本日志"""
    username = request.user.username
    has_latest_read = VersionLogVisited.objects.has_visit_latest(username, config.LATEST_VERSION)
    return JsonResponse(
        {
            "result": True,
            "code": 0,
            "message": "",
            "data": {
                "latest_version": config.LATEST_VERSION,
                "has_read_latest": has_latest_read,
            },
        }
    )
