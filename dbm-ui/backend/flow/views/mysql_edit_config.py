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
from rest_framework.response import Response

from backend.flow.engine.controller.mysql import MySQLController
from backend.flow.views.base import FlowTestView
from backend.utils.basic import generate_root_id

logger = logging.getLogger("root")


class MysqlEditConfigSceneApiView(FlowTestView):
    """
    {
    "uid":"2022051612120002",
    "created_by":"admin",
    "bk_biz_id":"2005000194",
    "module":1,
    "ticket_type":"MYSQL_EDIT_CONFIG",
    "infos":[
        {
            "cluster_id":6,
            "items":{},
            "persistent":false,
            "restart":2,
            "restart_ips":[
                "127.0.0.1"
            ]
        }
    ]
    }
    items 为每一个修改的配置项，格式如下:
    {
    "mysqld.binlog_format":{
        "conf_name":"",
        "conf_value":"ROW",
        "op_type":"upsert"
    },
    "mysqld.innodb_buffer_pool_size":{
        "conf_name":"",
        "conf_value":"4096M",
        "op_type":"upsert",
        "need_restart":true
    }
    }
    """

    def post(self, request):
        logger.info(_("开始下发修改的参数"))
        root_id = generate_root_id()
        logger.info("define root_id: {}".format(root_id))
        mysql_controller_new = MySQLController(root_id, request.data)
        mysql_controller_new.mysql_edit_config_scene()
        return Response({"root_id": root_id})
