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

import time
from itertools import chain

from django.utils.translation import gettext_lazy as _
from rest_framework.response import Response

from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster
from backend.dbm_aiagent.mcp_tools.common.impl.get_source_access_impl import generate_cluster_query_report
from backend.dbm_aiagent.mcp_tools.common.impl.job import exec_cluster_query_net_tcp_cmd, get_job_exec_status
from backend.dbm_aiagent.mcp_tools.common.serializers.get_source_access import (
    GetSourceAccessInputSerializer,
    GetSourceAccessOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.constants import DBMAMcpTools, DBMMCPTags
from backend.dbm_aiagent.mcp_tools.decorators import mcp_tools_api_decorator
from backend.dbm_aiagent.mcp_tools.views import McpToolsViewSet
from backend.iam_app.handlers.drf_perm.base import DBManagePermission


class GetSourceAccessMcpToolsViewSet(McpToolsViewSet):
    default_permission_class = [DBManagePermission()]

    @mcp_tools_api_decorator(
        description=str(_("""查询集群访问来源，返回访问来源列表""")),
        request_slz=GetSourceAccessInputSerializer,
        response_slz=GetSourceAccessOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMAMcpTools.COMMON_TOOL],
        name_prefix="common-tool",
    )
    def get_cluster_source_access(self, request, *args, **kwargs):
        bk_biz_id = self.get_param("bk_biz_id")
        cluster_domain = self.get_param("cluster_domain")

        cluster_obj = Cluster.objects.get(bk_biz_id=bk_biz_id, immute_domain=cluster_domain)

        cluster_all_ips = [
            e.machine.ip for e in chain(cluster_obj.storageinstance_set.all(), cluster_obj.proxyinstance_set.all())
        ]
        # 如果是主从，那就是rs
        if cluster_obj.cluster_type in (ClusterType.TendisRedisInstance):
            target_ips = [
                {"ip": e.machine.ip, "bk_cloud_id": cluster_obj.bk_cloud_id}
                for e in cluster_obj.storageinstance_set.all()
            ]
        # 如果是plus/cluster，则是proxy+rs
        elif cluster_obj.cluster_type in (
            ClusterType.TendisPredixyRedisCluster,
            ClusterType.TendisPredixyTendisplusCluster,
            ClusterType.TendisTendisplusCluster,
        ):
            target_ips = [
                {"ip": e.machine.ip, "bk_cloud_id": cluster_obj.bk_cloud_id}
                for e in chain(cluster_obj.storageinstance_set.all(), cluster_obj.proxyinstance_set.all())
            ]
        # 默认是proxy
        else:
            target_ips = [
                {"ip": e.machine.ip, "bk_cloud_id": cluster_obj.bk_cloud_id}
                for e in cluster_obj.proxyinstance_set.all()
            ]

        # 执行job
        job_task = exec_cluster_query_net_tcp_cmd(target_ips)

        # 轮询job状态
        #  轮询job,直到超时(5分钟)或结束
        job_instance_id = job_task["job_instance_id"]
        tcp_report = []
        for i in range(10):
            time.sleep(30)
            job_resp = get_job_exec_status(job_instance_id)
            if job_resp["finished"]:
                # 生成报告
                tcp_report = generate_cluster_query_report(job_resp["job_log_resp"], cluster_domain, cluster_all_ips)
                break
        return Response({"report": tcp_report[0]["report"], "failed_hosts": tcp_report[0]["error"]})
