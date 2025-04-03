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

from backend.flow.engine.controller.mysql_clb_operation import MySQLClbController
from backend.flow.views.base import FlowTestView
from backend.utils.basic import generate_root_id

logger = logging.getLogger("root")


class MysqlClbCreateSceneApiView(FlowTestView):
    """
    名字服务clb创建api接口
    """

    @staticmethod
    def post(request):
        """
        创建clb
        """
        root_id = generate_root_id()
        MySQLClbController(root_id=root_id, ticket_data=request.data).clb_create()
        return Response({"root_id": root_id})


class MysqlClbDeleteSceneApiView(FlowTestView):
    """
    名字服务clb删除api接口
    """

    @staticmethod
    def post(request):
        """
        删除clb
        """
        root_id = generate_root_id()
        MySQLClbController(root_id=root_id, ticket_data=request.data).clb_delete()
        return Response({"root_id": root_id})


class MysqlDomainBindClbIpSceneApiView(FlowTestView):
    """
    主域名绑定clb ip api接口
    """

    @staticmethod
    def post(request):
        """
        主域名绑定clb ip
        """
        root_id = generate_root_id()
        MySQLClbController(root_id=root_id, ticket_data=request.data).immute_domain_bind_clb_ip()
        return Response({"root_id": root_id})


class MysqlDomainUnBindClbIpSceneApiView(FlowTestView):
    """
    主域名解绑clb ip api接口
    """

    @staticmethod
    def post(request):
        """
        主域名解绑clb ip
        """
        root_id = generate_root_id()
        MySQLClbController(root_id=root_id, ticket_data=request.data).immute_domain_unbind_clb_ip()
        return Response({"root_id": root_id})
