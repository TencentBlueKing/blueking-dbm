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

from backend.dbm_aiagent.mcp_tools.common.auth_parser.base import auth_parse_clusters
from backend.dbm_aiagent.mcp_tools.constants import DBMMCPTags, DBMMcpTools
from backend.dbm_aiagent.mcp_tools.decorators import mcp_tools_api_decorator
from backend.dbm_aiagent.mcp_tools.mysql.impl.mysql_config_update import update_mysql_config
from backend.dbm_aiagent.mcp_tools.mysql.serializers.mysql_config_update import (
    UpdateMysqlConfigInputSerializer,
    UpdateMysqlConfigOutputSerializer,
)
from backend.dbm_aiagent.mcp_tools.views import McpToolsViewSet
from backend.iam_app.handlers.drf_perm.base import RejectPermission
from backend.iam_app.handlers.drf_perm.mcp import McpClusterManagePermission, McpIsDbaPermission


class MySQLConfigUpdateMcpToolsViewSet(McpToolsViewSet):
    default_permission_class = [RejectPermission()]

    @mcp_tools_api_decorator(
        description=str(
            _(
                """修改 MySQL 集群周边工具的配置
支持修改的配置类型（conf_type):
- backup: 备份配置，conf_file 可选值为 binlog_rotate.yaml / dbbackup.ini / dbbackup.options
  - 修改备份开始时间: conf_file=dbbackup.options, conf_name=CrontabTime, conf_value="3 5 * * *"
  - 修改备份类型: conf_file=dbbackup.ini, conf_name=Public.BackupType, conf_value=logical (physical)
  - 修改 binlog 保留阈值: conf_file=binlog_rotate.yaml, conf_name=public.max_disk_used_pct, conf_value=80 (表示 80% 开启清理)
- mysql_monitor: 监控配置，conf_file 固定为 items-config.yaml
  - 关闭主从心跳: conf_file=items-config.yaml, conf_name=master-slave-heartbeat, conf_value='{"enable":false}',
- checksum: 校验配置，conf_file 固定为 checksum.yaml
  - 关闭数据校验: conf_file=checksum.yaml, conf_name=enable, conf_value=false
仅支持修改集群级别（cluster）的配置
"""
            )
        ),
        request_slz=UpdateMysqlConfigInputSerializer,
        response_slz=UpdateMysqlConfigOutputSerializer,
        permission_classes=[McpClusterManagePermission, McpIsDbaPermission],
        mcp_auth_parser=auth_parse_clusters,
        tags=[DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.MYSQL_CONFIG],
        name_prefix="mysql_config",
    )
    def update_mysql_config(self, request, *args, **kwargs):
        bk_biz_id = self.get_param("bk_biz_id")
        cluster_domain = self.get_param("cluster_domain")
        conf_type = self.get_param("conf_type")
        conf_file = self.get_param("conf_file")
        conf_name = self.get_param("conf_name")
        conf_value = self.get_param("conf_value")

        return Response(
            update_mysql_config(
                bk_biz_id=bk_biz_id,
                cluster_domain=cluster_domain,
                conf_type=conf_type,
                conf_file=conf_file,
                conf_name=conf_name,
                conf_value=conf_value,
            )
        )
