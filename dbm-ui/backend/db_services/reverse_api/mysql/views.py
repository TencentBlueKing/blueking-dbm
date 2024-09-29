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

from django.db.models import Q
from django.http import JsonResponse
from django.utils.translation import ugettext_lazy as _

from backend.bk_web.swagger import common_swagger_auto_schema
from backend.db_meta.enums import AccessLayer
from backend.db_meta.models import Machine, ProxyInstance, StorageInstance
from backend.db_services.reverse_api.base_reverse_api_view import BaseReverseApiView
from backend.db_services.reverse_api.decorators import reverse_api

logger = logging.getLogger("root")


class MySQLReverseApiView(BaseReverseApiView):
    @common_swagger_auto_schema(operation_summary=_("获取实例基本信息"))
    @reverse_api(url_path="list_instance_info")
    def list_instance_info(self, request, *args, **kwargs):
        bk_cloud_id, ip, port_list = self.get_api_params()
        logger.info(f"bk_cloud_id: {bk_cloud_id}, ip: {ip}, port:{port_list}")

        m = Machine.objects.get(ip=ip, bk_cloud_id=bk_cloud_id)
        q = Q()
        q |= Q(**{"machine": m})

        if port_list:
            q &= Q(**{"port__in": port_list})

        res = []
        if m.access_layer == AccessLayer.PROXY:
            for i in ProxyInstance.objects.filter(q):
                res.append({"ip": i.machine.ip, "port": i.port, "phase": i.phase, "status": i.status})
        else:
            for i in StorageInstance.objects.filter(q):
                res.append({"ip": i.machine.ip, "port": i.port, "phase": i.phase, "status": i.status})

        logger.info(f"instance info: {res}")
        return JsonResponse(
            {
                "result": True,
                "code": 0,
                "data": res,
                "message": "",
                "errors": None,
            }
        )
