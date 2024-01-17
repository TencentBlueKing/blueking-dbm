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

from rest_framework.response import Response

from backend.flow.engine.controller.pulsar import PulsarController
from backend.flow.views.base import FlowTestView
from backend.utils.basic import generate_root_id

logger = logging.getLogger("root")


class InstallPulsarSceneApiView(FlowTestView):
    """
    api: /apis/v1/flow/scene/install_pulsar
    params:
    {
        "username": "username",
        "uid": 352,
        "ticket_type": "PULSAR_APPLY",
        "retention_hours": 2,
        "replication_num": 2,
        "ack_quorum": 1,
        "port": 9200,
        "password": "password",
        "partition_num": 2,
        "nodes": {
            "zookeeper": [
                {
                    "ip": "127.0.0.x",
                    "bk_cloud_id": 0,
                    "bk_host_id": 1,
                    "bk_biz_id": 2005000002
                },
                {
                    "ip": "127.0.0.x",
                    "bk_cloud_id": 0,
                    "bk_host_id": 2,
                    "bk_biz_id": 2005000002
                },
                {
                    "ip": "127.0.0.x",
                    "bk_cloud_id": 0,
                    "bk_host_id": 3,
                    "bk_biz_id": 2005000002
                }
            ],
            "broker": [
                {
                    "ip": "127.0.0.x",
                    "bk_cloud_id": 0,
                    "bk_host_id": 4,
                    "bk_biz_id": 2005000002
                },
                {
                    "ip": "127.0.0.x",
                    "bk_cloud_id": 0,
                    "bk_host_id": 5,
                    "bk_biz_id": 2005000002
                }
            ],
            "bookkeeper": [
                {
                    "ip": "127.0.0.x",
                    "bk_cloud_id": 0,
                    "bk_host_id": 4,
                    "bk_biz_id": 2005000002
                },
                {
                    "ip": "127.0.0.x",
                    "bk_cloud_id": 0,
                    "bk_host_id": 5,
                    "bk_biz_id": 2005000002
                }
            ]
        },
        "ip_source": "manual_input",
        "db_version": "2.10.1",
        "created_by": "aaa",
        "cluster_name": "pulsar-cluster",
        "cluster_alias": "测试集群",
        "city_code": "深圳",
        "bk_biz_id": 2000000002,
        "db_app_abbr": "blueking"
    }
    """

    def post(self, request):
        logger.info("Begin apply Pulsar scene")

        root_id = generate_root_id()
        logger.info("define root_id: {}".format(root_id))
        PulsarController(root_id=root_id, ticket_data=request.data).pulsar_apply_scene()
        return Response({"root_id": root_id})
