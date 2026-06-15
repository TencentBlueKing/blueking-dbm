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

from backend.flow.engine.controller.qdrant import QdrantController
from backend.flow.views.base import FlowTestView
from backend.utils.basic import generate_root_id

logger = logging.getLogger("root")


class InstallK8sQdrantSceneApiView(FlowTestView):
    """
    api: /apis/v1/flow/scene/install_k8s_qdrant
    params:
    {
        "bk_biz_id": 2005000002,
        "ticket_type": "K8S_QDRANT_HA_APPLY",
        "db_app_abbr": "blueking",
        "bk_biz_name": "蓝鲸",
        "bk_cloud_id": 0,
        "bk_cloud_region": "test-region",
        "city_code": "深圳",
        "cluster_type": "qdrant",
        "cluster_name": "test-qdrant",
        "cluster_alias": "测试集群",
        "k8s_cluster_name": "test-k8s",
        "major_version": "1",
        "db_version": "1.7.4",
        "remark": "测试创建qdrant集群",
        "component_list": [
           {
            "component_name": "qdrant",
            "replicas": 1,
            "request_cpu": "1",
            "request_memory": "1Gi",
            "storage": "100Gi"
            }
        ]
    }
    """

    def post(self, request):
        logger.info(_("开始部署K8s Qdrant场景"))

        root_id = generate_root_id()
        logger.info("define root_id: {}".format(root_id))
        QdrantController(root_id=root_id, ticket_data=request.data).qdrant_apply_scene()
        return Response({"root_id": root_id})
