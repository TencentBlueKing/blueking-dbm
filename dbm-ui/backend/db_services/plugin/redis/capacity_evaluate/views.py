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
import traceback

from django.http import JsonResponse
from django.utils.translation import gettext_lazy as _
from rest_framework import status
from rest_framework.decorators import action

from backend.bk_web.swagger import common_swagger_auto_schema
from backend.db_services.plugin.redis.capacity_evaluate.serializers import CapacityEvaluateSLZ
from backend.db_services.plugin.view import BaseOpenAPIViewSet
from backend.db_services.redis.capacity_evaluate_service.api.evaluate_api import EvaluateAPI
from backend.db_services.redis.capacity_evaluate_service.services import capacity_cal
from backend.iam_app.handlers.drf_perm.base import DBManagePermission


# viewsets.GenericViewSet require data
class CapacityEvaluateViewSet(BaseOpenAPIViewSet):
    """capacity evaluate viewset"""

    action_permission_map = {}
    default_permission_class = [DBManagePermission()]
    serializer_class = CapacityEvaluateSLZ
    """
    detail=True 时，url 中需要传入 id 参数，否则会报错
    """

    @common_swagger_auto_schema(
        operation_summary=_("Redis容量评估"),
        responses={status.HTTP_200_OK: CapacityEvaluateSLZ()},
    )
    @action(detail=False, methods=["POST"])
    def v1(self, request):
        """容量评估 view.py -> api.py -> service.py"""
        out = {}
        try:
            self.serializer_class(data=request.data).is_valid(raise_exception=True)
            out = EvaluateAPI().do_evaluate(request)
        except Exception as e:
            traceback.print_exc()
            out.update({"result_code": 3, "result_status": "error", "result_msg": "%s" % str(e)})
        return JsonResponse(out)

    @common_swagger_auto_schema(
        operation_summary=_("获取集群规格"),
        responses={status.HTTP_200_OK: CapacityEvaluateSLZ()},
    )
    @action(detail=False, methods=["POST"])
    def get_cluster_spec(self, request):
        bk_biz_id = request.data.get("action_info").get("bk_biz_id")
        out = {}
        try:
            self.serializer_class(data=request.data).is_valid(raise_exception=True)
            out = capacity_cal.CapacityCalculateService.get_cluster_info(bk_biz_id, 25)
        except Exception:
            traceback.print_exc()
            out.update(
                {
                    "request": request.data.get("req")[0],
                    "bk_biz_id": bk_biz_id,
                    "result_code": 3,
                    "result_status": "error",
                    "result_msg": "error : %s" % traceback.format_exc(),
                }
            )
        return JsonResponse(out, safe=False, json_dumps_params={"default": lambda o: o.__dict__()})
