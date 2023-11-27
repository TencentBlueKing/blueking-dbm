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

from rest_framework import serializers
from rest_framework.response import Response

from backend.bk_web.swagger import common_swagger_auto_schema
from backend.flow.engine.controller.pulsar import PulsarController
from backend.flow.views.base import MigrateFlowView

logger = logging.getLogger("root")


class FakeInstallPulsarSceneApiView(MigrateFlowView):
    """
    api: /apis/v1/flow/scene/fake_install_pulsar
    params:
    {
        "bk_biz_id": 111,
        "remark": "部署pulsar集群",
        "ticket_type": "PULSAR_APPLY",
        "username": "username",
        "password": "password",
        "ip_source": "manual_input",
        "db_version": "2.10.1",
        "retention_minutes": 2,
        "replication_num": 2,
        "ensemble_size": 3,
        "ack_quorum": 1,
        "port": 6650,
        "partition_num": 2,
        "cluster_name": "pulsartest",
        "cluster_alias": "测试虚拟上架集群",
        "city_code": "深圳",
        "bk_app_abbr": "xxxx",
        "bk_cloud_id": 0,
        "domain": "xxxx.test.test.test",
        "uid": 111,
        "created_by": "someone",
        "manager_ip": "127.0.0.1",
        "manager_port": 1234,
        "token": "xxxxx",
        "nodes": {
            "zookeeper": [
                {
                    "ip": "1.1.1.1",
                    "bk_cloud_id": 0,
                    "bk_host_id": 1,
                    "bk_biz_id": 111
                },
                {
                    "ip": "2.2.2.2",
                    "bk_cloud_id": 0,
                    "bk_host_id": 2,
                    "bk_biz_id": 111
                },
                {
                    "ip": "3.3.3.3",
                    "bk_cloud_id": 0,
                    "bk_host_id": 3,
                    "bk_biz_id": 111
                }
            ],
            "broker": [
                {
                    "ip": "4.4.4.4",
                    "bk_cloud_id": 0,
                    "bk_host_id": 4,
                    "bk_biz_id": 111
                }
            ],
            "bookkeeper": [
                {
                    "ip": "5.5.5.5",
                    "bk_cloud_id": 0,
                    "bk_host_id": 5,
                    "bk_biz_id": 111
                },
                {
                    "ip": "6.6.6.6",
                    "bk_cloud_id": 0,
                    "bk_host_id": 6,
                    "bk_biz_id": 111
                }
            ]
        }
    }
    """

    @common_swagger_auto_schema(request_body=serializers.Serializer())
    def post(self, request):
        logger.info("Begin fake apply Pulsar scene")

        root_id = uuid.uuid1().hex
        logger.info("define root_id: {}".format(root_id))
        PulsarController(root_id=root_id, ticket_data=request.data).pulsar_fake_apply_scene()
        return Response({"root_id": root_id})
