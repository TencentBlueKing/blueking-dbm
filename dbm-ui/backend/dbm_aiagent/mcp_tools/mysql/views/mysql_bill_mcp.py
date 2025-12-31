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

from backend.db_meta.enums import ClusterType, InstanceInnerRole
from backend.db_meta.models import Cluster
from backend.dbm_aiagent.mcp_tools.constants import DBMAMcpTools, DBMMCPTags
from backend.dbm_aiagent.mcp_tools.decorators import mcp_tools_api_decorator
from backend.dbm_aiagent.mcp_tools.exceptions import (
    DBMMcpNotSupportClusterTypeException,
    DBMMcpUsernameNotFoundException,
)
from backend.dbm_aiagent.mcp_tools.mysql.impl.bill_apply_priv import bill_apply_priv
from backend.dbm_aiagent.mcp_tools.mysql.serializers.bill_output import SubmitBillOutputSerializer
from backend.dbm_aiagent.mcp_tools.mysql.serializers.mysql_apply_priv_bill import (
    SubmitBillMySQLApplyPrivInputSerializer,
)
from backend.dbm_aiagent.mcp_tools.mysql.serializers.mysql_db_table_backup import (
    SubmitBillMySQLDBTableBackupInputSerializer,
)
from backend.dbm_aiagent.mcp_tools.mysql.serializers.mysql_full_backup_bill import (
    SubmitBillMySQLFullBackupInputSerializer,
)
from backend.dbm_aiagent.mcp_tools.views import McpToolsViewSet
from backend.flow.consts import MySQLBackupFileTagEnum
from backend.iam_app.handlers.drf_perm.base import DBManagePermission
from backend.ticket.constants import TicketType
from backend.ticket.models import Ticket


class MySQLBillMcpToolsViewSet(McpToolsViewSet):
    default_permission_class = [DBManagePermission()]

    @mcp_tools_api_decorator(
        description=str(_("""创建 TenDBHA, TenDBCluster 全备单据""")),
        request_slz=SubmitBillMySQLFullBackupInputSerializer,
        response_slz=SubmitBillOutputSerializer,
        tags=[DBMMCPTags.READ, DBMMCPTags.WRITE],
        mcp=[DBMAMcpTools.MYSQL_BILL],
        name_prefix="mysql_bill",
    )
    def submit_bill_mysql_full_backup(self, request, *args, **kwargs):
        bk_biz_id = self.get_param("bk_biz_id")
        backup_type = self.get_param("backup_type")
        cluster_domain = self.get_param("cluster_domain")

        username = request.user.username
        if not username:
            raise DBMMcpUsernameNotFoundException()

        cluster_obj = Cluster.objects.get(bk_biz_id=bk_biz_id, immute_domain=cluster_domain)
        cluster_type = cluster_obj.cluster_type

        if cluster_type == ClusterType.TenDBCluster:
            ticket_type = TicketType.TENDBCLUSTER_FULL_BACKUP
        elif cluster_type == ClusterType.TenDBHA:
            ticket_type = TicketType.MYSQL_HA_FULL_BACKUP
        else:
            raise DBMMcpNotSupportClusterTypeException(cluster_type=cluster_type)

        ticket_param = {
            "ticket_type": ticket_type,
            "remark": ticket_type,
            "creator": username,
            "helpers": [],
            "bk_biz_id": bk_biz_id,
            "details": {
                "backup_type": backup_type,  # MySQLBackupTypeEnum.PHYSICAL,
                "file_tag": MySQLBackupFileTagEnum.DBFILE1M,
                "infos": [
                    {
                        "cluster_id": cluster_obj.pk,
                        "backup_local": InstanceInnerRole.SLAVE,
                    }
                ],
            },
        }

        tk = Ticket.create_ticket(**ticket_param)
        return Response({"bill_id": tk.pk})

    @mcp_tools_api_decorator(
        description=str(_("""创建 TenDBHA, TenDBCluster 库表备单据""")),
        request_slz=SubmitBillMySQLDBTableBackupInputSerializer,
        response_slz=SubmitBillOutputSerializer,
        tags=[DBMMCPTags.READ, DBMMCPTags.WRITE],
        mcp=[DBMAMcpTools.MYSQL_BILL],
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

        cluster_obj = Cluster.objects.get(bk_biz_id=bk_biz_id, immute_domain=cluster_domain)
        cluster_type = cluster_obj.cluster_type

        if cluster_type == ClusterType.TenDBCluster:
            ticket_type = TicketType.TENDBCLUSTER_DB_TABLE_BACKUP
        elif cluster_type in ClusterType.TenDBHA:
            ticket_type = TicketType.MYSQL_HA_DB_TABLE_BACKUP
        else:
            raise DBMMcpNotSupportClusterTypeException(cluster_type=cluster_type)

        ticket_param = {
            "ticket_type": ticket_type,
            "remark": ticket_type,
            "creator": username,
            "helpers": [],
            "bk_biz_id": bk_biz_id,
            "details": {
                "infos": [
                    {
                        "cluster_id": cluster_obj.pk,
                        "db_patterns": include_dbs,
                        "ignore_dbs": ignore_dbs,
                        "table_patterns": ["*"],
                        "ignore_tables": [""],
                    }
                ]
            },
        }

        tk = Ticket.create_ticket(**ticket_param)
        return Response({"bill_id": tk.pk})

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
        tags=[DBMMCPTags.READ, DBMMCPTags.WRITE],
        mcp=[DBMAMcpTools.MYSQL_BILL],
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

        bill_id = bill_apply_priv(
            request=request,
            username=username,
            bk_biz_id=bk_biz_id,
            apply_username=account_name,
            apply_access_dbs=dbnames,
            apply_source_ips=apply_source_ips,
            cluster_domain=cluster_domain,
        )

        return Response({"bill_id": bill_id})
