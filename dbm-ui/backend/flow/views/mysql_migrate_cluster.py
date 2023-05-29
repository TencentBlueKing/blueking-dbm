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

from backend.flow.engine.controller.mysql import MySQLController
from backend.flow.views.base import FlowTestView

logger = logging.getLogger("root")


class MigrateMysqlClusterSceneApiView(FlowTestView):
    """
    {
    "uid":"2022051612120002",
    "created_by":"xxxx",
    "bk_biz_id":"152",
    "module":1,
    "ticket_type":"MYSQL_MIGRATE_CLUSTER",
    "infos":[
        {
            # 必须是同机器的clusterid
            "cluster_ids":[
                1,2,3,4
            ],
            "new_master_ip":"xxx",
            "new_slave_ip":xxx",
            "backup_source":"local"
        }
    ]
    }
    """

    def post(self, request):
        logger.info(_("开始重建slave"))
        root_id = uuid.uuid1().hex
        logger.info("define root_id: {}".format(root_id))
        mysql_controller_new = MySQLController(root_id, request.data)
        mysql_controller_new.mysql_migrate_cluster_scene()
        return Response({"root_id": root_id})
