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
from django.utils.translation import gettext as _
from rest_framework.response import Response

from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster
from backend.dbm_aiagent.mcp_tools.common.auth_parser.base import auth_parse_clusters
from backend.dbm_aiagent.mcp_tools.constants import DBMMCPTags, DBMMcpTools
from backend.dbm_aiagent.mcp_tools.decorators import mcp_tools_api_decorator
from backend.dbm_aiagent.mcp_tools.exceptions import DBMMcpBaseException, DBMMcpUsernameNotFoundException
from backend.dbm_aiagent.mcp_tools.sqlserver.impl.bill_commit.bill_backup_dbs import bill_sqlserver_backup_dbs
from backend.dbm_aiagent.mcp_tools.sqlserver.impl.bill_commit.bill_cluster_migrate import (
    bill_sqlserver_cluster_migrate,
)
from backend.dbm_aiagent.mcp_tools.sqlserver.impl.bill_commit.bill_host_migrate import bill_sqlserver_host_migrate
from backend.dbm_aiagent.mcp_tools.sqlserver.impl.bill_commit.bill_master_slave_switch import (
    bill_sqlserver_master_slave_switch,
)
from backend.dbm_aiagent.mcp_tools.sqlserver.impl.bill_commit.bill_restore_local_slave import (
    bill_sqlserver_restore_local_slave,
)
from backend.dbm_aiagent.mcp_tools.sqlserver.impl.bill_commit.bill_restore_slave import bill_sqlserver_restore_slave
from backend.dbm_aiagent.mcp_tools.sqlserver.serializers.bill_output import SubmitBillOutputSerializer
from backend.dbm_aiagent.mcp_tools.sqlserver.serializers.sqlserver_bill_commit import (
    SubmitSQLServerBackupDbsSerializer,
    SubmitSQLServerClusterMigrateSerializer,
    SubmitSQLServerHostMigrateSerializer,
    SubmitSQLServerMasterSlaveSwitchSerializer,
    SubmitSQLServerRestoreLocalSlaveSerializer,
    SubmitSQLServerRestoreSlaveSerializer,
)
from backend.dbm_aiagent.mcp_tools.views import McpToolsViewSet
from backend.iam_app.handlers.drf_perm.base import DBManagePermission
from backend.iam_app.handlers.drf_perm.mcp import McpTicketToolPermission


def _auth_parse_sqlserver_infos_clusters(request, key: str):
    """从多行 infos 中提取集群域名并解析 SQLServer HA 集群，供鉴权使用。"""
    data = request.query_params if request.method == "GET" else request.data
    infos = data.get("infos") or []

    if key == "cluster_domains":
        domains = [d for info in infos for d in (info.get("cluster_domains") or [])]
    elif key == "cluster_domain":
        domains = [info.get("cluster_domain") for info in infos if info.get("cluster_domain")]
    else:
        raise DBMMcpBaseException(msg=_("不支持的 sqlserver infos 鉴权解析 key: {}").format(key))

    if not domains:
        raise DBMMcpBaseException(msg=_("infos 中未找到 cluster_domain"))

    clusters = Cluster.objects.filter(immute_domain__in=domains, cluster_type=ClusterType.SqlserverHA)
    if not clusters.exists():
        raise DBMMcpBaseException(msg=_("未找到集群: {}").format(domains))

    return list(clusters.values_list("id", flat=True))


def auth_parse_sqlserver_cluster_migrate(request, *args, **kwargs):
    return _auth_parse_sqlserver_infos_clusters(request, "cluster_domain")


def auth_parse_sqlserver_host_migrate(request, *args, **kwargs):
    return _auth_parse_sqlserver_infos_clusters(request, "cluster_domains")


