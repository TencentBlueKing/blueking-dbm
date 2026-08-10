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
import copy
import time

from django.core.exceptions import MultipleObjectsReturned
from django.utils.translation import gettext as _
from rest_framework.response import Response

from backend import env
from backend.db_meta.enums import ClusterType, MachineType
from backend.db_meta.models import Cluster, Machine, ProxyInstance, StorageInstance
from backend.dbm_aiagent.mcp_tools.common.auth_parser.base import auth_parse_clusters, auth_parse_instances
from backend.dbm_aiagent.mcp_tools.constants import DBMMCPTags, DBMMcpTools
from backend.dbm_aiagent.mcp_tools.decorators import mcp_tools_api_decorator
from backend.dbm_aiagent.mcp_tools.exceptions import (
    DBMMcpBaseException,
    DBMMcpNoneBillSubmittedException,
    DBMMcpNotSupportClusterTypeException,
    DBMMcpNotSupportMachineTypeException,
    DBMMcpUsernameNotFoundException,
)
from backend.dbm_aiagent.mcp_tools.mysql.auth_parser.bill import auth_parse_mysql_tdbctl_upgrade_ticket
from backend.dbm_aiagent.mcp_tools.mysql.constants import MYSQL_MCP_DB_READ
from backend.dbm_aiagent.mcp_tools.mysql.helpers.assert_clustertype import assert_cluster_type
from backend.dbm_aiagent.mcp_tools.mysql.impl.bill_apply_priv import bill_apply_priv
from backend.dbm_aiagent.mcp_tools.mysql.impl.bill_construct_rollback import bill_construct_rollback
from backend.dbm_aiagent.mcp_tools.mysql.impl.bill_db_table_backup import bill_db_table_backup
from backend.dbm_aiagent.mcp_tools.mysql.impl.bill_fullbackup import mysql_full_backup
from backend.dbm_aiagent.mcp_tools.mysql.impl.bill_machine_replace.bill_backend_slave_replace import (
    bill_backend_slave_replace,
)
from backend.dbm_aiagent.mcp_tools.mysql.impl.bill_machine_replace.bill_proxy_replace import bill_proxy_replace
from backend.dbm_aiagent.mcp_tools.mysql.impl.bill_machine_replace.bill_remote_replace import bill_remote_replace
from backend.dbm_aiagent.mcp_tools.mysql.impl.bill_machine_replace.bill_spider_replace import bill_spider_replace
from backend.dbm_aiagent.mcp_tools.mysql.impl.bill_machine_replace.bill_tendbcluster_master_slave_switch import (
    bill_tendbcluster_master_slave_switch,
)
from backend.dbm_aiagent.mcp_tools.mysql.impl.bill_machine_replace.bill_tendbha_master_slave_swtich import (
    bill_tendbha_master_slave_switch,
)
from backend.dbm_aiagent.mcp_tools.mysql.impl.bill_mysql_destroy import bill_mysql_destroy
from backend.dbm_aiagent.mcp_tools.mysql.impl.bill_mysql_disable import bill_mysql_disable
from backend.dbm_aiagent.mcp_tools.mysql.impl.bill_mysql_standardize import bill_mysql_standardize
from backend.dbm_aiagent.mcp_tools.mysql.impl.bill_rename_db import bill_rename_db
from backend.dbm_aiagent.mcp_tools.mysql.impl.bill_tdbctl_upgrade import bill_tdbctl_upgrade
from backend.dbm_aiagent.mcp_tools.mysql.serializers.bill_output import SubmitBillOutputSerializer
from backend.dbm_aiagent.mcp_tools.mysql.serializers.mysql_apply_priv_bill import (
    SubmitBillMySQLApplyPrivInputSerializer,
)
from backend.dbm_aiagent.mcp_tools.mysql.serializers.mysql_clone_grants_bill import (
    SubmitBillMySQLCloneGrantsInputSerializer,
)
from backend.dbm_aiagent.mcp_tools.mysql.serializers.mysql_construct_rollback_bill import (
    SubmitBillMySQLConstructRollbackInputSerializer,
)
from backend.dbm_aiagent.mcp_tools.mysql.serializers.mysql_db_rename_bill import SubmitBillMySQLDBRenameInputSerializer
from backend.dbm_aiagent.mcp_tools.mysql.serializers.mysql_db_table_backup import (
    SubmitBillMySQLDBTableBackupInputSerializer,
)
from backend.dbm_aiagent.mcp_tools.mysql.serializers.mysql_destroy_bill import SubmitBillMySQLDestroyInputSerializer
from backend.dbm_aiagent.mcp_tools.mysql.serializers.mysql_disable_bill import SubmitBillMySQLDisableInputSerializer
from backend.dbm_aiagent.mcp_tools.mysql.serializers.mysql_full_backup_bill import (
    SubmitBillMySQLFullBackupInputSerializer,
)
from backend.dbm_aiagent.mcp_tools.mysql.serializers.mysql_machine_replace import (
    SubmitBillMySQLMachineReplaceSerializer,
    SubmitBillTenDBClusterMachineReplaceSerializer,
)
from backend.dbm_aiagent.mcp_tools.mysql.serializers.mysql_standardize_bill import (
    SubmitBillMySQLStandardizeInputSerializer,
)
from backend.dbm_aiagent.mcp_tools.mysql.serializers.tdbctl_upgrade_bill import SubmitBillTdbctlUpgradeInputSerializer
from backend.dbm_aiagent.mcp_tools.views import McpToolsViewSet
from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.engine.bamboo.scene.mysql.clone_grants_from_file import mysql_clone_grants_from_file_subflow
from backend.flow.engine.bamboo.scene.spider.clone_grants_from_file import spider_clone_grants_from_file_subflow
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

        assert_cluster_type(
            Cluster.objects.using(MYSQL_MCP_DB_READ).get(immute_domain=cluster_domain),
            [ClusterType.TenDBHA, ClusterType.TenDBCluster],
        )

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

        assert_cluster_type(
            Cluster.objects.using(MYSQL_MCP_DB_READ).get(immute_domain=cluster_domain),
            [ClusterType.TenDBHA, ClusterType.TenDBCluster],
        )

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

        assert_cluster_type(
            Cluster.objects.using(MYSQL_MCP_DB_READ).get(immute_domain=cluster_domain),
            [ClusterType.TenDBSingle, ClusterType.TenDBHA, ClusterType.TenDBCluster],
        )

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

        assert_cluster_type(
            Cluster.objects.using(MYSQL_MCP_DB_READ).filter(immute_domain__in=cluster_domains),
            [ClusterType.TenDBSingle, ClusterType.TenDBHA, ClusterType.TenDBCluster],
        )

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

        assert_cluster_type(
            Cluster.objects.using(MYSQL_MCP_DB_READ).get(immute_domain=cluster_domain),
            [ClusterType.TenDBSingle, ClusterType.TenDBHA, ClusterType.TenDBCluster],
        )

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
- cluster_domains: 集群域名列表（可选，与 cluster_ids 二选一）
- cluster_ids: 集群ID列表（可选，与 cluster_domains 二选一）
- version: 升级版本号（可选，如 2.4.13，不传则使用最新创建的 tdbctl 包）

