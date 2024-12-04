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

from django.utils.translation import ugettext_lazy as _

from backend.exceptions import AppBaseException, ErrorCode


class ExternalProxyBaseException(AppBaseException):
    MODULE_CODE = ErrorCode.EXTERNAL_PROXY_CODE
    MESSAGE = _("外部路由转发异常")


class ExternalUserNotExistException(ExternalProxyBaseException):
    ERROR_CODE = "001"
    MESSAGE = _("外部用户不存在")


class ExternalRouteInvalidException(ExternalProxyBaseException):
    ERROR_CODE = "002"
    MESSAGE = _("转发路由非法")


class ExternalClusterIdInvalidException(ExternalProxyBaseException):
    ERROR_CODE = "003"
    MESSAGE = _("转发集群请求非法")
    MESSAGE_TPL = _("转发集群[{cluster_id}]请求非法")
