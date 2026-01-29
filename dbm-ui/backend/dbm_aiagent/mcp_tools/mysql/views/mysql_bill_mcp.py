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
from backend.dbm_aiagent.mcp_tools.exceptions import DBMMcpNoneBillSubmittedException, DBMMcpUsernameNotFoundException
from backend.dbm_aiagent.mcp_tools.mysql.auth_parser.bill import auth_parse_mysql_tdbctl_upgrade_ticket
from backend.dbm_aiagent.mcp_tools.mysql.impl.bill_apply_priv import bill_apply_priv
from backend.dbm_aiagent.mcp_tools.mysql.impl.bill_db_table_backup import bill_db_table_backup
from backend.dbm_aiagent.mcp_tools.mysql.impl.bill_fullbackup import mysql_full_backup
from backend.dbm_aiagent.mcp_tools.mysql.impl.bill_mysql_standardize import bill_mysql_standardize
from backend.dbm_aiagent.mcp_tools.mysql.impl.bill_rename_db import bill_rename_db
from backend.dbm_aiagent.mcp_tools.mysql.impl.bill_tdbctl_upgrade import bill_tdbctl_upgrade
from backend.dbm_aiagent.mcp_tools.mysql.serializers.bill_output import SubmitBillOutputSerializer
from backend.dbm_aiagent.mcp_tools.mysql.serializers.mysql_apply_priv_bill import (
    SubmitBillMySQLApplyPrivInputSerializer,
)
from backend.dbm_aiagent.mcp_tools.mysql.serializers.mysql_db_rename_bill import SubmitBillMySQLDBRenameInputSerializer
from backend.dbm_aiagent.mcp_tools.mysql.serializers.mysql_db_table_backup import (
    SubmitBillMySQLDBTableBackupInputSerializer,
)
from backend.dbm_aiagent.mcp_tools.mysql.serializers.mysql_full_backup_bill import (
    SubmitBillMySQLFullBackupInputSerializer,
)
from backend.dbm_aiagent.mcp_tools.mysql.serializers.mysql_standardize_bill import (
    SubmitBillMySQLStandardizeInputSerializer,
)
from backend.dbm_aiagent.mcp_tools.mysql.serializers.tdbctl_upgrade_bill import SubmitBillTdbctlUpgradeInputSerializer
from backend.dbm_aiagent.mcp_tools.views import McpToolsViewSet
from backend.iam_app.handlers.drf_perm.base import DBManagePermission
from backend.iam_app.handlers.drf_perm.mcp import McpTicketToolPermission


