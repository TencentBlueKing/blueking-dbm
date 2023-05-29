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

from rest_framework.response import Response

from backend.flow.engine.controller.name_service import NameServiceController
from backend.flow.views.base import FlowTestView

logger = logging.getLogger("root")


class NameServiceClbCreateSceneApiView(FlowTestView):
    """
    名字服务clb创建api接口
    """

    @staticmethod
    def post(request):
        """
        创建clb
        """
        root_id = uuid.uuid1().hex
        NameServiceController(root_id=root_id, ticket_data=request.data).clb_create()
        return Response({"root_id": root_id})


class NameServiceClbDeleteSceneApiView(FlowTestView):
    """
    名字服务clb删除api接口
    """

    @staticmethod
    def post(request):
        """
        删除clb
        """
        root_id = uuid.uuid1().hex
        NameServiceController(root_id=root_id, ticket_data=request.data).clb_delete()
        return Response({"root_id": root_id})


class NameServicePolarisCreateSceneApiView(FlowTestView):
    """
    名字服务polaris创建api接口
    """

    @staticmethod
    def post(request):
        """
        创建polaris
        """
        root_id = uuid.uuid1().hex
        NameServiceController(root_id=root_id, ticket_data=request.data).polaris_create()
        return Response({"root_id": root_id})


class NameServicePolarisDeleteSceneApiView(FlowTestView):
    """
    名字服务polaris删除api接口
    """

    @staticmethod
    def post(request):
        """
        删除polaris
        """
        root_id = uuid.uuid1().hex
        NameServiceController(root_id=root_id, ticket_data=request.data).polaris_delete()
        return Response({"root_id": root_id})