class SQLServerBillCommitMcpToolsViewSet(McpToolsViewSet):
    default_permission_class = [DBManagePermission()]

    @mcp_tools_api_decorator(
        description=str(_("创建 SQLServer 集群迁移单据（支持多行，每行一个集群 + 目标规格）")),
        request_slz=SubmitSQLServerClusterMigrateSerializer,
        response_slz=SubmitBillOutputSerializer,
        permission_classes=[McpTicketToolPermission],
        mcp_auth_parser=auth_parse_sqlserver_cluster_migrate,
        tags=[DBMMCPTags.READ, DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.SQLSERVER_BILL],
        name_prefix="sqlserver_bill",
    )
    def submit_bill_sqlserver_cluster_migrate(self, request, *args, **kwargs):
        infos = self.get_param("infos")
        username = request.user.username
        if not username:
            raise DBMMcpUsernameNotFoundException()

        return Response(bill_sqlserver_cluster_migrate(username=username, infos=infos))

    @mcp_tools_api_decorator(
        description=str(_("创建 SQLServer 整机迁移单据（支持多行，每行一台源主机 + 目标规格）")),
        request_slz=SubmitSQLServerHostMigrateSerializer,
        response_slz=SubmitBillOutputSerializer,
        permission_classes=[McpTicketToolPermission],
        mcp_auth_parser=auth_parse_sqlserver_host_migrate,
        tags=[DBMMCPTags.READ, DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.SQLSERVER_BILL],
        name_prefix="sqlserver_bill",
    )
    def submit_bill_sqlserver_host_migrate(self, request, *args, **kwargs):
        infos = self.get_param("infos")
        username = request.user.username
        if not username:
            raise DBMMcpUsernameNotFoundException()

        return Response(bill_sqlserver_host_migrate(username=username, infos=infos))

    @mcp_tools_api_decorator(
        description=str(_("创建 SQLServer 主从互切单据")),
        request_slz=SubmitSQLServerMasterSlaveSwitchSerializer,
        response_slz=SubmitBillOutputSerializer,
        permission_classes=[McpTicketToolPermission],
        mcp_auth_parser=auth_parse_clusters,
        tags=[DBMMCPTags.READ, DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.SQLSERVER_BILL],
        name_prefix="sqlserver_bill",
    )
    def submit_bill_sqlserver_master_slave_switch(self, request, *args, **kwargs):
        cluster_domains = list({d.strip() for d in self.get_param("cluster_domains")})
        ips = list({addr.strip() for addr in self.get_param("ips")})

        username = request.user.username
        if not username:
            raise DBMMcpUsernameNotFoundException()

        return Response(
            bill_sqlserver_master_slave_switch(username=username, cluster_domains=cluster_domains, ips=ips)
        )

    @mcp_tools_api_decorator(
        description=str(_("创建 SQLServer 原地重建单据")),
        request_slz=SubmitSQLServerRestoreLocalSlaveSerializer,
        response_slz=SubmitBillOutputSerializer,
        permission_classes=[McpTicketToolPermission],
        mcp_auth_parser=auth_parse_clusters,
        tags=[DBMMCPTags.READ, DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.SQLSERVER_BILL],
        name_prefix="sqlserver_bill",
    )
    def submit_bill_sqlserver_restore_local_slave(self, request, *args, **kwargs):
        cluster_domain = self.get_param("cluster_domain")
        ips = list({addr.strip() for addr in self.get_param("ips")})

        username = request.user.username
        if not username:
            raise DBMMcpUsernameNotFoundException()

        return Response(bill_sqlserver_restore_local_slave(username=username, cluster_domain=cluster_domain, ips=ips))

    @mcp_tools_api_decorator(
        description=str(_("创建 SQLServer 新机重建单据")),
        request_slz=SubmitSQLServerRestoreSlaveSerializer,
        response_slz=SubmitBillOutputSerializer,
        permission_classes=[McpTicketToolPermission],
        mcp_auth_parser=auth_parse_clusters,
        tags=[DBMMCPTags.READ, DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.SQLSERVER_BILL],
        name_prefix="sqlserver_bill",
    )
    def submit_bill_sqlserver_restore_slave(self, request, *args, **kwargs):
        cluster_domain = self.get_param("cluster_domain")
        ips = list({addr.strip() for addr in self.get_param("ips")})
        spec_id = self.get_param("spec_id")
        labels = self.get_param("labels")

        username = request.user.username
        if not username:
            raise DBMMcpUsernameNotFoundException()

        return Response(
            bill_sqlserver_restore_slave(
                username=username, cluster_domain=cluster_domain, ips=ips, spec_id=spec_id, labels=labels
            )
        )

    @mcp_tools_api_decorator(
        description=str(_("创建 SQLServer 库表备份单据")),
        request_slz=SubmitSQLServerBackupDbsSerializer,
        response_slz=SubmitBillOutputSerializer,
        permission_classes=[McpTicketToolPermission],
        mcp_auth_parser=auth_parse_clusters,
        tags=[DBMMCPTags.READ, DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.SQLSERVER_BILL],
        name_prefix="sqlserver_bill",
    )
    def submit_bill_sqlserver_backup_dbs(self, request, *args, **kwargs):
        bk_biz_id = self.get_param("bk_biz_id")
        cluster_domain = self.get_param("cluster_domain")
        backup_dbs = self.get_param("backup_dbs")
        file_tag = self.get_param("file_tag")
        backup_type = self.get_param("backup_type")
        backup_place = self.get_param("backup_place")

        username = request.user.username
        if not username:
            raise DBMMcpUsernameNotFoundException()

        return Response(
            bill_sqlserver_backup_dbs(
                username=username,
                bk_biz_id=bk_biz_id,
                cluster_domain=cluster_domain,
                backup_dbs=backup_dbs,
                file_tag=file_tag,
                backup_type=backup_type,
                backup_place=backup_place,
            )
        )
