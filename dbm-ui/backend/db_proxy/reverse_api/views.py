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

from django.http import JsonResponse
from django.utils.translation import ugettext_lazy as _

from backend.bk_web.swagger import common_swagger_auto_schema
from backend.db_proxy.models import DBCloudProxy
from backend.db_proxy.reverse_api.base_reverse_api_view import BaseReverseApiView
from backend.db_proxy.reverse_api.decorators import reverse_api


class CommonReverseApiView(BaseReverseApiView):
    @common_swagger_auto_schema(operation_summary=_("云区域NGINX列表"))
    @reverse_api(url_path="list_cloud_nginx")
    def list_cloud_nginx(self, request):
        bk_cloud_id, ip, port = self.get_api_params()

        res = []
        for ele in DBCloudProxy.objects.filter(bk_cloud_id=bk_cloud_id):
            res.append(
                {
                    "internal-address": ele.internal_address,
                    "external-address": ele.external_address,
                }
            )

        return JsonResponse({"result": True, "code": 0, "data": res, "message": "", "errors": None})
