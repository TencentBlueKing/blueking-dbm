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

from django.http import JsonResponse
from django.utils.translation import ugettext_lazy as _
from rest_framework.decorators import action

from backend.bk_web.swagger import common_swagger_auto_schema
from backend.components import DBPrivManagerApi
from backend.db_meta.enums import AccessLayer
from backend.db_meta.models import Machine
from backend.db_services.reverse_api.base_reverse_api_view import BaseReverseApiView
from backend.db_services.reverse_api.decorators import reverse_api
from backend.db_services.reverse_api.mysql.serializers import MySQLReverseApiParamSerializer
from backend.flow.consts import DEFAULT_INSTANCE, MySQLPrivComponent, UserName

logger = logging.getLogger("root")


class MySQLReverseApiView(BaseReverseApiView):
    @classmethod
    def _get_login_exempt_view_func(cls):
        return {
            "post": [],
            "put": [],
            "get": [
                cls.list_instance_info.__name__,
                cls.get_runtime_account.__name__,
            ],
            "delete": [],
        }

    @common_swagger_auto_schema(operation_summary=_("获取实例基本信息"))
    @action(
        methods=["GET"],
        detail=False,
        url_path="list_instance_info",
        serializer_class=MySQLReverseApiParamSerializer,
    )
    @reverse_api
    def list_instance_info(self, request, *args, **kwargs):
        data = self.params_validate(self.get_serializer_class())

        ip = data.get("ip")
        bk_cloud_id = data.get("bk_cloud_id")

        logger.info(f"bk_cloud_id: {bk_cloud_id}, ip: {ip}")

        m = Machine.objects.get(ip=ip, bk_cloud_id=bk_cloud_id)
        if m.access_layer == AccessLayer.PROXY:
            pass
        else:
            pass
        return JsonResponse({"ip": ip})

    @common_swagger_auto_schema(operation_summary=_("反向获取DB系统账号"))
    @action(
        methods=["GET"],
        detail=False,
        url_path="get_runtime_account",
    )
    def get_runtime_account(self, request, *args, **kwargs):
        data = DBPrivManagerApi.get_runtime_account(
            {
                "instances": [DEFAULT_INSTANCE],
                "users": [
                    {"username": UserName.BACKUP.value, "component": MySQLPrivComponent.MYSQL.value},
                    {"username": UserName.MONITOR.value, "component": MySQLPrivComponent.MYSQL.value},
                    {"username": UserName.MONITOR_ACCESS_ALL.value, "component": MySQLPrivComponent.MYSQL.value},
                    {"username": UserName.OS_MYSQL.value, "component": MySQLPrivComponent.MYSQL.value},
                    {"username": UserName.REPL.value, "component": MySQLPrivComponent.MYSQL.value},
                    {"username": UserName.YW.value, "component": MySQLPrivComponent.MYSQL.value},
                    {"username": UserName.PARTITION_YW.value, "component": MySQLPrivComponent.MYSQL.value},
                ],
            }
        )
        return JsonResponse({"data": data})
