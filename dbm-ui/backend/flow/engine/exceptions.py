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
from typing import Any

from django.utils.translation import ugettext as _

from backend.exceptions import AppBaseException


class PipelineError(Exception):
    def __init__(self, err_info: Any):
        super().__init__()
        self.err_info = err_info

    def __str__(self):
        return self.err_info


class ServiceDoesNotApply(AppBaseException):
    MESSAGE = _("组件服务未部署")
