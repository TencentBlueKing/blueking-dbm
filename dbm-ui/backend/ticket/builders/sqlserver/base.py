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
from rest_framework import serializers

from backend.configuration.constants import DBType
from backend.db_meta.enums import ClusterSqlserverStatusFlags, ClusterType
from backend.db_meta.models import Cluster
from backend.ticket import builders
from backend.ticket.builders import TicketFlowBuilder
from backend.ticket.builders.common.base import (
    BaseOperateResourceParamBuilder,
    CommonValidate,
    SkipToRepresentationMixin,
    SQLServerTicketFlowBuilderPatchMixin,
    fetch_cluster_ids,
)
from backend.ticket.builders.mysql.base import MySQLClustersTakeDownDetailsSerializer
from backend.ticket.constants import TicketType


class BaseSQLServerTicketFlowBuilder(SQLServerTicketFlowBuilderPatchMixin, TicketFlowBuilder):
    group = DBType.Sqlserver.value


class SQLServerBasePauseParamBuilder(builders.PauseParamBuilder):
    pass


class SQLServerTakeDownDetailsSerializer(MySQLClustersTakeDownDetailsSerializer):
    """sqlserver的下架逻辑同mysql"""

    pass


class SQLServerBaseOperateDetailSerializer(SkipToRepresentationMixin, serializers.Serializer):
    """
    sqlserver操作的基类，主要功能:
    1. 屏蔽序列化的to_representation
    2. 存放sqlserver操作的各种校验逻辑
    """

    # 实例不可用时，还能正常提单类型的白名单
    SLAVE_UNAVAILABLE_WHITELIST = [
        TicketType.SQLSERVER_IMPORT_SQLFILE.value,
        TicketType.SQLSERVER_DBRENAME.value,
        TicketType.SQLSERVER_CLEAR_DBS.value,
        TicketType.SQLSERVER_BACKUP_DBS.value,
        TicketType.SQLSERVER_FULL_MIGRATE.value,
        TicketType.SQLSERVER_INCR_MIGRATE.value,
        TicketType.SQLSERVER_ROLLBACK.value,
        TicketType.SQLSERVER_RESTORE_SLAVE.value,
        TicketType.SQLSERVER_RESTORE_LOCAL_SLAVE.value,
        TicketType.SQLSERVER_ADD_SLAVE.value,
        TicketType.SQLSERVER_AUTHORIZE_RULES.value,
    ]
    MASTER_UNAVAILABLE_WHITELIST = [
        TicketType.SQLSERVER_MASTER_FAIL_OVER.value,
    ]
    # 集群的flag状态与白名单的映射表
    unavailable_whitelist__status_flag = {
        ClusterSqlserverStatusFlags.BackendSlaveUnavailable: SLAVE_UNAVAILABLE_WHITELIST,
        ClusterSqlserverStatusFlags.BackendMasterUnavailable: MASTER_UNAVAILABLE_WHITELIST,
    }

    def validate_cluster_can_access(self, attrs):
        """校验集群状态是否可以提单"""
        clusters = Cluster.objects.filter(id__in=fetch_cluster_ids(details=attrs))
        ticket_type = self.context["ticket_type"]

        for cluster in clusters:
            if cluster.cluster_type == ClusterType.SqlserverSingle:
                # 如果副本集异常，则直接报错
                if cluster.status_flag:
                    raise serializers.ValidationError(_("副本集实例状态异常，暂时无法执行该单据类型：{}").format(ticket_type))
                continue

            for status_flag, whitelist in self.unavailable_whitelist__status_flag.items():
                if cluster.status_flag & status_flag and ticket_type not in whitelist:
                    raise serializers.ValidationError(
                        _("集群实例状态异常:{}，暂时无法执行该单据类型：{}").format(status_flag.flag_text(), ticket_type)
                    )

        return attrs

    def validated_cluster_type(self, attrs, cluster_type: ClusterType):
        """校验集群类型为高可用"""
        cluster_ids = fetch_cluster_ids(attrs)
        CommonValidate.validated_cluster_type(cluster_ids, cluster_type)

    def validate_database_table_selector(self, attrs, role_key=None):
        """校验库表选择器的数据是否合法"""
        is_valid, message = CommonValidate.validate_sqlserver_table_selector(
            bk_biz_id=self.context["bk_biz_id"], infos=attrs["infos"], role_key=role_key
        )
        if not is_valid:
            raise serializers.ValidationError(message)

    def validate(self, attrs):
        # 默认全局校验只需要校验集群的状态
        return attrs


class SQLServerBaseOperateResourceParamBuilder(BaseOperateResourceParamBuilder):
    def format(self):
        super().format()

    def post_callback(self):
        super().post_callback()
