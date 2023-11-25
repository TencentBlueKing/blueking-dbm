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
from rest_framework import serializers
from rest_framework.response import Response

from backend.bk_web.swagger import common_swagger_auto_schema
from backend.flow.engine.controller.influxdb import InfluxdbController
from backend.flow.views.base import FlowTestView, MigrateFlowView

logger = logging.getLogger("root")


class FakeInstallInfluxdbSceneApiView(MigrateFlowView):
    """
    api: /apis/v1/flow/scene/fake_install_influxdb
    params:
    {
        "uid": "2022921034",
        "created_by": "xxx",
        "bk_biz_id": "2005000002",
        "ticket_type": "INFLUXDB_APPLY",
        "city_code": "\u6df1\u5733",
        "version": "2.4.0",
        "port": 8080,
      "username": "username",
      "password": "password",
          "nodes": {
            "influxdb": [
              {
                "ip": "xxx.xxx.xx.x",
                "bk_cloud_id": 0
              },
              {
                "ip": "xxx.xxx.xx.x",
                "bk_cloud_id": 0
              },
              {
                "ip": "xxx.xxx.xx.x",
                "bk_cloud_id": 0
              }
            ]
          },
    }
    """

    @common_swagger_auto_schema(request_body=serializers.Serializer())
    def post(self, request):
        logger.info(_("开始部署influxdb场景"))
        root_id = uuid.uuid1().hex
        logger.info("define root_id: {}".format(root_id))
        InfluxdbController(root_id=root_id, ticket_data=request.data).influxdb_fake_apply_scene()
        return Response({"root_id": root_id})
