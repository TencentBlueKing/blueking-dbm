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
from django.utils.translation import gettext_lazy as _
from rest_framework.response import Response

from backend.components import CCApi
from backend.db_dirty.models import DirtyMachine
from backend.dbm_aiagent.mcp_tools.common.impl.bkcc_wrap.check_operator import check_operator
from backend.dbm_aiagent.mcp_tools.common.impl.bkcc_wrap.list_hosts_without_biz import list_hosts_without_biz
from backend.dbm_aiagent.mcp_tools.common.impl.bkcc_wrap.update_hosts_operator import update_hosts_operator
from backend.dbm_aiagent.mcp_tools.common.serializers.bkcc_wrap.find_host_biz_relations import (
    FindHostBizRelationsInputSerializer,
    FindHostBizRelationsOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.common.serializers.bkcc_wrap.get_biz_internal_module import (
    GetBizInternalModuleInputSerializer,
    GetBizInternalModuleOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.common.serializers.bkcc_wrap.list_hosts_without_biz import (
    ListHostsWithoutBizInputSerializer,
    ListHostsWithoutBizOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.common.serializers.bkcc_wrap.transfer_host_across_biz import (
    TransferHostAcrossBizInputSerializer,
    TransferHostAcrossBizOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.common.serializers.bkcc_wrap.transfer_host_to_idlemodule import (
    TransferHostToIdlemoduleInputSerializer,
    TransferHostToIdlemoduleOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.common.serializers.bkcc_wrap.update_hosts_operator import (
    UpdateHostsOperatorInputSerializer,
    UpdateHostsOperatorOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.common.views.bkcc_wrap.plan_checkers import (
    transfer_host_across_biz_plan_checker,
    transfer_host_to_idlemodule_plan_checker,
    update_hosts_operator_plan_checker,
)
from backend.dbm_aiagent.mcp_tools.constants import DBMMCPTags, DBMMcpTools
from backend.dbm_aiagent.mcp_tools.decorators import mcp_tools_api_decorator
from backend.dbm_aiagent.mcp_tools.exceptions import (
    DBMMcpBaseException,
    DBMMcpForbiddenException,
    DBMMcpUsernameNotFoundException,
)
from backend.dbm_aiagent.mcp_tools.views import McpToolsViewSet
from backend.iam_app.handlers.drf_perm.mcp import McpIsDbaPermission


class BKCCWrapMcpToolsViewSet(McpToolsViewSet):
    default_permission_class = [McpIsDbaPermission()]

    @mcp_tools_api_decorator(
        description=str(CCApi.list_hosts_without_biz.description),
        request_slz=ListHostsWithoutBizInputSerializer,
        response_slz=ListHostsWithoutBizOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.BKCC_WRAP],
        name_prefix="bkcc_wrap",
        enable=True,
    )
    def list_hosts_without_biz(self, request, *args, **kwargs):
        bk_cloud_id = self.get_param("bk_cloud_id")
        ips = self.get_param("ips")

        res = list_hosts_without_biz(bk_cloud_id=bk_cloud_id, ips=ips)
        return Response({"info": res})

    @mcp_tools_api_decorator(
        description=str(CCApi.get_biz_internal_module.description),
        request_slz=GetBizInternalModuleInputSerializer,
        response_slz=GetBizInternalModuleOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.BKCC_WRAP],
        name_prefix="bkcc_wrap",
        enable=True,
    )
    def get_biz_internal_module(self, request, *args, **kwargs):
        bk_biz_id = self.get_param("bk_biz_id")
        return Response(CCApi.get_biz_internal_module({"bk_biz_id": bk_biz_id}, use_admin=True))

    @mcp_tools_api_decorator(
        description=str(CCApi.find_host_biz_relations.description),
        request_slz=FindHostBizRelationsInputSerializer,
        response_slz=FindHostBizRelationsOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.BKCC_WRAP],
        name_prefix="bkcc_wrap",
        enable=True,
    )
    def find_host_biz_relations(self, request, *args, **kwargs):
        """
        ccapi 的参数用单数名词又是传入 list -_-
        """
        bk_host_ids = self.get_param("bk_host_ids")
        return Response({"info": CCApi.find_host_biz_relations({"bk_host_id": bk_host_ids}, use_admin=True)})

    @mcp_tools_api_decorator(
        description=_("修改机器负责人"),
        request_slz=UpdateHostsOperatorInputSerializer,
        response_slz=UpdateHostsOperatorOutputSerializer,
        tags=[DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.BKCC_WRAP],
        name_prefix="bkcc_wrap",
        enable=True,
        enable_callee_plan=True,
        callee_plan_checker=update_hosts_operator_plan_checker,
    )
    def update_hosts_operator(self, request, *args, **kwargs):
        bk_host_ids = self.get_param("bk_host_ids")
        operators = self.get_param("operators", [])
        bak_operators = self.get_param("bak_operators", [])

        username = request.user.username
        if not username:
            raise DBMMcpUsernameNotFoundException()

        dbm_pool_machines = DirtyMachine.objects.filter(bk_host_id__in=bk_host_ids)
        pool_host_ids = set(dbm_pool_machines.values_list("bk_host_id", flat=True))
        not_in_pool_host_ids = list(set(bk_host_ids) - pool_host_ids)
        if not_in_pool_host_ids:
            raise DBMMcpForbiddenException(msg=f"{not_in_pool_host_ids} not found in DBM pool")

        update_hosts_operator(
            bk_host_ids=bk_host_ids,
            operators=operators,
            bak_operators=bak_operators,
            username=username,
        )

        return Response({"bk_host_ids": bk_host_ids})

    @mcp_tools_api_decorator(
        description=str(CCApi.transfer_host_to_idlemodule.description),
        request_slz=TransferHostToIdlemoduleInputSerializer,
        response_slz=TransferHostToIdlemoduleOutputSerializer,
        tags=[DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.BKCC_WRAP],
        name_prefix="bkcc_wrap",
        enable=True,
        enable_callee_plan=True,
        callee_plan_checker=transfer_host_to_idlemodule_plan_checker,
    )
    def transfer_host_to_idlemodule(self, request, *args, **kwargs):
        bk_biz_id = self.get_param("bk_biz_id")
        bk_host_ids = self.get_param("bk_host_ids")

        username = request.user.username
        if not username:
            raise DBMMcpUsernameNotFoundException()

        check_operator(username=username, bk_host_ids=bk_host_ids)

        dbm_pool_machines = DirtyMachine.objects.filter(bk_host_id__in=bk_host_ids)
        if dbm_pool_machines.exists():
            raise DBMMcpForbiddenException(
                msg=f"{list(dbm_pool_machines.values_list('bk_host_id', flat=True))} found in DBM pool"
            )

        CCApi.transfer_host_to_idlemodule(
            {"bk_biz_id": bk_biz_id, "bk_host_id": bk_host_ids}, use_admin=True  # CC API 这里是传入数组, 但是 key 名确实是单数形式
        )

        return Response({"bk_biz_id": bk_biz_id, "bk_host_ids": bk_host_ids})

    @mcp_tools_api_decorator(
        description=_("跨业务空闲机转移"),
        request_slz=TransferHostAcrossBizInputSerializer,
        response_slz=TransferHostAcrossBizOutputSerializer,
        tags=[DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.BKCC_WRAP],
        name_prefix="bkcc_wrap",
        enable=True,
        enable_callee_plan=True,
        callee_plan_checker=transfer_host_across_biz_plan_checker,
    )
    def transfer_host_across_biz(self, request, *args, **kwargs):
        """
        跨业务转移主机，只能将源业务空闲机池集群中的主机转移到目标业务的空闲机池集群
        这是 cc api 内置的校验
        所以这里不需要再校验机器在 src biz 中的拓扑位置

        bk_module_id	int	是	主机要转移到的模块ID，该模块ID必须为下空闲机池set下的模块ID
        这是 cc api 对目标的内置限制
        """
        src_bk_biz_id = self.get_param("src_bk_biz_id")
        bk_host_ids = self.get_param("bk_host_ids")
        dst_bk_biz_id = self.get_param("dst_bk_biz_id")

        username = request.user.username
        if not username:
            raise DBMMcpUsernameNotFoundException()

        check_operator(username=username, bk_host_ids=bk_host_ids)

        dbm_pool_machines = DirtyMachine.objects.filter(bk_host_id__in=bk_host_ids)
        if dbm_pool_machines.exists():
            raise DBMMcpForbiddenException(
                msg=f"{list(dbm_pool_machines.values_list('bk_host_id', flat=True))} found in DBM pool"
            )

        dst_biz_internal_module = CCApi.get_biz_internal_module({"bk_biz_id": dst_bk_biz_id}, use_admin=True)
        dst_idle_module_id = None
        for module in dst_biz_internal_module.get("module") or []:
            if module.get("default") == 1:
                dst_idle_module_id = module["bk_module_id"]
                break
        if dst_idle_module_id is None:
            raise DBMMcpBaseException(msg=f"idle module not found in biz {dst_bk_biz_id}")

        CCApi.transfer_host_across_biz(
            {
                "src_bk_biz_id": src_bk_biz_id,
                "bk_host_id": bk_host_ids,
                "dst_bk_biz_id": dst_bk_biz_id,
                "bk_module_id": dst_idle_module_id,
            },
            use_admin=True,
        )

        return Response(
            {
                "src_bk_biz_id": src_bk_biz_id,
                "dst_bk_biz_id": dst_bk_biz_id,
                "dst_idle_module_id": dst_idle_module_id,
                "bk_host_ids": bk_host_ids,
            }
        )
