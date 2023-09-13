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


class RestoreMysqlLocalRemoteSceneApiView(FlowTestView):
    """
     {
        "uid":"2022051612120002",
        "created_by":"xxxx",
        "bk_biz_id":"2005000194",
        "module":1,
        "ticket_type":"MYSQL_RESTORE_LOCAL_SLAVE",
        "slaves":[
            {
                "clusterid":3,
                "slave_ip":"xxxx",
                "slave_port":3306,
                "backup_source":"master",
                "force":false
            }
        ]
    }
    """

    def post(self, request):
        logger.info(_("开始原地重建slave"))
        root_id = uuid.uuid1().hex
        logger.info("define root_id: {}".format(root_id))
        mysql_controller_new = MySQLController(root_id, request.data)
        mysql_controller_new.mysql_restore_local_remote_scene()
        return Response({"root_id": root_id})
