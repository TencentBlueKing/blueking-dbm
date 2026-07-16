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

from django.utils.translation import gettext_lazy as _
from rest_framework.response import Response

from backend.db_services.dbresource.handlers import async_create_replenish
from backend.db_services.dbresource.models import ResourceReplenishRecord
from backend.dbm_aiagent.mcp_tools.common.auth_parser.base import auth_parse_bizs
from backend.dbm_aiagent.mcp_tools.common.serializers.resource_replenish import (
    HcmResourceReplenishInputSerializer,
    HcmResourceReplenishOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.constants import DBMMCPTags, DBMMcpTools
from backend.dbm_aiagent.mcp_tools.decorators import mcp_tools_api_decorator
from backend.dbm_aiagent.mcp_tools.views import McpToolsViewSet
from backend.iam_app.handlers.drf_perm.mcp import McpDBManagePermission
from backend.ticket.constants import ReplenishTypeEnum

logger = logging.getLogger("root")


class HcmResourceReplenishMcpToolsViewSet(McpToolsViewSet):
    @mcp_tools_api_decorator(
        description=str(_("创建海磊主机补货记录")),
        request_slz=HcmResourceReplenishInputSerializer,
        response_slz=HcmResourceReplenishOutputSerializer,
        tags=[DBMMCPTags.WRITE],
        permission_classes=[McpDBManagePermission],
        mcp_auth_parser=auth_parse_bizs,
        mcp=[DBMMcpTools.RESOURCE_REPLENISH],
        name_prefix="resource_replenish",
    )
    def hcm_resource_replenish(self, request, *args, **kwargs):
        username = request.user.username
        infos = self.get_param("infos")
        bk_biz_id = self.get_param("bk_biz_id")
        # 先创建空记录用于防重入和状态轮询，异步任务完成后更新 ticket_ids 和 details
        record = ResourceReplenishRecord.objects.create(
            creator=username, ticket_ids=[], details={}, replenish_type=ReplenishTypeEnum.INCREMENT
        )
        # 一次提单可能很多，所以异步发起
        kwargs = {"username": username, "bk_biz_id": bk_biz_id, "infos": infos, "record_id": record.id}
        async_create_replenish.apply_async(kwargs=kwargs)
        return Response(data={"record_id": record.id})
