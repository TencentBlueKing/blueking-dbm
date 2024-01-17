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

from backend.flow.engine.controller.mysql import MySQLController
from backend.flow.views.base import FlowTestView
from backend.utils.basic import generate_root_id

logger = logging.getLogger("root")


class InstallMySQLHASceneApiView(FlowTestView):
    """
        api: /apis/v1/flow/scene/install_mysql_ha
        params:
        (手输ip模式，单机单实例部署)
        {
        "uid": "000",
        "created_by": "xxxx",
        "bk_biz_id": "xxx",
        "module": "xxx",
        "city": "xxx",
        "spec": "S5.MEDIUM4",
        "start_mysql_port": 20000,
        "start_proxy_port": 10000,
        "inst_num": 1,
        "ticket_type": "MYSQL_HA_APPLY",
        "db_version": "MySQL-5.7",
        "charset": "utf8",
        "ip_source": "manual_input",
        "apply_infos":[
            {
                "mysql_ip_list": [{"ip": "1.1.1.1", "bk_cloud_id": 0},{"ip": "2.2.2.2", "bk_cloud_id": 0}],
                "proxy_ip_list": [{"ip": "3.3.3.3", "bk_cloud_id": 0},{"ip": "4.4.4.4, "bk_cloud_id": 0}],
                "clusters":[
                    {
                        "name": "test",
                        "master": "gamedb.test.db",
                        "slave": "gamedb.test.dr"
                    }
                ]
            }

        ]
    }
    """

    def post(self, request):
        # logger.info("开始部署tenDB HA场景")
        root_id = generate_root_id()
        test = MySQLController(root_id=root_id, ticket_data=request.data)
        test.mysql_ha_apply_scene()
        return Response({"root_id": root_id})
