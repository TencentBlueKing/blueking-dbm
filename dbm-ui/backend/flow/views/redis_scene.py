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

from backend.db_meta.enums import ClusterType
from backend.flow.engine.controller.redis import RedisController
from backend.flow.views.base import FlowTestView

logger = logging.getLogger("flow")


class RedisClusterCompleteReplaceSceneApiView(FlowTestView):
    """
    /apis/v1/flow/scene/cutoff/redis_cluster
    params:
    {
        "bk_biz_id": 3,
        "uid": "2022051612120001",
        "created_by":"vitox",
        "ticket_type":"REDIS_CLUSTER_CUTOFF",
        "infos": [
            {
            "cluster_id": 1,
            "redis_proxy": [
                {
                    "old": {"ip": "2.2.a.4", "bk_cloud_id": 0, "bk_host_id": 123},
                    "new": {"ip": "2.2.a.4", "bk_cloud_id": 0, "bk_host_id": 123}
                }],
            "redis_slave": [
                {
                    "old": {"ip": "2.b.3.4", "bk_cloud_id": 0, "bk_host_id": 123},
                    "new": {"ip": "2.b.3.4", "bk_cloud_id": 0, "bk_host_id": 123}
                }],
            "redis_master": [
                {
                    "old": {"ip": "2.2.3.c", "bk_cloud_id": 0, "bk_host_id": 123},
                    "new": [{"ip": "2.2.3.c", "bk_cloud_id": 0, "bk_host_id": 123},]
                }]
            }
        ]
    }
    """

    @staticmethod
    def post(request):
        root_id = uuid.uuid1().hex
        RedisController(root_id=root_id, ticket_data=request.data).redis_cluster_cutoff_scene()
        return Response({"root_id": root_id})


class RedisInstallDbmonSceneApiView(FlowTestView):
    """
    /apis/v1/flow/scene/install/dbmon
    params:
    {
      "bk_biz_id":"", # 必须有
      "bk_cloud_id":11, # 必须有
      "hosts":[1.1.1.1,2.2.2.2],
      "ticket_type": "REDIS_INSTALL_DBMON"
    }
    """

    @staticmethod
    def post(request):
        root_id = uuid.uuid1().hex
        RedisController(root_id=root_id, ticket_data=request.data).redis_install_dbmon_scene()
        return Response({"root_id": root_id})
