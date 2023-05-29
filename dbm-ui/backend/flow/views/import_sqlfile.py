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

# from turtle import back


logger = logging.getLogger("root")


class ImportSQLFileSceneApiView(FlowTestView):
    """
    Templ Payload
    {
        "uid": "2022051612120001",
        "created_by": "xxx",
        "bk_biz_id": "152",
        "ticket_type": "MYSQL_IMPORT_SQLFILE",
        "charset": "default",
        "force": false,
        "path": "/bk-xx/path1/path2"
        "cluster_ids": [1,2],
        "execute_objects": [
                {
                        "sql_file": "bar.sql",
                        "ignore_dbnames": [
                                "db1",
                                "db2"
                        ],
                        "dbnames": [
                                "db_log%"
                        ]
                },
                {
                        "sql_file": "foo.sql",
                        "ignore_dbnames": [
                                "db1",
                                "db2"
                        ],
                        "dbnames": [
                                "db_tool%"
                        ]
                }
        ]
    }
    """

    def post(self, request):
        root_id = generate_root_id()
        test = MySQLController(root_id=root_id, ticket_data=request.data)
        test.mysql_import_sqlfile_scene()
        return Response({"root_id": root_id})
