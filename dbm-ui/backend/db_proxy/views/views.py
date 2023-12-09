# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2022 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""

import logging

from backend.bk_web import viewsets
from backend.iam_app.handlers.drf_perm import ProxyPassPermission

logger = logging.getLogger("root")


class BaseProxyPassViewSet(viewsets.SystemViewSet):
    """透传视图的基本视图"""

    global_login_exempt = True

    def get_permissions(self):
        return [ProxyPassPermission()]
