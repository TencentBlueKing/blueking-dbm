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

from django.utils.translation import gettext as _
from rest_framework.response import Response

from backend.flow.engine.controller.surrealdb import SurrealDBController
from backend.flow.views.base import FlowTestView
from backend.utils.basic import generate_root_id

logger = logging.getLogger("root")


class RestartSurrealDBSceneApiView(FlowTestView):
    """
    api: /apis/v1/flow/scene/restart_k8s_surrealdb
    params:
    {
        "cluster_id": 65,
        "ticket_type": "K8S_SURREALDB_RESTART",
        "bk_biz_id": 10,
        "created_by": "admin"
    }
    """

    def post(self, request):
        logger.info(_("开始重启 K8s SurrealDB 场景"))

        root_id = generate_root_id()
        logger.info(f"define root_id: {root_id}")
        SurrealDBController(root_id=root_id, ticket_data=request.data).surrealdb_restart_scene()
        return Response({"root_id": root_id})
