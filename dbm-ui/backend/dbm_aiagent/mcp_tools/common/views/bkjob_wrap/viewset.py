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

from backend.dbm_aiagent.mcp_tools.common.impl.bkcc_wrap.check_ips_biz_scope import check_ips_biz_scope
from backend.dbm_aiagent.mcp_tools.common.impl.bkcc_wrap.check_machines_operator import check_machines_operator
from backend.dbm_aiagent.mcp_tools.common.impl.bkjob_wrap.execute_script import execute_script
from backend.dbm_aiagent.mcp_tools.common.impl.bkjob_wrap.query_result import query_result
from backend.dbm_aiagent.mcp_tools.common.serializers.bkjob_wrap.current_date_and_ip import (
    CurrentDateAndIpInputSerializer,
)
from backend.dbm_aiagent.mcp_tools.common.serializers.bkjob_wrap.execute_script import ExecuteScriptOutputSerializer
from backend.dbm_aiagent.mcp_tools.common.serializers.bkjob_wrap.query_result import (
    QueryResultInputSerializer,
    QueryResultOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.constants import DBMMCPTags, DBMMcpTools
from backend.dbm_aiagent.mcp_tools.decorators import mcp_tools_api_decorator
from backend.dbm_aiagent.mcp_tools.views import McpToolsViewSet
from backend.iam_app.handlers.drf_perm.mcp import McpIsDbaPermission


class BKJobWrapMcpToolsViewSet(McpToolsViewSet):
    default_permission_class = [McpIsDbaPermission()]

    @mcp_tools_api_decorator(
        description=_("获取目标机器的当前日期和IP"),
        request_slz=CurrentDateAndIpInputSerializer,
        response_slz=ExecuteScriptOutputSerializer,
        tags=[DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.BKJOB_WRAP],
        name_prefix="bkjob_wrap",
        enable=True,
    )
    def current_date_and_ip(self, request, *args, **kwargs):
        bk_cloud_id = self.get_param("bk_cloud_id")
        ips = self.get_param("ips")
        bk_scope_id = self.get_param("bk_scope_id")

        username = request.user.username

        # 机器存在 + 执行者校验（复用公共 helper）
        hosts = check_machines_operator(bk_cloud_id=bk_cloud_id, ips=ips, username=username)
        # 业务归属校验：IP 必须属于用户提供的 CMDB 业务ID，禁止猜测
        bk_scope_type = "biz"  # 仅支持单业务，禁止 biz_set
        check_ips_biz_scope(bk_scope_type=bk_scope_type, bk_scope_id=bk_scope_id, hosts=hosts)

        script = """echo $LOCAL_IP && date"""
        name = "current_data_and_ip"
        run_as = "root"

        job_instance_id = execute_script(
            name=name,
            username=username,
            bk_cloud_id=bk_cloud_id,
            ips=ips,
            script=script,
            run_as=run_as,
            bk_scope_type=bk_scope_type,
            bk_scope_id=bk_scope_id,
        )
        return Response(
            {
                "job_instance_id": job_instance_id,
                "bk_scope_type": bk_scope_type,
                "bk_scope_id": bk_scope_id,
            }
        )

    @mcp_tools_api_decorator(
        description=_("查询作业执行结果"),
        request_slz=QueryResultInputSerializer,
        response_slz=QueryResultOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.BKJOB_WRAP],
        name_prefix="bkjob_wrap",
        enable=True,
    )
    def query_result(self, request, *args, **kwargs):
        bk_scope_id = self.get_param("bk_scope_id")
        bk_scope_type = "biz"  # 仅支持单业务，禁止 biz_set
        job_instance_id = self.get_param("job_instance_id")

        result = query_result(
            bk_scope_type=bk_scope_type,
            bk_scope_id=bk_scope_id,
            job_instance_id=job_instance_id,
        )
        return Response(result)
