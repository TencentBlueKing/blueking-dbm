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

from backend.bk_web.swagger import common_swagger_auto_schema
from backend.db_proxy.reverse_api.base_reverse_api_view import BaseReverseApiView
from backend.db_proxy.reverse_api.common.impl import list_nginx_addrs
from backend.db_proxy.reverse_api.decorators import reverse_api

logger = logging.getLogger("root")


class CommonReverseApiView(BaseReverseApiView):
    @common_swagger_auto_schema(operation_summary=_("获取NGINX 地址"))
    @reverse_api(url_path="list_nginx_addrs")
    def list_nginx_addrs(self, request, *args, **kwargs):
        """
        返回特定云区域的 NGINX 地址 列表
        param: bk_cloud_id: int
        return: ["ip1:90", "ip2:90", ...]
        """
        bk_cloud_id, _, _ = self.get_api_params()
        logger.info(f"bk_cloud_id: {bk_cloud_id}")
        res = list_nginx_addrs(bk_cloud_id=bk_cloud_id)
        logger.info(f"res: {res}")

        return JsonResponse(
            {
                "result": True,
                "code": 0,
                "data": res,
                "message": "",
                "errors": None,
            }
        )
