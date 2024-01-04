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

from backend.flow.engine.controller.mongodb import MongoDBController
from backend.flow.views.base import FlowTestView

logger = logging.getLogger("root")


class MultiReplicasetInstallApiView(FlowTestView):
    """复制集安装"""

    @staticmethod
    def post(request):
        root_id = uuid.uuid1().hex
        MongoDBController(root_id=root_id, ticket_data=request.data).multi_replicaset_create()
        return Response({"root_id": root_id})


class ClusterInstallApiView(FlowTestView):
    """cluster安装"""

    @staticmethod
    def post(request):
        root_id = uuid.uuid1().hex
        MongoDBController(root_id=root_id, ticket_data=request.data).cluster_create()
        return Response({"root_id": root_id})


class MongoBackupApiView(FlowTestView):
    """
    Mongo Backup Api
    """

    @staticmethod
    def post(request):
        """
        mongo_backup
        """
        root_id = uuid.uuid1().hex
        # root_id 32位字串 320ba2d87a1411eebbed525400066689
        # request 是一个request对象
        # request.data 输入Json
        MongoDBController(root_id=root_id, ticket_data=request.data).mongo_backup()
        return Response({"root_id": root_id})


class MongoFakeInstallApiView(FlowTestView):
    """
    Mongo Backup Api
    """

    @staticmethod
    def post(request):
        """
        mongo_backup
        """
        root_id = uuid.uuid1().hex
        # root_id 32位字串 320ba2d87a1411eebbed525400066689
        # request 是一个request对象
        # request.data 输入Json
        MongoDBController(root_id=root_id, ticket_data=request.data).fake_install()
        return Response({"root_id": root_id})
