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

from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from backend.db_meta.enums import ClusterSqlserverStatusFlags, InstanceInnerRole
from backend.db_meta.models import Cluster
from backend.flow.consts import SqlserverBackupFileTagEnum, SqlserverBackupMode
from backend.flow.engine.controller.sqlserver import SqlserverController
from backend.ticket import builders
from backend.ticket.builders.common.base import fetch_cluster_ids
from backend.ticket.builders.sqlserver.base import BaseSQLServerTicketFlowBuilder, SQLServerBaseOperateDetailSerializer
from backend.ticket.constants import FlowRetryType, TicketType


class SQLServerBackupDetailSerializer(SQLServerBaseOperateDetailSerializer):
    class BackupDataInfoSerializer(serializers.Serializer):
        cluster_id = serializers.IntegerField(help_text=_("集群ID"))
        backup_dbs = serializers.ListField(help_text=_("备份db列表"), child=serializers.CharField())
        db_list = serializers.ListField(help_text=_("库正则"), child=serializers.CharField(), required=False)
        ignore_db_list = serializers.ListField(help_text=_("忽略库正则"), child=serializers.CharField(), required=False)

    backup_place = serializers.CharField(help_text=_("备份位置(先固定为master)"), required=False, default="master")
    backup_type = serializers.ChoiceField(
        help_text=_("备份方式"), choices=SqlserverBackupMode.get_choices(), required=False
    )
    file_tag = serializers.ChoiceField(help_text=_("备份保存时间"), choices=SqlserverBackupFileTagEnum.get_choices())
    infos = serializers.ListSerializer(help_text=_("备份信息列表"), child=BackupDataInfoSerializer())

    def validate(self, attrs):
        """验证库表数据库的数据"""
        super().validate(attrs)
        # 库表选择器校验
        super().validate_database_table_selector(attrs)
        # 校验集群是否可用
        try:
            self.validate_cluster_can_access(attrs)
        except serializers.ValidationError as e:
            clusters = Cluster.objects.filter(id__in=fetch_cluster_ids(details=attrs))
            id__cluster = {cluster.id: cluster for cluster in clusters}
            # 如果备份位置选的是master，但是slave异常，则认为是可以的
            if attrs["backup_place"] != InstanceInnerRole.MASTER:
                raise serializers.ValidationError(e)
            for info in attrs["infos"]:
                if id__cluster[info["cluster_id"]].status_flag & ClusterSqlserverStatusFlags.BackendMasterUnavailable:
                    raise serializers.ValidationError(e)
        return attrs


class SQLServerBackupFlowParamBuilder(builders.FlowParamBuilder):
    controller = SqlserverController.backup_dbs_scene


@builders.BuilderFactory.register(TicketType.SQLSERVER_BACKUP_DBS)
class SQLServerBackupFlowBuilder(BaseSQLServerTicketFlowBuilder):
    serializer = SQLServerBackupDetailSerializer
    inner_flow_builder = SQLServerBackupFlowParamBuilder
    inner_flow_name = _("SQLServer 库表备份执行")
    retry_type = FlowRetryType.MANUAL_RETRY