class MySQLBillMcpToolsViewSet(McpToolsViewSet):
    default_permission_class = [DBManagePermission()]

    @mcp_tools_api_decorator(
        description=str(_("""创建 TenDBHA, TenDBCluster 全备单据""")),
        request_slz=SubmitBillMySQLFullBackupInputSerializer,
        response_slz=SubmitBillOutputSerializer,
        permission_classes=[McpTicketToolPermission],
        mcp_auth_parser=auth_parse_clusters,
        tags=[DBMMCPTags.READ, DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.MYSQL_BILL],
        name_prefix="mysql_bill",
    )
    def submit_bill_mysql_full_backup(self, request, *args, **kwargs):
        bk_biz_id = self.get_param("bk_biz_id")
        backup_type = self.get_param("backup_type")
        cluster_domain = self.get_param("cluster_domain")

        username = request.user.username
        if not username:
            raise DBMMcpUsernameNotFoundException()

        return Response(
            mysql_full_backup(
                username=username, bk_biz_id=bk_biz_id, backup_type=backup_type, cluster_domain=cluster_domain
            )
        )

    @mcp_tools_api_decorator(
        description=str(_("""创建 TenDBHA, TenDBCluster 库表备单据""")),
        request_slz=SubmitBillMySQLDBTableBackupInputSerializer,
        response_slz=SubmitBillOutputSerializer,
        permission_classes=[McpTicketToolPermission],
        mcp_auth_parser=auth_parse_clusters,
        tags=[DBMMCPTags.READ, DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.MYSQL_BILL],
        name_prefix="mysql_bill",
    )
    def submit_bill_mysql_db_table_backup(self, request, *args, **kwargs):
        bk_biz_id = self.get_param("bk_biz_id")
        cluster_domain = self.get_param("cluster_domain")
        include_dbs = self.get_param("include_dbs")
        ignore_dbs = self.get_param("ignore_dbs")

        username = request.user.username
        if not username:
            raise DBMMcpUsernameNotFoundException()

        if not ignore_dbs:
            ignore_dbs = []

        return Response(
            bill_db_table_backup(
                username=username,
                bk_biz_id=bk_biz_id,
                cluster_domain=cluster_domain,
                include_dbs=include_dbs,
                ignore_dbs=ignore_dbs,
            )
        )

    @mcp_tools_api_decorator(
        description=str(
            _(
                """创建 mysql 权限申请单据
        * 按照权限模版的定义在集群上开通权限
        * account_name 和 dbname 需要在模版预录入
        * 如果缺少参数参考权限模版
        """
            )
        ),
        request_slz=SubmitBillMySQLApplyPrivInputSerializer,
        response_slz=SubmitBillOutputSerializer,
        permission_classes=[McpTicketToolPermission],
        mcp_auth_parser=auth_parse_clusters,
        tags=[DBMMCPTags.READ, DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.MYSQL_BILL],
        name_prefix="mysql_bill",
    )
    def submit_bill_mysql_apply_priv(self, request, *args, **kwargs):
        bk_biz_id = self.get_param("bk_biz_id")
        cluster_domain = self.get_param("cluster_domain")
        account_name = self.get_param("account_name")
        dbnames = self.get_param("dbnames")
        apply_source_ips = self.get_param("apply_source_ips")

        username = request.user.username
        if not username:
            raise DBMMcpUsernameNotFoundException()

        return Response(
            bill_apply_priv(
                request=request,
                username=username,
                bk_biz_id=bk_biz_id,
                apply_username=account_name,
                apply_access_dbs=dbnames,
                apply_source_ips=apply_source_ips,
                cluster_domain=cluster_domain,
            )
        )

    @mcp_tools_api_decorator(
        description=str(_("""创建 mysql 标准化单据""")),
        request_slz=SubmitBillMySQLStandardizeInputSerializer,
        response_slz=SubmitBillOutputSerializer,
        permission_classes=[McpTicketToolPermission],
        mcp_auth_parser=auth_parse_clusters,
        tags=[DBMMCPTags.READ, DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.MYSQL_BILL],
        name_prefix="mysql_bill",
    )
    def submit_bill_mysql_standardize(self, request, *args, **kwargs):
        bk_biz_id = self.get_param("bk_biz_id")
        cluster_domains = self.get_param("cluster_domains")

        with_instance_standardize = self.get_param("with_instance_standardize", False)
        with_cc_standardize = self.get_param("with_cc_standardize", False)
        with_deploy_binary = self.get_param("with_deploy_binary", False)
        with_push_config = self.get_param("with_push_config", False)

        if not (with_instance_standardize or with_cc_standardize or with_deploy_binary or with_push_config):
            raise DBMMcpNoneBillSubmittedException(msg=_("所有选项为否, 无需提交单据"))

        username = request.user.username
        if not username:
            raise DBMMcpUsernameNotFoundException()

        return Response(
            bill_mysql_standardize(
                username=username,
                bk_biz_id=bk_biz_id,
                cluster_domains=cluster_domains,
                with_instance_standardize=with_instance_standardize,
                with_cc_standardize=with_cc_standardize,
                with_deploy_binary=with_deploy_binary,
                with_push_config=with_push_config,
            )
        )

    @mcp_tools_api_decorator(
        description=str(_("""创建 DB 重命名单据""")),
        request_slz=SubmitBillMySQLDBRenameInputSerializer,
        response_slz=SubmitBillOutputSerializer,
        permission_classes=[McpTicketToolPermission],
        mcp_auth_parser=auth_parse_clusters,
        tags=[DBMMCPTags.READ, DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.MYSQL_BILL],
        name_prefix="mysql_bill",
    )
    def submit_bill_mysql_db_rename(self, request, *args, **kwargs):
        bk_biz_id = self.get_param("bk_biz_id")
        cluster_domain = self.get_param("cluster_domain")
        source_dbname = self.get_param("source_dbname")
        target_dbname = self.get_param("target_dbname")

        username = request.user.username
        if not username:
            raise DBMMcpUsernameNotFoundException()

        return Response(
            bill_rename_db(
                bk_biz_id=bk_biz_id,
                username=username,
                cluster_domain=cluster_domain,
                source_dbname=source_dbname,
                target_dbname=target_dbname,
            )
        )

    @mcp_tools_api_decorator(
        description=str(
            _(
                """创建 TenDBCluster 中控（tdbctl）升级单据

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
        request_slz=SubmitBillTdbctlUpgradeInputSerializer,
        response_slz=SubmitBillOutputSerializer,
        permission_classes=[McpTicketToolPermission],
        mcp_auth_parser=auth_parse_mysql_tdbctl_upgrade_ticket,
        tags=[DBMMCPTags.READ, DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.MYSQL_BILL],
        name_prefix="mysql_bill",
    )
    def submit_bill_tdbctl_upgrade(self, request, *args, **kwargs):
        bk_biz_id = self.get_param("bk_biz_id")
        cluster_domain = self.get_param("cluster_domain", None)
        cluster_id = self.get_param("cluster_id", None)
        version = self.get_param("version", None)

        username = request.user.username
        if not username:
            raise DBMMcpUsernameNotFoundException()

        return Response(
            bill_tdbctl_upgrade(
                bk_biz_id=bk_biz_id,
                username=username,
                cluster_domain=cluster_domain,
                cluster_id=cluster_id,
                version=version,
            )
        )
