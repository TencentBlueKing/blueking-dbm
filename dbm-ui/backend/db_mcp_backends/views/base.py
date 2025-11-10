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

from types import FunctionType

from backend.bk_web.viewsets import SystemViewSet


class BaseMCPView(SystemViewSet):
    @classmethod
    def _get_login_exempt_view_func(cls):
        func_list = []
        for x, y in cls.__dict__.items():
            if isinstance(y, FunctionType):
                func_list.append(x)
        return {"post": func_list}

    def get_permissions(self):
        return []
