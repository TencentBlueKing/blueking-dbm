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
from django.utils.translation import gettext as _
from rest_framework.decorators import action
from rest_framework.response import Response

from backend.bk_web import viewsets
from backend.bk_web.swagger import common_swagger_auto_schema
from backend.db_services.mysql.dts.handlers import MySQLDtsMigrateHandler
from backend.db_services.mysql.dts.serializers import ResetDtsTaskSerializer
from backend.iam_app.handlers.drf_perm.base import DBManagePermission

SWAGGER_TAG = "db_services/mysql/dts"


class MySQLDtsMigrateViewSet(viewsets.SystemViewSet):
    default_permission_class = [DBManagePermission()]

    @common_swagger_auto_schema(
        operation_summary=_("重置 DTS 任务（删除后重建并从 Dump 重跑，不清目标业务数据）"),
        request_body=ResetDtsTaskSerializer(),
        tags=[SWAGGER_TAG],
    )
    @action(methods=["POST"], detail=False, serializer_class=ResetDtsTaskSerializer)
    def reset_task(self, request, *args, **kwargs):
        # 手写 as_view 时 @action(serializer_class=...) 不会生效，须显式传入
        data = self.params_validate(ResetDtsTaskSerializer)
        result = MySQLDtsMigrateHandler.reset_task(
            task_name=data["task_name"],
            dts_cluster_id=data["dts_cluster_id"],
        )
        return Response(result)
