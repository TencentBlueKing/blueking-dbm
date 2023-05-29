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
import uuid

from rest_framework.response import Response

from backend.flow.engine.controller.pulsar import PulsarController
from backend.flow.views.base import FlowTestView

logger = logging.getLogger("root")


class ScaleUpPulsarSceneApiView(FlowTestView):
    """
    api: /apis/v1/flow/scene/scale_up_pulsar
    params:
    {
        "bk_biz_id": 2005000002,
        "remark": "测试扩容pulsar集群",
        "ticket_type": "PULSAR_SCALE_UP",
        "cluster_id": 123,
        "created_by": "user",
        "nodes": {
            "broker": [
                {"ip": "127.0.0.6", "bk_cloud_id": 0},
                {"ip": "127.0.0.7", "bk_cloud_id": 0}
            ],
            "bookkeeper": [
                {"ip": "127.0.0.8", "bk_cloud_id": 0},
                {"ip": "127.0.0.9", "bk_cloud_id": 0}
            ],
        }
    }
    """

    def post(self, request):
        logger.info("Begin Scale up Pulsar scene")

        root_id = uuid.uuid1().hex
        logger.info("define root_id: {}".format(root_id))
        PulsarController(root_id=root_id, ticket_data=request.data).pulsar_scale_up_scene()
        return Response({"root_id": root_id})
