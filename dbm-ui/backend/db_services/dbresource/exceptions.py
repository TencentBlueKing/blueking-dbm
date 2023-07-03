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


class ResourcePoolBaseException(AppBaseException):
    MODULE_CODE = ErrorCode.RESOURCE_POOL_CODE
    MESSAGE = _("资源池服务异常")


class ResourceApplyException(ResourcePoolBaseException):
    ERROR_CODE = "001"
    MESSAGE = _("资源池申请资源异常")
    MESSAGE_TPL = _("资源池申请资源异常")


class SpecOperateException(ResourcePoolBaseException):
    ERROR_CODE = "002"
    MESSAGE = _("规格操作失败")
    MESSAGE_TPL = _("规格操作失败")
