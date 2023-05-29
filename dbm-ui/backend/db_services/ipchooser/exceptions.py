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

from backend.core.exceptions import CoreBaseException


class IpChooserBaseException(CoreBaseException):
    MODULE_CODE = 3004


class SerValidationError(IpChooserBaseException):
    MESSAGE_TPL = _("参数校验失败")
    MESSAGE = _("参数校验失败")
    ERROR_CODE = 1


class TopoNotExistsError(IpChooserBaseException):
    MESSAGE_TPL = _("业务【bk_biz_id: {bk_biz_id}】拓扑不存在")
    MESSAGE = _("业务拓扑不存在")
    ERROR_CODE = 2
