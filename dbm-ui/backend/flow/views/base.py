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

from blueapps.account.decorators import login_exempt
from django.conf import settings
from django.utils.translation import ugettext as _
from rest_framework.exceptions import PermissionDenied
from rest_framework.permissions import AllowAny
from rest_framework.views import APIView

logger = logging.getLogger("root")


class FlowTestView(APIView):
    permission_classes = [AllowAny]

    @classmethod
    def as_view(cls, **initkwargs):
        # 对透传接口增加登录豁免
        view_func = super().as_view(**initkwargs)
        return login_exempt(view_func)

    def get_permissions(self):
        # 暂时只对超级用户或者DEBUG模式开放
        """
        if not self.request.user.is_superuser and not settings.DEBUG:
            raise PermissionDenied(_("权限不足，无法访问!"))
        """
        return []