使用场景：
1. 只传 bk_biz_id: 升级该业务下所有 TenDBCluster 集群
2. 传 bk_biz_id + cluster_domains/cluster_ids: 升级指定集群（支持多个）
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
        cluster_domains = self.get_param("cluster_domains", None)
        cluster_ids = self.get_param("cluster_ids", None)
        version = self.get_param("version", None)

        assert_cluster_type(
            Cluster.objects.using(MYSQL_MCP_DB_READ).filter(id__in=cluster_ids), [ClusterType.TenDBCluster]
        )

        username = request.user.username
        if not username:
            raise DBMMcpUsernameNotFoundException()

        return Response(
            bill_tdbctl_upgrade(
                bk_biz_id=bk_biz_id,
                username=username,
                cluster_domains=cluster_domains,
                cluster_ids=cluster_ids,
                version=version,
            )
        )

    @mcp_tools_api_decorator(
        description=str(_("""创建 TenDBHA proxy 新机替换单据""")),
        request_slz=SubmitBillMySQLMachineReplaceSerializer,
        response_slz=SubmitBillOutputSerializer,
        permission_classes=[McpTicketToolPermission],
        mcp_auth_parser=auth_parse_clusters,
        tags=[DBMMCPTags.READ, DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.MYSQL_BILL],
        name_prefix="mysql_bill",
    )
    def submit_bill_proxy_replace(self, request, *args, **kwargs):
        cluster_domains = list({d.strip() for d in self.get_param("cluster_domains")})
        ips = list({addr.strip() for addr in self.get_param("ips")})

        assert_cluster_type(
            Cluster.objects.using(MYSQL_MCP_DB_READ).filter(immute_domain__in=cluster_domains), [ClusterType.TenDBHA]
        )

        return Response(bill_proxy_replace(cluster_domains=cluster_domains, ips=ips))

    @mcp_tools_api_decorator(
        description=str(_("""创建 TenDBHA 存储 slave 新机替换单据""")),
        request_slz=SubmitBillMySQLMachineReplaceSerializer,
        response_slz=SubmitBillOutputSerializer,
        permission_classes=[McpTicketToolPermission],
        mcp_auth_parser=auth_parse_clusters,
        tags=[DBMMCPTags.READ, DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.MYSQL_BILL],
        name_prefix="mysql_bill",
    )
    def submit_bill_backend_slave_replace(self, request, *args, **kwargs):
        cluster_domains = list({d.strip() for d in self.get_param("cluster_domains")})
        ips = list({addr.strip() for addr in self.get_param("ips")})

        assert_cluster_type(
            Cluster.objects.using(MYSQL_MCP_DB_READ).filter(immute_domain__in=cluster_domains), [ClusterType.TenDBHA]
        )

        return Response(bill_backend_slave_replace(cluster_domains=cluster_domains, ips=ips))

    @mcp_tools_api_decorator(
        description=str(_("""创建 TenDBCluster spider 新机替换单据""")),
        request_slz=SubmitBillTenDBClusterMachineReplaceSerializer,
        response_slz=SubmitBillOutputSerializer,
        permission_classes=[McpTicketToolPermission],
        mcp_auth_parser=auth_parse_clusters,
        tags=[DBMMCPTags.READ, DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.MYSQL_BILL],
        name_prefix="mysql_bill",
    )
    def submit_bill_spider_replace(self, request, *args, **kwargs):
        cluster_domain = self.get_param("cluster_domain")
        ips = list({addr.strip() for addr in self.get_param("ips")})

        assert_cluster_type(
            Cluster.objects.using(MYSQL_MCP_DB_READ).get(immute_domain=cluster_domain), [ClusterType.TenDBCluster]
        )

        return Response(bill_spider_replace(cluster_domain=cluster_domain, ips=ips))

    @mcp_tools_api_decorator(
        description=str(_("""创建 TenDBCluster remote slave 新机替换单据""")),
        request_slz=SubmitBillTenDBClusterMachineReplaceSerializer,
        response_slz=SubmitBillOutputSerializer,
        permission_classes=[McpTicketToolPermission],
        mcp_auth_parser=auth_parse_clusters,
        tags=[DBMMCPTags.READ, DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.MYSQL_BILL],
        name_prefix="mysql_bill",
    )
    def submit_bill_remote_slave_replace(self, request, *args, **kwargs):
        cluster_domain = self.get_param("cluster_domain")
        ips = list({addr.strip() for addr in self.get_param("ips")})

        assert_cluster_type(
            Cluster.objects.using(MYSQL_MCP_DB_READ).get(immute_domain=cluster_domain), [ClusterType.TenDBCluster]
        )

        return Response(bill_remote_replace(cluster_domain=cluster_domain, ips=ips))

    @mcp_tools_api_decorator(
        description=str(_("""创建 TenDBHA 主从互切单据""")),
        request_slz=SubmitBillMySQLMachineReplaceSerializer,
        response_slz=SubmitBillOutputSerializer,
        permission_classes=[McpTicketToolPermission],
        mcp_auth_parser=auth_parse_clusters,
        tags=[DBMMCPTags.READ, DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.MYSQL_BILL],
        name_prefix="mysql_bill",
    )
    def submit_bill_tendbha_master_slave_switch(self, request, *args, **kwargs):
        """
        因为懒得定义个新的 serializer, 这里的输入 ip 才是 list
        实际上只应该有一个
        """
        cluster_domains = list({d.strip() for d in self.get_param("cluster_domains")})
        ips = list({addr.strip() for addr in self.get_param("ips")})

        assert_cluster_type(
            Cluster.objects.using(MYSQL_MCP_DB_READ).filter(immute_domain__in=cluster_domains), [ClusterType.TenDBHA]
        )

        return Response(bill_tendbha_master_slave_switch(cluster_domains=cluster_domains, ips=ips))

    @mcp_tools_api_decorator(
        description=str(_("""创建 TenDBCluster 主从互切单据""")),
        request_slz=SubmitBillTenDBClusterMachineReplaceSerializer,
        response_slz=SubmitBillOutputSerializer,
        permission_classes=[McpTicketToolPermission],
        mcp_auth_parser=auth_parse_clusters,
        tags=[DBMMCPTags.READ, DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.MYSQL_BILL],
        name_prefix="mysql_bill",
    )
    def submit_bill_tendbcluster_master_slave_switch(self, request, *args, **kwargs):
        cluster_domain = self.get_param("cluster_domain")
        ips = list({addr.strip() for addr in self.get_param("ips")})

        assert_cluster_type(
            Cluster.objects.using(MYSQL_MCP_DB_READ).get(immute_domain=cluster_domain), [ClusterType.TenDBCluster]
        )

        return Response(bill_tendbcluster_master_slave_switch(cluster_domain, ips))

    @mcp_tools_api_decorator(
        description=str(
            _(
                """创建 TenDBHA, TenDBCluster 数据构造到已有集群单据、回档单据
参数说明：
- bk_biz_id: 业务ID（必填）
- cluster_domain: 集群域名（必填）
- target_cluster_domain: 目标集群域名（必填）
- databases: 数据库列表（缺省 ["*"]，需用户确认）
- tables: 表列表（缺省 ["*"]，需用户确认）
- rollback_time: 构造时间点 ISO 8601（与 backup_id 二选一）
- backup_id: 备份ID（可选, 与 rollback_time 二选一）
"""
            )
        ),
        request_slz=SubmitBillMySQLConstructRollbackInputSerializer,
        response_slz=SubmitBillOutputSerializer,
        permission_classes=[McpTicketToolPermission],
        mcp_auth_parser=auth_parse_clusters,
        tags=[DBMMCPTags.READ, DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.MYSQL_BILL],
        name_prefix="mysql_bill",
    )
    def submit_bill_mysql_construct_rollback(self, request, *args, **kwargs):
        bk_biz_id = self.get_param("bk_biz_id")
        cluster_domain = self.get_param("cluster_domain")
        target_cluster_domain = self.get_param("target_cluster_domain")
        databases = self.get_param("databases")
        tables = self.get_param("tables")
        rollback_time = self.get_param("rollback_time", None)
        backup_id = self.get_param("backup_id", None)

        username = request.user.username
        if not username:
            raise DBMMcpUsernameNotFoundException()

        return Response(
            bill_construct_rollback(
                bk_biz_id=bk_biz_id,
                username=username,
                cluster_domain=cluster_domain,
                target_cluster_domain=target_cluster_domain,
                databases=databases,
                tables=tables,
                rollback_time=rollback_time,
                backup_id=backup_id,
            )
        )

    @mcp_tools_api_decorator(
        description=str(
            _(
                """创建 DB 权限克隆流程
参数说明：
- bk_cloud_id: 云区域 ID（可选，默认 0）
- address: 源实例地址 ip:port（必填）
- dest_addresses: 目标实例地址列表 ip:port（必填）
"""
            )
        ),
        request_slz=SubmitBillMySQLCloneGrantsInputSerializer,
        response_slz=SubmitBillOutputSerializer,
        permission_classes=[McpTicketToolPermission],
        mcp_auth_parser=auth_parse_instances,
        tags=[DBMMCPTags.READ, DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.MYSQL_BILL],
        enable_callee_plan=True,
        name_prefix="mysql_bill",
    )
    def submit_bill_mysql_clone_grants(self, request, *args, **kwargs):
        bk_cloud_id = self.get_param("bk_cloud_id")
        source_address = self.get_param("address")
        dest_addresses = self.get_param("dest_addresses")

        source_ip, source_port = source_address.split(":")
        try:
            m = Machine.objects.using(MYSQL_MCP_DB_READ).get(ip=source_ip, bk_cloud_id=bk_cloud_id)
        except MultipleObjectsReturned as e:
            raise DBMMcpBaseException(e)
        except Machine.DoesNotExist as e:
            raise DBMMcpBaseException(e)

        if m.cluster_type not in [ClusterType.TenDBSingle, ClusterType.TenDBHA, ClusterType.TenDBCluster]:
            raise DBMMcpNotSupportClusterTypeException(cluster_type=m.cluster_type)

        if m.machine_type not in [MachineType.SINGLE, MachineType.BACKEND, MachineType.REMOTE, MachineType.SPIDER]:
            raise DBMMcpNotSupportMachineTypeException(machine_type=m.machine_type)

        if m.machine_type == MachineType.SPIDER:
            cluster_ids = list(
                ProxyInstance.find_insts_by_addresses([source_address] + dest_addresses)
                .values_list("cluster__id", flat=True)
                .distinct()
            )
        else:
            cluster_ids = list(
                StorageInstance.find_insts_by_addresses([source_address] + dest_addresses)
                .values_list("cluster__id", flat=True)
                .distinct()
            )

        username = request.user.username
        if not username:
            raise DBMMcpUsernameNotFoundException()

        root_id = str(int(time.time()))
        data = {
            "uid": None,
            "created_by": username,
            "bk_biz_id": m.bk_biz_id,
            "bk_cloud_id": bk_cloud_id,
            "ticket_type": "",
        }

        if m.cluster_type == ClusterType.TenDBHA:
            p = mysql_clone_grants_from_file_subflow(
                root_id=root_id,
                data=copy.deepcopy(data),
                bk_cloud_id=bk_cloud_id,
                bk_biz_id=m.bk_biz_id,
                source_address=source_address,
                dest_addresses=dest_addresses,
            )
        else:
            p = spider_clone_grants_from_file_subflow(
                root_id=root_id,
                data=copy.deepcopy(data),
                bk_cloud_id=bk_cloud_id,
                bk_biz_id=m.bk_biz_id,
                source_address=source_address,
                dest_addresses=dest_addresses,
            )

        rp = Builder(root_id=root_id, data=copy.deepcopy(data), need_random_pass_cluster_ids=cluster_ids)
        rp.add_sub_pipeline(p)
        rp.run_pipeline(is_drop_random_user=True)

        return Response(
            [{"bill_id": root_id, "bill_url": f"{env.BK_SAAS_HOST}/{m.bk_biz_id}/task-history/detail/{root_id}"}]
        )

    @mcp_tools_api_decorator(
        description=str(
            _(
                """创建 MySQL 集群禁用单据（TenDBHA / TenDBSingle / TenDBCluster）
参数说明：
- bk_biz_id: 业务ID（必填）
- cluster_domains: 集群域名列表（必填，支持多个，可按集群类型自动拆分提单）

使用场景：对指定业务下的一个或多个 MySQL 系列集群发起禁用操作。
按集群类型分别生成对应禁用单据：TenDBHA → MYSQL_HA_DISABLE，TenDBSingle → MYSQL_SINGLE_DISABLE，TenDBCluster → TENDBCLUSTER_DISABLE。
"""
            )
        ),
        request_slz=SubmitBillMySQLDisableInputSerializer,
        response_slz=SubmitBillOutputSerializer,
        permission_classes=[McpTicketToolPermission],
        mcp_auth_parser=auth_parse_clusters,
        tags=[DBMMCPTags.READ, DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.MYSQL_BILL],
        name_prefix="mysql_bill",
    )
    def submit_bill_mysql_disable(self, request, *args, **kwargs):
        bk_biz_id = self.get_param("bk_biz_id")
        cluster_domains = list({d.strip() for d in self.get_param("cluster_domains") if d.strip()})

        assert_cluster_type(
            Cluster.objects.using(MYSQL_MCP_DB_READ).filter(immute_domain__in=cluster_domains),
            [ClusterType.TenDBSingle, ClusterType.TenDBHA, ClusterType.TenDBCluster],
        )

        username = request.user.username
        if not username:
            raise DBMMcpUsernameNotFoundException()

        return Response(
            bill_mysql_disable(
                username=username,
                bk_biz_id=bk_biz_id,
                cluster_domains=cluster_domains,
            )
        )

    @mcp_tools_api_decorator(
        description=str(
            _(
                """创建 MySQL 集群删除单据（TenDBHA / TenDBSingle / TenDBCluster）
参数说明：
- bk_biz_id: 业务ID（必填）
- cluster_domains: 集群域名列表（必填，支持多个，可按集群类型自动拆分提单）

前置条件：集群必须处于禁用状态（phase=offline）才可以提交删除单据，否则直接报错。
使用场景：对指定业务下已禁用的一个或多个 MySQL 系列集群发起删除操作。
按集群类型分别生成对应删除单据：TenDBHA → MYSQL_HA_DESTROY，TenDBSingle → MYSQL_SINGLE_DESTROY，TenDBCluster → TENDBCLUSTER_DESTROY。
"""
            )
        ),
        request_slz=SubmitBillMySQLDestroyInputSerializer,
        response_slz=SubmitBillOutputSerializer,
        permission_classes=[McpTicketToolPermission],
        mcp_auth_parser=auth_parse_clusters,
        tags=[DBMMCPTags.READ, DBMMCPTags.WRITE],
        mcp=[DBMMcpTools.MYSQL_BILL],
        name_prefix="mysql_bill",
    )
    def submit_bill_mysql_destroy(self, request, *args, **kwargs):
        bk_biz_id = self.get_param("bk_biz_id")
        cluster_domains = list({d.strip() for d in self.get_param("cluster_domains") if d.strip()})

        assert_cluster_type(
            Cluster.objects.using(MYSQL_MCP_DB_READ).filter(immute_domain__in=cluster_domains),
            [ClusterType.TenDBSingle, ClusterType.TenDBHA, ClusterType.TenDBCluster],
        )

        username = request.user.username
        if not username:
            raise DBMMcpUsernameNotFoundException()

        return Response(
            bill_mysql_destroy(
                username=username,
                bk_biz_id=bk_biz_id,
                cluster_domains=cluster_domains,
            )
        )
