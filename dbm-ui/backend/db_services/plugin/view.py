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

from backend.bk_web import viewsets
from backend.iam_app.handlers.drf_perm.base import RejectPermission

logger = logging.getLogger("root")


class BaseOpenAPIViewSet(viewsets.SystemViewSet):
    """openapi 视图基类"""

    def get_default_permission_class(self) -> list:
        # 默认访问openapi的客户端都通过了网关jwt认证
        permission_class = [] if self.request.is_bk_jwt() else [RejectPermission()]
        return permission_class
