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
from types import FunctionType

from django.utils.translation import ugettext as _
from rest_framework import permissions
from rest_framework.request import Request

from backend import env
from backend.bk_web.viewsets import SystemViewSet
from backend.db_meta.models import Machine
from backend.db_proxy.reverse_api.helper import get_client_ip, validate_nginx_ip

logger = logging.getLogger("root")


class IPHasRegisteredPermission(permissions.BasePermission):
    def has_permission(self, request: Request, view):
        if env.DEBUG_REVERSE_API:
            logger.info("in debug mode")
        else:
            logger.info(
                f"[checking reverse-api-perm] request path: {request.path},"
                f"REMOTE_ADDR: {request.META.get('REMOTE_ADDR')},"
                f"HTTP_X_FORWARDED_FOR: {request.META.get('HTTP_X_FORWARDED_FOR')}"
            )

        try:
            bk_cloud_id = int(request.query_params.get("bk_cloud_id"))

            if not env.DEBUG_REVERSE_API:
                validate_nginx_ip(bk_cloud_id, request)

            client_ip = get_client_ip(request)
            Machine.objects.get(ip=client_ip, bk_cloud_id=bk_cloud_id)

        except Exception as e:  # noqa
            # if not found:
            raise Exception(_("访问受限，不存在于DBM平台 {}".format(e)))

        return True

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)


class BaseReverseApiView(SystemViewSet):
    @classmethod
    def _get_login_exempt_view_func(cls):
        r = {}
        for x, y in cls.__dict__.items():
            if isinstance(y, FunctionType):
                m = getattr(y, "reverse_api_method", None)
                if m in ["get", "post"]:
                    if m in r:
                        r[m].append(x)
                    else:
                        r[m] = [x]

        return r

    def get_permissions(self):
        return [IPHasRegisteredPermission()]
