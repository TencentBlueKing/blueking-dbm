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

from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster
from backend.dbm_aiagent.mcp_tools.common.auth_parser.base import auth_parse_clusters
from backend.dbm_aiagent.mcp_tools.common.serializers.ticket_commit import TicketCommitInputSerializer
from backend.dbm_aiagent.mcp_tools.constants import DBMMCPTags, DBMMcpTools
from backend.dbm_aiagent.mcp_tools.decorators import mcp_tools_api_decorator
from backend.dbm_aiagent.mcp_tools.exceptions import (
    DBMMcpClusterNotFoundException,
    DBMMcpMultiBkBizIdFoundException,
    DBMMcpNoneBillSubmittedException,
    DBMMcpUsernameNotFoundException,
)
from backend.dbm_aiagent.mcp_tools.mysql.auth_parser.bill import auth_parse_mysql_tdbctl_upgrade_ticket
from backend.dbm_aiagent.mcp_tools.mysql.impl.ticket_param_apply_priv import ticket_param_apply_priv
from backend.dbm_aiagent.mcp_tools.mysql.impl.ticket_param_db_table_backup import ticket_param_db_table_backup
from backend.dbm_aiagent.mcp_tools.mysql.impl.ticket_param_fullbackup import ticket_param_mysql_full_backup
from backend.dbm_aiagent.mcp_tools.mysql.impl.ticket_param_mysql_standardize import ticket_param_mysql_standardize
from backend.dbm_aiagent.mcp_tools.mysql.impl.ticket_param_rename_db import ticket_param_rename_db
from backend.dbm_aiagent.mcp_tools.mysql.impl.ticket_param_tdbctl_upgrade import ticket_param_tdbctl_upgrade
from backend.dbm_aiagent.mcp_tools.mysql.serializers.ticket_param_mysql_apply_priv import (
    GenerateMySQLApplyPrivParamInputSerializer,
)
from backend.dbm_aiagent.mcp_tools.mysql.serializers.ticket_param_mysql_db_rename import (
    GenerateMySQLDBRenameParamInputSerializer,
)
from backend.dbm_aiagent.mcp_tools.mysql.serializers.ticket_param_mysql_db_table_backup import (
    GenerateMySQLDBTableBackupParamInputSerializer,
)
from backend.dbm_aiagent.mcp_tools.mysql.serializers.ticket_param_mysql_full_backup import (
    GenerateMySQLFullBackupParamInputSerializer,
)
from backend.dbm_aiagent.mcp_tools.mysql.serializers.ticket_param_mysql_standardize import (
    GenerateMySQLStandardizeParamInputSerializer,
)
from backend.dbm_aiagent.mcp_tools.mysql.serializers.ticket_param_tdbctl_upgrade import (
    GenerateTdbctlUpgradeParamInputSerializer,
)
from backend.dbm_aiagent.mcp_tools.views import McpToolsViewSet
from backend.iam_app.handlers.drf_perm.base import DBManagePermission
from backend.iam_app.handlers.drf_perm.mcp import McpTicketToolPermission


