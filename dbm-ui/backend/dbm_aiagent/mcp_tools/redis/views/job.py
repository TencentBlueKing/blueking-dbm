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

import shlex
import time
from itertools import chain

from django.utils.translation import gettext_lazy as _
from rest_framework.response import Response

from backend.db_meta.enums import InstanceInnerRole
from backend.db_meta.models import Cluster
from backend.db_services.redis.util import is_have_proxy, is_redis_cluster_protocal
from backend.dbm_aiagent.mcp_tools.common.auth_parser.base import auth_parse_clusters
from backend.dbm_aiagent.mcp_tools.common.impl.job import exec_cluster_query_net_tcp_cmd, get_job_exec_status
from backend.dbm_aiagent.mcp_tools.constants import DBMMCPTags, DBMMcpTools
from backend.dbm_aiagent.mcp_tools.decorators import mcp_tools_api_decorator
from backend.dbm_aiagent.mcp_tools.redis.impl.get_source_access_impl import generate_cluster_query_report
from backend.dbm_aiagent.mcp_tools.redis.impl.job import exec_redis_capture_tool_cmd, generate_redis_capture_report
from backend.dbm_aiagent.mcp_tools.redis.serializers.get_source_access import (
    GetRedisSourceAccessByKeyInputSerializer,
    GetRedisSourceAccessByKeyOutputSerializer,
    GetRedisSourceAccessInputSerializer,
    GetRedisSourceAccessOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.views import McpToolsViewSet
from backend.iam_app.handlers.drf_perm.base import DBManagePermission
from backend.iam_app.handlers.drf_perm.mcp import McpClusterManagePermission


class RedisJobMcpToolsViewSet(McpToolsViewSet):
    default_permission_class = [DBManagePermission()]

    @mcp_tools_api_decorator(
        description=str(_("""查询Redis集群访问来源，返回来源列表""")),
        request_slz=GetRedisSourceAccessInputSerializer,
        response_slz=GetRedisSourceAccessOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.REDIS_JOB],
        name_prefix="redis_job",
    )
    def get_redis_source_access(self, request, *args, **kwargs):
        cluster_domain = self.get_param("cluster_domain")

        cluster_obj = Cluster.objects.get(immute_domain=cluster_domain)

        cluster_all_ips = [
            e.machine.ip for e in chain(cluster_obj.storageinstance_set.all(), cluster_obj.proxyinstance_set.all())
        ]
        # 如果是主从，那就是rs
        if not is_have_proxy(cluster_obj.cluster_type):
            target_ips = [
                {"ip": e.machine.ip, "bk_cloud_id": cluster_obj.bk_cloud_id}
                for e in cluster_obj.storageinstance_set.all()
            ]
        # 如果是plus/cluster，则是proxy+rs
        elif is_redis_cluster_protocal(cluster_obj.cluster_type):
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

    @mcp_tools_api_decorator(
        description=str(_("""根据关键字，实时获取对应关键字的请求情况""")),
        request_slz=GetRedisSourceAccessByKeyInputSerializer,
        response_slz=GetRedisSourceAccessByKeyOutputSerializer,
        permission_classes=[McpClusterManagePermission],
        mcp_auth_parser=auth_parse_clusters,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.REDIS_JOB],
        name_prefix="redis_job",
    )
    def get_redis_query_cmd_by_key(self, request, *args, **kwargs):
        bk_biz_id = self.get_param("bk_biz_id")
        cluster_domain = self.get_param("cluster_domain")
        keyword_list = self.get_param("keyword_list")
        timeout = self.get_param("timeout")
        ins = self.get_param("ins")

        cluster_obj = Cluster.objects.get(bk_biz_id=bk_biz_id, immute_domain=cluster_domain)
        if ins != "":
            ip, port = ins.split(":")
            target_ips = [{"ip": ip, "bk_cloud_id": cluster_obj.bk_cloud_id}]
        else:
            #  如果是集群，那从proxy上抓
            if is_have_proxy(cluster_obj.cluster_type):
                target_ips = [
                    {"ip": e.machine.ip, "bk_cloud_id": cluster_obj.bk_cloud_id}
                    for e in cluster_obj.proxyinstance_set.all()
                ]
                port = cluster_obj.proxyinstance_set.first().port
            # 主从
            else:
                m_ins = cluster_obj.storageinstance_set.filter(
                    instance_inner_role=InstanceInnerRole.MASTER.value
                ).first()
                target_ips = [{"ip": m_ins.machine.ip, "bk_cloud_id": cluster_obj.bk_cloud_id}]
                port = m_ins.port

        # 将keyword_list 转换成shell的管道情况
        grep_cmd = " | ".join(f"grep -i {shlex.quote(k)}" for k in keyword_list)

        # 执行job
        job_task = exec_redis_capture_tool_cmd(target_ips, timeout, port, grep_cmd)

        # 轮询job状态
        #  轮询job,直到超时(5分钟)或结束
        job_instance_id = job_task["job_instance_id"]
        capture_report = []
        for i in range(10):
            time.sleep(30)
            job_resp = get_job_exec_status(job_instance_id)
            if job_resp["finished"]:
                # 解析工具抓包结果
                capture_report = generate_redis_capture_report(job_resp["job_log_resp"])
                break
        return Response({"result": capture_report})
