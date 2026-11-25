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

from backend.dbm_aiagent.mcp_tools.constants import DBMMCPTags, DBMMcpTools
from backend.dbm_aiagent.mcp_tools.decorators import mcp_tools_api_decorator
from backend.dbm_aiagent.mcp_tools.hdfs.impl.hdfs_toolbox import (
    DB_COUNT_MAX,
    JOB_TIMEOUT_SECONDS,
    NAMED_TABLE_MAX,
    TABLE_COUNT_MAX,
    TOOLBOX_LOCK_TTL_SECONDS,
    IcebergTableSizesTask,
    ListIcebergDbsTask,
    ListIcebergTablesTask,
    query_task_result,
    submit_task,
)
from backend.dbm_aiagent.mcp_tools.hdfs.serializers.hdfs_toolbox import (
    HdfsGetIcebergTableSizesInputSerializer,
    HdfsListIcebergTablesInputSerializer,
    HdfsToolboxBaseInputSerializer,
    HdfsToolboxQueryResultInputSerializer,
    HdfsToolboxQueryResultOutputSerializer,
    HdfsToolboxSubmitOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.views import McpToolsViewSet
from backend.iam_app.handlers.drf_perm.base import RejectPermission

logger = logging.getLogger("root")

"""
HDFS 工具箱：在一台 DataNode 上执行 hdfs dfs 命令，只处理 /data/iceberg/warehouse 下的 iceberg 库表目录。
所有功能都是异步的：提交工具只下发 Job 并返回 job_instance_id，结果统一用 hdfs_toolbox_query_result 查询。
- 列出库目录
- 列出单个库的表目录
- 统计指定表目录（最多 20 个）的数据量
"""

_ASYNC_NOTE = str(
    _(
        "异步执行：本工具只提交任务并返回 job_instance_id，结果用 hdfs_toolbox_query_result 查询。"
        "同一集群同一时刻只允许一个工具箱任务，提交后集群锁保持 {} 秒；Job 超时 {} 秒。"
    )
).format(TOOLBOX_LOCK_TTL_SECONDS, JOB_TIMEOUT_SECONDS)


class HdfsToolboxMcpToolsViewSet(McpToolsViewSet):
    # 当前 HDFS MCP 功能仅对后台 admin 身份开放。
    default_permission_class = [RejectPermission()]

    @mcp_tools_api_decorator(
        description=str(
            _(
                "列出 HDFS 集群 iceberg 仓库 /data/iceberg/warehouse 下的库目录（一级子目录），"
                "在一台 DataNode 上执行一次 hdfs dfs -ls。"
                "最多返回按名称排序的前 {} 个库目录；超过时 truncated=true，db_count 为总数。"
                "参数：cluster_domain（集群域名）。"
            )
        ).format(DB_COUNT_MAX)
        + _ASYNC_NOTE,
        request_slz=HdfsToolboxBaseInputSerializer,
        response_slz=HdfsToolboxSubmitOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.HDFS_TOOLBOX],
        name_prefix="hdfs_toolbox",
    )
    def list_iceberg_dbs(self, request, *args, **kwargs):
        validated_params = self.params_validate(self.get_serializer_class())
        return Response(submit_task(validated_params["cluster_domain"], ListIcebergDbsTask()))

    @mcp_tools_api_decorator(
        description=str(
            _(
                "列出单个 iceberg 库目录下的表目录（库目录的一级子目录），在一台 DataNode 上执行一次 hdfs dfs -ls。"
                "最多返回按名称排序的前 {} 个表目录；超过时 truncated=true，table_count 为总数。"
                "参数：cluster_domain，db_dir（库目录，例如 /data/iceberg/warehouse/iceberg_xxx.db）。"
            )
        ).format(TABLE_COUNT_MAX)
        + _ASYNC_NOTE,
        request_slz=HdfsListIcebergTablesInputSerializer,
        response_slz=HdfsToolboxSubmitOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.HDFS_TOOLBOX],
        name_prefix="hdfs_toolbox",
    )
    def list_iceberg_tables(self, request, *args, **kwargs):
        validated_params = self.params_validate(self.get_serializer_class())
        task = ListIcebergTablesTask(db_dir=validated_params["db_dir"])
        return Response(submit_task(validated_params["cluster_domain"], task))

    @mcp_tools_api_decorator(
        description=str(
            _(
                "统计指定 iceberg 表目录的数据量（逻辑大小和含副本的磁盘占用），逐表 hdfs dfs -du -s。"
                "参数：cluster_domain，table_dirs（表目录绝对路径列表，形如 /data/iceberg/warehouse/<库目录>/<表目录>，"
                "最多 {} 个）。"
            )
        ).format(NAMED_TABLE_MAX)
        + _ASYNC_NOTE,
        request_slz=HdfsGetIcebergTableSizesInputSerializer,
        response_slz=HdfsToolboxSubmitOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.HDFS_TOOLBOX],
        name_prefix="hdfs_toolbox",
    )
    def get_iceberg_table_sizes(self, request, *args, **kwargs):
        validated_params = self.params_validate(self.get_serializer_class())
        task = IcebergTableSizesTask(table_dirs=validated_params["table_dirs"])
        return Response(submit_task(validated_params["cluster_domain"], task))

    @mcp_tools_api_decorator(
        description=str(
            _(
                "查询 HDFS 工具箱任务的结果，立即返回不等待。"
                "status=running 表示仍在执行，按 poll_interval_seconds 间隔再查；"
                "status=succeeded 时结果在 result，结构按 task_type 区分；status=failed 时原因在 message。"
                "只能查询本工具箱提交且属于该集群的任务。"
                "参数：cluster_domain，job_instance_id（提交工具返回的作业实例 ID）。"
            )
        ),
        request_slz=HdfsToolboxQueryResultInputSerializer,
        response_slz=HdfsToolboxQueryResultOutputSerializer,
        tags=[DBMMCPTags.READ],
        mcp=[DBMMcpTools.HDFS_TOOLBOX],
        name_prefix="hdfs_toolbox",
    )
    def query_result(self, request, *args, **kwargs):
        validated_params = self.params_validate(self.get_serializer_class())
        result = query_task_result(validated_params["cluster_domain"], validated_params["job_instance_id"])
        return Response(result)
