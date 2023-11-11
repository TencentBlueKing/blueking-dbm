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

from backend.flow.engine.controller.hdfs import HdfsController
from backend.flow.views.base import MigrateFlowView

logger = logging.getLogger("root")


class FakeInstallHdfsSceneApiView(MigrateFlowView):
    """
    api: /apis/v1/flow/scene/fake_install_hdfs
    params:
    {
        "bk_biz_id": "2005000002",
        "remark": "测试创建hdfs集群",
        "ticket_type": "HDFS_APPLY",
        "cluster_name": "cluster_name",
        "cluster_alias": "cluster_alias"
        "city_code": "深圳",
        "db_app_abbr": "blueking",
        "db_version": "2.6.0-cdh5.4.11-tendataV0.2",
        "rpc_port": 9000
        "http_port": 50070,
        "uid":"2111"
        "created_by": "xxxx",
        "ip_source": "manual_input",
        "nodes": {
            "nn1": {"ip": "127.0.0.1", "hostname": "nn1-host-name"},
            "nn2": {"ip": "127.0.0.2", "hostname": "nn2-host-name"},
            "namenode": [
                {"ip": "127.0.0.1", "bk_cloud_id": 0},
                {"ip": "127.0.0.2", "bk_cloud_id": 0},
            ],
            "zookeeper": [
                {"ip": "127.0.0.3", "bk_cloud_id": 0},
                {"ip": "127.0.0.4", "bk_cloud_id": 0},
                {"ip": "127.0.0.5", "bk_cloud_id": 0}

            ],
            "datanode": [
                {"ip": "127.0.0.6", "bk_cloud_id": 0},
                {"ip": "127.0.0.7", "bk_cloud_id": 0}
            ]
        }
    }
    """

    def post(self, request):
        logger.info(_("开始部署hdfs场景"))
        root_id = uuid.uuid1().hex
        logger.info("define root_id: {}".format(root_id))
        HdfsController(root_id=root_id, ticket_data=request.data).hdfs_fake_apply_scene()
        return Response({"root_id": root_id})
