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

import collections

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from backend.db_meta.enums import ClusterType, InstanceInnerRole, InstanceStatus
from backend.db_meta.models import Cluster
from backend.flow.engine.controller.mysql import MySQLController
from backend.ticket import builders
from backend.ticket.builders.mysql.base import (
    BaseMySQLHATicketFlowBuilder,
    DBTableField,
    MySQLBaseOperateDetailSerializer,
)
from backend.ticket.constants import FlowRetryType, TicketType


class MySQLDBTableBackupDetailSerializer(MySQLBaseOperateDetailSerializer):
    class DBTableBackupDataInfoSerializer(serializers.Serializer):
        cluster_id = serializers.IntegerField(help_text=_("集群ID"))
        db_patterns = serializers.ListField(help_text=_("匹配DB列表"), child=DBTableField(db_field=True))
        ignore_dbs = serializers.ListField(help_text=_("忽略DB列表"), child=DBTableField(db_field=True))
        table_patterns = serializers.ListField(help_text=_("匹配Table列表"), child=DBTableField())
        ignore_tables = serializers.ListField(help_text=_("忽略Table列表"), child=DBTableField())

    infos = serializers.ListSerializer(help_text=_("备份信息列表"), child=DBTableBackupDataInfoSerializer())

    def validate(self, attrs):
        """验证库表数据库的数据"""
        super().validate(attrs)
        cluster_ids = [info["cluster_id"] for info in attrs["infos"]]

        errors = []

        # msg = self.__validate_cluster_id_unique(cluster_ids=cluster_ids)
        # if msg:
        #     errors.append(msg)

        msg = self.__validate_cluster_type(cluster_ids=cluster_ids)
        if msg:
            errors.append(msg)

        msg = self.__validate_cluster_exists(cluster_ids=cluster_ids)
        if msg:
            errors.append(msg)

        msg = self.__validate_cluster_status(cluster_ids=cluster_ids)
        if msg:
            errors.append(msg)

        if errors:
            raise serializers.ValidationError(errors)

        # 库表选择器校验
        super().validate_database_table_selector(attrs)

        return attrs

    @staticmethod
    def __validate_cluster_id_unique(cluster_ids) -> str:
        """
        集群 id 不能重复出现
        """
        dup_cluster_ids = [cid for cid, cnt in collections.Counter(cluster_ids).items() if cnt > 1]
        if dup_cluster_ids:
            return _(
                "重复输入集群: {}".format(
                    Cluster.objects.filter(pk__in=dup_cluster_ids).values_list("immute_domain", flat=True)
                )
            )

    @staticmethod
    def __validate_cluster_type(cluster_ids) -> str:
        """
        集群类型不能混合
        """
        bad = []
        cluster_types = []
        for cluster_obj in Cluster.objects.filter(pk__in=cluster_ids):
            if cluster_obj.cluster_type not in [ClusterType.TenDBHA, ClusterType.TenDBSingle]:
                bad.append(str(_("不支持的集群类型 {} {}".format(cluster_obj.immute_domain, cluster_obj.cluster_type))))

            cluster_types.append(cluster_obj.cluster_type)

        # if len(cluster_types) > 1:
        #     bad.append(_("集群类型混合输入"))

        if bad:
            return ", ".join(bad)

    @staticmethod
    def __validate_cluster_exists(cluster_ids) -> str:
        """
        集群 id 必须存在
        """
        exists_cluster_ids = list(
            Cluster.objects.filter(
                pk__in=cluster_ids, cluster_type__in=[ClusterType.TenDBHA, ClusterType.TenDBSingle]
            ).values_list("id", flat=True)
        )
        not_exists_cluster_ids = list(set(cluster_ids) - set(exists_cluster_ids))
        if not_exists_cluster_ids:
            return _("cluster id: {} 不存在".format(cluster_ids))

    @staticmethod
    def __validate_cluster_status(cluster_ids) -> str:
        """
        库表备份强制在 slave 备份, 所以集群的 standby slave 必须正常
        """
        bad = []
        for cluster_id in cluster_ids:
            cluster_obj = Cluster.objects.get(pk=cluster_id)
            if (
                cluster_obj.cluster_type == ClusterType.TenDBHA
                and not cluster_obj.storageinstance_set.filter(
                    status=InstanceStatus.RUNNING, is_stand_by=True, instance_inner_role=InstanceInnerRole.SLAVE
                ).exists()
            ):
                bad.append(_("{} 缺少状态正常的 standby slave".format(cluster_obj.immute_domain)))
            elif not cluster_obj.storageinstance_set.filter(status=InstanceStatus.RUNNING).exists():
                bad.append(_("{} 缺少状态正常的存储实例".format(cluster_obj.immute_domain)))

        if bad:
            return _("{} 缺少状态正常的 standby slave".format(bad))


class MySQLDBTableBackupFlowParamBuilder(builders.FlowParamBuilder):
    controller = MySQLController.mysql_db_table_backup_scene


@builders.BuilderFactory.register(TicketType.MYSQL_HA_DB_TABLE_BACKUP)
class TenDBHADBTableBackupFlowBuilder(BaseMySQLHATicketFlowBuilder):
    serializer = MySQLDBTableBackupDetailSerializer
    inner_flow_builder = MySQLDBTableBackupFlowParamBuilder
    inner_flow_name = _("MySQL 库表备份执行")
    retry_type = FlowRetryType.MANUAL_RETRY
