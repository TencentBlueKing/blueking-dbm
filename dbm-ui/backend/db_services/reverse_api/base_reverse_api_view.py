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
from typing import Tuple

from django.utils.translation import ugettext as _
from rest_framework import permissions

from backend.bk_web.viewsets import SystemViewSet
from backend.db_meta.models import Machine
from backend.db_services.reverse_api.get_ip_from_request import get_bk_cloud_id, get_client_ip, get_nginx_ip
from backend.db_services.reverse_api.serializers import ReverseApiParamSerializer

logger = logging.getLogger("root")


class IPHasRegisteredPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        try:
            nginx_ip = get_nginx_ip(request)
            logger.debug(f"nginx_ip: {nginx_ip}")

            bk_cloud_id = get_bk_cloud_id(request)
            logger.debug(f"bk_cloud_id: {bk_cloud_id}")

            client_ip = get_client_ip(request)
            Machine.objects.get(ip=client_ip, bk_cloud_id=bk_cloud_id)

            logger.debug(f"client_ip: {client_ip}")
        except Exception as e:  # noqa
            # if not found:
            raise Exception(_("访问受限，不存在于DBM平台 {}".format(e)))

        return True

    def has_object_permission(self, request, view, obj):
        return self.has_permission(request, view)


class BaseReverseApiView(SystemViewSet):
    serializer_class = ReverseApiParamSerializer

    @classmethod
    def _get_login_exempt_view_func(cls):
        return {
            "get": [
                x
                for x, y in cls.__dict__.items()
                if isinstance(y, FunctionType) and getattr(y, "is_reverse_api", False)
            ]
        }

    def get_permissions(self):
        return [IPHasRegisteredPermission()]

    def get_api_params(self) -> Tuple[int, str, int]:
        """
        return request bk_cloud_id, ip, port param
        """
        data = self.params_validate(self.get_serializer_class())

        ip = data.get("ip")
        bk_cloud_id = data.get("bk_cloud_id")
        port = data.get("port")

        return bk_cloud_id, ip, port
