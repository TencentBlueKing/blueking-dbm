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
from backend.db_meta.models import Cluster, StorageInstance
from backend.flow.consts import MySQLBackupFileTagEnum, MySQLBackupTypeEnum
from backend.flow.engine.controller.mysql import MySQLController
from backend.ticket import builders
from backend.ticket.builders.mysql.base import BaseMySQLHATicketFlowBuilder, MySQLBaseOperateDetailSerializer
from backend.ticket.constants import FlowRetryType, TicketType


class MySQLFullBackupDetailSerializer(MySQLBaseOperateDetailSerializer):
    class MySQLFullBackupInfoSerializer(serializers.Serializer):
        cluster_id = serializers.IntegerField(help_text=_("集群ID"))
        backup_local = serializers.ChoiceField(
            help_text=_("备份位置"), choices=InstanceInnerRole.get_choices(), default=InstanceInnerRole.SLAVE.value
        )

    backup_type = serializers.ChoiceField(help_text=_("备份类型"), choices=MySQLBackupTypeEnum.get_choices())
    file_tag = serializers.ChoiceField(help_text=_("备份文件tag"), choices=MySQLBackupFileTagEnum.get_choices())
    infos = serializers.ListSerializer(child=MySQLFullBackupInfoSerializer())

    def validate(self, attrs):
        attrs = super(MySQLBaseOperateDetailSerializer, self).validate(attrs)
        cluster_ids = [info["cluster_id"] for info in attrs["infos"]]

        errors = []

        msg = self.__validate_cluster_id_unique(cluster_ids=cluster_ids)
        if msg:
            errors.append(msg)

        msg = self.__validate_cluster_type(cluster_ids=cluster_ids)
        if msg:
            errors.append(msg)

        msg = self.__validate_backup_local(attrs=attrs)
        if msg:
            errors.append(msg)

        msg = self.__validate_cluster_status(attrs=attrs)
        if msg:
            errors.append(msg)

        if errors:
            raise serializers.ValidationError(errors)

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
    def __validate_backup_local(attrs) -> str:
        bad = []

        for info in attrs["infos"]:
            backup_local = info["backup_local"]
            cluster_id = info["cluster_id"]
            cluster_obj = Cluster.objects.get(pk=cluster_id)

            # 为了体验统一, single 也传入 master
            # 后端得用 orphan
            if cluster_obj.cluster_type == ClusterType.TenDBSingle and backup_local != "master":
                bad.append(_("{} 备份位置只能是 {}".format(cluster_obj.immute_domain, "master")))
            elif cluster_obj.cluster_type == ClusterType.TenDBHA and backup_local not in [
                InstanceInnerRole.MASTER,
                InstanceInnerRole.SLAVE,
            ]:
                bad.append(
                    str(
                        _(
                            "{} 备份位置只能是 {}".format(
                                cluster_obj.immute_domain, [InstanceInnerRole.MASTER, InstanceInnerRole.SLAVE]
                            )
                        )
                    )
                )

        if bad:
            return ", ".join(bad)

    @staticmethod
    def __validate_cluster_status(attrs) -> str:
        bad = []

        for info in attrs["infos"]:
            backup_local = info["backup_local"]
            cluster_id = info["cluster_id"]
            cluster_obj = Cluster.objects.get(pk=cluster_id)

            if cluster_obj.cluster_type == ClusterType.TenDBSingle:
                backup_local = InstanceInnerRole.ORPHAN

            if not StorageInstance.objects.filter(
                cluster=cluster_obj, instance_inner_role=backup_local, is_stand_by=True, status=InstanceStatus.RUNNING
            ).exists():
                bad.append(
                    str(
                        _(
                            "{} 没找到正常的 {} 实例".format(
                                cluster_obj.immute_domain,
                                backup_local,
                            )
                        )
                    )
                )

        if bad:
            return ", ".join(bad)


class MySQLFullBackupFlowParamBuilder(builders.FlowParamBuilder):
    """TenDB HA 备份执行单据参数"""

    controller = MySQLController.mysql_full_backup_scene


@builders.BuilderFactory.register(TicketType.MYSQL_HA_FULL_BACKUP)
class TenDBHAFullBackupFlowBuilder(BaseMySQLHATicketFlowBuilder):
    serializer = MySQLFullBackupDetailSerializer
    inner_flow_builder = MySQLFullBackupFlowParamBuilder
    inner_flow_name = _("MySQL 全库备份执行")
    retry_type = FlowRetryType.MANUAL_RETRY
