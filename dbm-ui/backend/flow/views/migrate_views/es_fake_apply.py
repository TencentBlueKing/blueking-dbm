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

from django.utils.translation import ugettext as _
from rest_framework.response import Response

from backend.flow.engine.controller.es import EsController
from backend.flow.views.base import FlowTestView, MigrateFlowView

logger = logging.getLogger("root")


class FakeInstallEsSceneApiView(MigrateFlowView):
    """
    api: /apis/v1/flow/scene/fake_install_es
    params:
    {
        "bk_biz_id": 2005000002,
        "remark": "测试创建es集群",
        "ticket_type": "ES_APPLY",
        "cluster_name": "viper-cluster",
        "cluster_alias": "测试集群",
        "ip_source": "manual_input",
        "city_code": "深圳",
        "db_app_abbr": "blueking",
        "db_version": "7.10.2",
        "username": "username",
        "password": "password",
        "http_port": 9200,
        "uid":"2111"
        "created_by": "rtx",
        "domain": "es.viper-cluster.blueking.db",
        "nodes": {
            "hot": [
                {"ip": "127.0.0.1", "bk_cloud_id": 0, "instance_num": 1}
            ],
            "cold": [
                {"ip": "127.0.0.2", "bk_cloud_id": 0, "instance_num": 1}
            ],
            "client": [
                {"ip": "127.0.0.3", "bk_cloud_id": 0}
            ],
            "master": [
                {"ip": "127.0.0.4", "bk_cloud_id": 0},
                {"ip": "127.0.0.5", "bk_cloud_id": 0},
                {"ip": "127.0.0.6", "bk_cloud_id": 0}
            ]
        }
    }
    """

    def post(self, request):
        logger.info(_("开始部署ES场景"))

        root_id = uuid.uuid1().hex
        logger.info("define root_id: {}".format(root_id))
        EsController(root_id=root_id, ticket_data=request.data).es_fake_apply_scene()
        return Response({"root_id": root_id})
