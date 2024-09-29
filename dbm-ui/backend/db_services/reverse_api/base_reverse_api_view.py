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

from django.utils.translation import ugettext as _
from rest_framework import permissions

from backend.bk_web.viewsets import SystemViewSet
from backend.db_meta.models import Machine

logger = logging.getLogger("root")


class IPHasRegisteredPermission(permissions.BasePermission):
    @staticmethod
    def get_client_ip(request):
        x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
        if x_forwarded_for:
            ip = x_forwarded_for.split(",")[0]
        else:
            ip = request.META.get("REMOTE_ADDR")
        return ip

    def has_permission(self, request, view):
        client_ip = self.get_client_ip(request)
        found = Machine.objects.filter(ip=client_ip).exists()

        logger.debug(f"client_ip: {client_ip}, found: {found}")
        if not found:
            raise Exception(_("访问IP:{}受限，不存在于DBM平台").format(client_ip))
        return True

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)


class BaseReverseApiView(SystemViewSet):
    def get_permissions(self):
        return [IPHasRegisteredPermission()]
