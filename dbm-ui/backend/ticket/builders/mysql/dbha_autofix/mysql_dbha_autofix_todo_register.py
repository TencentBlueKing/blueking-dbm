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
from django.core.exceptions import ObjectDoesNotExist
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from backend.db_meta.enums import ClusterType, ClusterTypeMachineTypeDefine
from backend.db_meta.models import Cluster
from backend.db_monitor.serializers import AlarmCallBackDataSerializer
from backend.flow.engine.controller.mysql import MySQLController
from backend.ticket import builders
from backend.ticket.builders.common.base import SkipToRepresentationMixin
from backend.ticket.builders.mysql.base import BaseMySQLTicketFlowBuilder
from backend.ticket.constants import TicketType


class MySQLDBHAAutofixRegisterDetailSerializer(SkipToRepresentationMixin, serializers.Serializer):
    class MySQLDBHAAutofixRegisterInfoSerializer(serializers.Serializer):
        bk_cloud_id = serializers.IntegerField()
        bk_biz_id = serializers.IntegerField()
        check_id = serializers.IntegerField()
        immute_domain = serializers.CharField()
        machine_type = serializers.CharField()
        ip = serializers.IPAddressField()
        port = serializers.IntegerField()
        event_create_time = serializers.DateTimeField()

        def validate(self, attrs):

            try:
                cluster_obj = Cluster.objects.get(
                    bk_cloud_id=attrs.get("bk_cloud_id"),
                    bk_biz_id=attrs.get("bk_biz_id"),
                    immute_domain=attrs.get("immute_domain"),
                )
            except ObjectDoesNotExist:
                raise serializers.ValidationError(
                    "bk_cloud_id: {}, bk_biz_id: {} cluster: {} not found".format(
                        attrs.get("bk_cloud_id"),
                        attrs.get("bk_biz_id"),
                        attrs.get("immute_domain"),
                    )
                )

            self.__validate_cluster_type(cluster_type=cluster_obj.cluster_type, attrs=attrs)
            self.__validate_machine_type_match(cluster_type=cluster_obj.cluster_type, attrs=attrs)

            return attrs

        @staticmethod
        def __validate_cluster_type(cluster_type, attrs):
            """
            集群类型限定为 TenDBSingle, TenDBHA, TenDBCluster
            """
            if cluster_type not in [ClusterType.TenDBSingle, ClusterType.TenDBHA, ClusterType.TenDBCluster]:
                raise serializers.ValidationError("{} not a mysql cluster type".format(cluster_type))

            return attrs

        @staticmethod
        def __validate_machine_type_match(cluster_type, attrs):
            """
            检查 machine_type 和 cluster_type 是否匹配
            """
            machine_type = attrs.get("machine_type")
            if machine_type not in ClusterTypeMachineTypeDefine[cluster_type]:
                raise serializers.ValidationError(
                    "{} not a valid machine_type for {}".format(machine_type, cluster_type)
                )

            return attrs

    infos = serializers.ListField(help_text=_("详情"), child=MySQLDBHAAutofixRegisterInfoSerializer())


class MySQLDBHAAlarmTransformSerializer(AlarmCallBackDataSerializer):
    def to_internal_value(self, data):
        data = super().to_internal_value(data)
        dimensions = data["callback_message"]["event"]["dimensions"]

        ticket_detail = {
            "infos": [
                {
                    "bk_cloud_id": dimensions.get("bk_cloud_id", 0),
                    "bk_biz_id": dimensions.get("appid", 0),
                    "check_id": dimensions.get("double_check_id", 0),
                    "immute_domain": dimensions["cluster_domain"],
                    "machine_type": dimensions.get("machine_type", ""),
                    "ip": dimensions.get("server_ip", ""),
                    "port": dimensions.get("server_port", 0),
                    "event_create_time": data["callback_message"]["event"]["create_time"],
                }
            ]
        }
        return ticket_detail


class MySQLDBHAAutofixRegisterInnerFlowBuilder(builders.FlowParamBuilder):
    controller = MySQLController.dbha_autofix_register_scene

    def format_ticket_data(self):
        super().format_ticket_data()


@builders.BuilderFactory.register(TicketType.MYSQL_AUTOFIX_TODO_REGISTER, is_apply=True)
class MySQLDBHAAutofixRegisterFlowBuilder(BaseMySQLTicketFlowBuilder):
    serializer = MySQLDBHAAutofixRegisterDetailSerializer
    alarm_transform_serializer = MySQLDBHAAlarmTransformSerializer
    inner_flow_builder = MySQLDBHAAutofixRegisterInnerFlowBuilder
    inner_flow_name = _("MySQL DBHA 故障自愈任务注册")
    default_need_itsm = False
    default_need_manual_confirm = False

    @property
    def need_itsm(self):
        return False
