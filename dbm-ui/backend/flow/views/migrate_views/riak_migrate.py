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

from django.utils.translation import ugettext as _
from rest_framework import serializers
from rest_framework.response import Response

from backend.bk_web.swagger import common_swagger_auto_schema
from backend.flow.engine.controller.riak import RiakController
from backend.flow.views.base import MigrateFlowView
from backend.utils.basic import generate_root_id

logger = logging.getLogger("root")


class RiakClusterMigrateApiView(MigrateFlowView):
    """
        api: /apis/v1/flow/scene/riak_cluster_migrate
        params:
    {
        "bk_biz_id": xxx,
        "remark": "迁移riak集群",
        "ticket_type": "RIAK_CLUSTER_MIGRATE",
        "db_module_name": "mixed",
        "db_module_id": xxx,
        "ip_source": "manual_input",
        "bk_cloud_id": 0,
        "db_app_abbr": "xxx",
        "db_version": "2.2",
        "uid": "xxx",
        "created_by": "rtx",
        "clusters": [
            {
                "cluster_name": "test.mixed",
                "domain": "test.mixed",
                "cluster_alias": "测试集群",
                "city_code": "深圳",
                "nodes": [
                    {
                        "ip": "127.0.0.1",
                    },
                    {
                        "ip": "127.0.0.1",
                    },
                    {
                        "ip": "127.0.0.1",
                    }
                ]
            }
        ]
    }
    """

    @common_swagger_auto_schema(request_body=serializers.Serializer())
    def post(self, request):
        logger.info(_("开始迁移RIAK场景"))

        root_id = generate_root_id()
        logger.info("define root_id: {}".format(root_id))
        RiakController(root_id=root_id, ticket_data=request.data).riak_cluster_migrate_scene()
        return Response({"root_id": root_id})
