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
import re

from django.http import JsonResponse
from django.utils.translation import gettext_lazy as _

from backend.version_log import config
from backend.version_log.models import VersionLogVisited
from backend.version_log.utils import get_md_files_dir_with_language_code, get_parsed_html, get_version_list

logger = logging.getLogger(__name__)


def validate_log_version(log_version: str) -> bool:
    """
    校验log_version参数，防止路径穿越攻击
    :param log_version: 版本号参数
    :return: True表示合法，False表示非法
    """
    if not log_version:
        return False

    if not log_version or len(log_version) > 50:  # 添加长度限制
        return False

    # 只允许字母、数字、下划线、连字符、点号
    if not re.match(r"^[a-zA-Z0-9._-]+$", log_version):
        return False
    # 允许的字符：字母、数字、下划线、点、连字符
    # 支持格式：V1.5.0, V1.5.0-alpha.78, V1.5.0-beta.1, V1.5.0-rc.1, V1.5.0_20240101等
    pattern = r"^[vV]?\d+(?:\.\d+)*(?:[-_][a-zA-Z]+(?:\.\d+)?)?$"

    # 检查是否包含路径穿越字符
    # 检查单个危险字符：点号、斜杠、反斜杠、冒号等
    dangerous_chars = ["..", "/", "\\", ":", "*", "?", '"', "<", ">", "|"]

    if any(char in log_version for char in dangerous_chars):
        return False
    # 检查是否符合命名规范
    return bool(re.match(pattern, log_version))


def latest_read_record(view_func):
    @functools.wraps(view_func)
    def wrapper(request, *args, **kwargs):
        visit_log_version = request.GET.get("log_version") or request.POST.get("log_version")
        if visit_log_version and not validate_log_version(visit_log_version):
            logger.warning(f"Invalid log_version detected: {visit_log_version}, username: {request.user.username}")
            return JsonResponse({"result": False, "code": -1, "message": _("版本参数不合法"), "data": None})

        if config.LATEST_VERSION_INFORM and visit_log_version == config.LATEST_VERSION:
            VersionLogVisited.objects.update_visit_version(request.user.username, visit_log_version)

        return view_func(request, *args, **kwargs)

    return wrapper


def version_logs_list(request):
    """获取版本日志列表"""
    language_code = getattr(request, "LANGUAGE_CODE", None)
    version_list = get_version_list(language_code)
    if version_list is None:
        md_files_dir = get_md_files_dir_with_language_code(language_code)
        logger.error("MD_FILES_DIR not found. Current path is {}".format(md_files_dir))
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
    language_code = getattr(request, "LANGUAGE_CODE", None)
    log_version = request.GET.get("log_version")
    # 再次校验参数，确保安全
    if not validate_log_version(log_version):
        logger.warning(f"Invalid log_version in get_version_log_detail: {log_version}")
        return JsonResponse({"result": False, "code": -1, "message": _("版本参数不合法"), "data": None})

    html_text = get_parsed_html(log_version, language_code)
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