class MySQLTicketMcpToolsViewSet(McpToolsViewSet):
    default_permission_class = [DBManagePermission()]

    @mcp_tools_api_decorator(
        description=str(_("""生成 TenDBHA, TenDBCluster 全备单据参数""")),
        request_slz=GenerateMySQLFullBackupParamInputSerializer,
        response_slz=TicketCommitInputSerializer,
        permission_classes=[McpTicketToolPermission],
        mcp_auth_parser=auth_parse_clusters,
        tags=[DBMMCPTags.READ, DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.MYSQL_TICKET],
        name_prefix="mysql_ticket",
    )
    def generate_mysql_full_backup_param(self, request, *args, **kwargs):
        # bk_biz_id = self.get_param("bk_biz_id")
        backup_type = self.get_param("backup_type")
        cluster_domain = self.get_param("cluster_domain")

        cluster_obj = Cluster.objects.get(immute_domain=cluster_domain)

        username = request.user.username
        if not username:
            raise DBMMcpUsernameNotFoundException()

        return Response(
            ticket_param_mysql_full_backup(username=username, cluster_obj=cluster_obj, backup_type=backup_type)
        )

    @mcp_tools_api_decorator(
        description=str(_("""生成 TenDBHA, TenDBCluster 库表备单据参数""")),
        request_slz=GenerateMySQLDBTableBackupParamInputSerializer,
        response_slz=TicketCommitInputSerializer,
        permission_classes=[McpTicketToolPermission],
        mcp_auth_parser=auth_parse_clusters,
        tags=[DBMMCPTags.READ, DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.MYSQL_TICKET],
        name_prefix="mysql_ticket",
    )
    def generate_mysql_db_table_backup_param(self, request, *args, **kwargs):
        # bk_biz_id = self.get_param("bk_biz_id")
        cluster_domain = self.get_param("cluster_domain")
        include_dbs = self.get_param("include_dbs")
        ignore_dbs = self.get_param("ignore_dbs")

        username = request.user.username
        if not username:
            raise DBMMcpUsernameNotFoundException()

        cluster_obj = Cluster.objects.get(immute_domain=cluster_domain)

        if not ignore_dbs:
            ignore_dbs = []

        return Response(
            ticket_param_db_table_backup(
                username=username,
                cluster_obj=cluster_obj,
                include_dbs=include_dbs,
                ignore_dbs=ignore_dbs,
            )
        )

    @mcp_tools_api_decorator(
        description=str(
            _(
                """生成 mysql 权限申请单据参数
        * 按照权限模版的定义在集群上开通权限
        * account_name 和 dbname 需要在模版预录入
        * 如果缺少参数参考权限模版
        """
            )
        ),
        request_slz=GenerateMySQLApplyPrivParamInputSerializer,
        response_slz=TicketCommitInputSerializer,
        permission_classes=[McpTicketToolPermission],
        mcp_auth_parser=auth_parse_clusters,
        tags=[DBMMCPTags.READ, DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.MYSQL_TICKET],
        name_prefix="mysql_ticket",
    )
    def generate_mysql_apply_priv_param(self, request, *args, **kwargs):
        # bk_biz_id = self.get_param("bk_biz_id")
        cluster_domain = self.get_param("cluster_domain")
        account_name = self.get_param("account_name")
        dbnames = self.get_param("dbnames")
        apply_source_ips = self.get_param("apply_source_ips")

        username = request.user.username
        if not username:
            raise DBMMcpUsernameNotFoundException()

        cluster_obj = Cluster.objects.get(immute_domain=cluster_domain)

        return Response(
            ticket_param_apply_priv(
                request=request,
                username=username,
                # bk_biz_id=bk_biz_id,
                apply_username=account_name,
                apply_access_dbs=dbnames,
                apply_source_ips=apply_source_ips,
                cluster_obj=cluster_obj,
                # cluster_domain=cluster_domain,
            )
        )

    @mcp_tools_api_decorator(
        description=str(_("""生成 mysql 标准化单据参数""")),
        request_slz=GenerateMySQLStandardizeParamInputSerializer,
        response_slz=TicketCommitInputSerializer,
        permission_classes=[McpTicketToolPermission],
        mcp_auth_parser=auth_parse_clusters,
        tags=[DBMMCPTags.READ, DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.MYSQL_TICKET],
        name_prefix="mysql_ticket",
    )
    def generate_mysql_standardize_param(self, request, *args, **kwargs):
        # bk_biz_id = self.get_param("bk_biz_id")
        cluster_domains = self.get_param("cluster_domains")

        username = request.user.username
        if not username:
            raise DBMMcpUsernameNotFoundException()

        cluster_objs = Cluster.objects.filter(
            immute_domain__in=cluster_domains,
            cluster_type__in=[ClusterType.TenDBSingle, ClusterType.TenDBHA, ClusterType.TenDBCluster],
        )
        if len(cluster_objs) != len(cluster_domains):
            found_domains = set(cluster_objs.values_list("immute_domain", flat=True))
            missing_domains = set(cluster_domains) - found_domains
            raise DBMMcpClusterNotFoundException(msg=_("集群不存在: {}").format(", ".join(missing_domains)))

        bk_biz_ids = set(cluster_objs.values_list("bk_biz_id", flat=True))
        if len(bk_biz_ids) > 1:
            raise DBMMcpMultiBkBizIdFoundException(msg=_("集群属于多个业务: {}").format(", ".join(map(str, bk_biz_ids))))
        bk_biz_id = bk_biz_ids.pop()

        with_instance_standardize = self.get_param("with_instance_standardize", False)
        with_cc_standardize = self.get_param("with_cc_standardize", False)
        with_deploy_binary = self.get_param("with_deploy_binary", False)
        with_push_config = self.get_param("with_push_config", False)

        if not (with_instance_standardize or with_cc_standardize or with_deploy_binary or with_push_config):
            raise DBMMcpNoneBillSubmittedException(msg=_("所有选项为否, 无需提交单据"))

        return Response(
            ticket_param_mysql_standardize(
                username=username,
                bk_biz_id=bk_biz_id,
                cluster_objs=cluster_objs,
                # cluster_domains=cluster_domains,
                with_instance_standardize=with_instance_standardize,
                with_cc_standardize=with_cc_standardize,
                with_deploy_binary=with_deploy_binary,
                with_push_config=with_push_config,
            )
        )

    @mcp_tools_api_decorator(
        description=str(_("""生成 DB 重命名单据参数""")),
        request_slz=GenerateMySQLDBRenameParamInputSerializer,
        response_slz=TicketCommitInputSerializer,
        permission_classes=[McpTicketToolPermission],
        mcp_auth_parser=auth_parse_clusters,
        tags=[DBMMCPTags.READ, DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.MYSQL_TICKET],
        name_prefix="mysql_ticket",
    )
    def generate_mysql_db_rename_param(self, request, *args, **kwargs):
        # bk_biz_id = self.get_param("bk_biz_id")
        cluster_domain = self.get_param("cluster_domain")
        source_dbname = self.get_param("source_dbname")
        target_dbname = self.get_param("target_dbname")

        username = request.user.username
        if not username:
            raise DBMMcpUsernameNotFoundException()

        cluster_obj = Cluster.objects.get(immute_domain=cluster_domain)

        return Response(
            ticket_param_rename_db(
                # bk_biz_id=bk_biz_id,
                cluster_obj=cluster_obj,
                username=username,
                # cluster_domain=cluster_domain,
                source_dbname=source_dbname,
                target_dbname=target_dbname,
            )
        )

    @mcp_tools_api_decorator(
        description=str(
            _(
                """生成 TenDBCluster 中控（tdbctl）升级单据参数

参数说明：
- bk_biz_id: 业务ID（必填）
- cluster_domain: 集群域名（可选，与 cluster_id 二选一）
- cluster_id: 集群ID（可选，与 cluster_domain 二选一）
- version: 升级版本号（可选，如 2.4.13，不传则使用最新创建的 tdbctl 包）

使用场景：
1. 只传 bk_biz_id: 升级该业务下所有 TenDBCluster 集群
2. 传 bk_biz_id + cluster_domain/cluster_id: 升级指定集群
        """
            )
        ),
        request_slz=GenerateTdbctlUpgradeParamInputSerializer,
        response_slz=TicketCommitInputSerializer,
        permission_classes=[McpTicketToolPermission],
        mcp_auth_parser=auth_parse_mysql_tdbctl_upgrade_ticket,
        tags=[DBMMCPTags.READ, DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.MYSQL_TICKET],
        name_prefix="mysql_ticket",
    )
    def generate_tdbctl_upgrade_param(self, request, *args, **kwargs):
        bk_biz_id = self.get_param("bk_biz_id")
        cluster_domain = self.get_param("cluster_domain", None)
        cluster_id = self.get_param("cluster_id", None)
        version = self.get_param("version", None)

        username = request.user.username
        if not username:
            raise DBMMcpUsernameNotFoundException()

        return Response(
            ticket_param_tdbctl_upgrade(
                bk_biz_id=bk_biz_id,
                username=username,
                cluster_domain=cluster_domain,
                cluster_id=cluster_id,
                version=version,
            )
        )
