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

from backend.flow.engine.controller.spider import SpiderController
from backend.flow.views.base import FlowTestView

logger = logging.getLogger("root")


class TenDBClusterTruncateDatabaseView(FlowTestView):
    """
    api: api: /apis/v1/flow/scene/tendbcluster_truncate_database
    """

    @staticmethod
    def post(request):
        logger.info(_("开始TenDBCluster清档场景"))

        root_id = uuid.uuid1().hex
        logger.info("define root_id: {}".format(root_id))

        c = SpiderController(root_id=root_id, ticket_data=request.data)
        c.truncate_database()
        return Response({"root_id": root_id})
