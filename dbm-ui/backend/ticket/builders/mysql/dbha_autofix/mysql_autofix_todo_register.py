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

from backend.db_meta.enums import (
    ClusterType,
    ClusterTypeMachineTypeDefine,
    InstanceInnerRole,
    InstanceRole,
    InstanceStatus,
    MachineType,
)
from backend.db_meta.models import Cluster, ProxyInstance, StorageInstance
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
        instance_role = serializers.CharField()
        ip = serializers.IPAddressField()
        port = serializers.IntegerField()
        event_create_time = serializers.DateTimeField()
        dbha_gm_ip = serializers.IPAddressField()
        context_master_host = serializers.CharField()
        context_master_port = serializers.IntegerField()
        context_master_log_file = serializers.CharField()
        context_master_log_pos = serializers.IntegerField()
        status = serializers.CharField()  # 自愈用不到, 并且 event 传来的应该恒为 running

        def validate(self, attrs):
            from django.core.exceptions import ObjectDoesNotExist

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
            self.__validate_consistency_instance_status(attrs=attrs)
            self.__validate_consistency_instance_inner_role(attrs=attrs)
            self.__validate_consistency_instance_role(attrs=attrs)
            if attrs.get("instance_role") in [InstanceRole.BACKEND_MASTER, InstanceRole.REMOTE_MASTER]:
                self.__validate_context(attrs=attrs)

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

        @staticmethod
        def __validate_consistency_instance_status(attrs):
            """
            检查单机多实例是否一起切换
            多实例状态需要一致
            而且必须是 unavailable
            """
            machine_type = attrs.get("machine_type")
            bk_cloud_id = attrs.get("bk_cloud_id")
            ip = attrs.get("ip")

            if (
                machine_type in [MachineType.PROXY, MachineType.SPIDER]
                and ProxyInstance.objects.filter(machine__bk_cloud_id=bk_cloud_id, machine__ip=ip)
                .exclude(status=InstanceStatus.UNAVAILABLE.value)
                .exists()
            ) or (
                machine_type in [MachineType.BACKEND, MachineType.REMOTE, MachineType.SINGLE]
                and StorageInstance.objects.filter(machine__bk_cloud_id=bk_cloud_id, machine__ip=ip)
                .exclude(status=InstanceStatus.UNAVAILABLE.value)
                .exists()
            ):
                raise serializers.ValidationError(
                    "instances status != {} found on {}, not switch at same time".format(
                        InstanceStatus.UNAVAILABLE.value, ip
                    )
                )

        @staticmethod
        def __validate_consistency_instance_inner_role(attrs):
            """
            检查单机多实例是否一起切换
            多实例角色需要一致
            而且 instance inner role 必须是 slave
            """
            machine_type = attrs.get("machine_type")
            bk_cloud_id = attrs.get("bk_cloud_id")
            ip = attrs.get("ip")

            if (
                machine_type in [MachineType.BACKEND, MachineType.REMOTE]
                and StorageInstance.objects.filter(machine__bk_cloud_id=bk_cloud_id, machine__ip=ip)
                .exclude(instance_inner_role=InstanceInnerRole.SLAVE.value)
                .exists()
            ):
                raise serializers.ValidationError(
                    "instances inner role != {} found on {}, not switch at same time".format(
                        InstanceInnerRole.SLAVE.value, ip
                    )
                )

        @staticmethod
        def __validate_consistency_instance_role(attrs):
            """
            检查单机多实例是否一起切换
            多实例角色需要一致
            而且 instance role 必须是 [backend_slave, remote_slave]
            """
            machine_type = attrs.get("machine_type")
            bk_cloud_id = attrs.get("bk_cloud_id")
            ip = attrs.get("ip")

            if (
                machine_type in [MachineType.BACKEND, MachineType.REMOTE]
                and StorageInstance.objects.filter(machine__bk_cloud_id=bk_cloud_id, machine__ip=ip)
                .exclude(instance_role__in=[InstanceRole.BACKEND_SLAVE.value, InstanceRole.REMOTE_SLAVE.value])
                .exists()
            ):
                raise serializers.ValidationError(
                    "instances role != [{}, {}] found on {}, not switch at same time".format(
                        InstanceRole.BACKEND_SLAVE.value, InstanceRole.REMOTE_SLAVE.value, ip
                    )
                )

        @staticmethod
        def __validate_context(attrs):
            context_master_host = attrs.get("context_master_host")
            context_master_port = attrs.get("context_master_port")
            context_master_log_file = attrs.get("context_master_log_file")
            context_master_log_pos = attrs.get("context_master_log_pos")
            ip = attrs.get("ip")
            port = attrs.get("port")

            if (
                context_master_host != ip
                or context_master_port != port
                or context_master_log_file == ""
                or context_master_log_pos == 0
            ):
                raise serializers.ValidationError(
                    "master_host = '{}', \
                    master_port = {}, \
                    master_log_file = '{}', \
                    master_log_pos = {} \
                    not a valid position info".format(
                        context_master_host, context_master_port, context_master_log_file, context_master_log_pos
                    )
                )

            return attrs

    infos = serializers.ListField(help_text=_("详情"), child=MySQLDBHAAutofixRegisterInfoSerializer())


class MySQLDBHAAlarmTransformSerializer(AlarmCallBackDataSerializer):
    def to_internal_value(self, data):
        data = super().to_internal_value(data)
        dimensions = data["callback_message"]["event"]["dimensions"]

        cluster_obj = Cluster.objects.get(immute_domain=dimensions["cluster_domain"])

        ticket_detail = {
            "infos": [
                {
                    "bk_cloud_id": dimensions.get("bk_cloud_id", 0),
                    "bk_biz_id": dimensions.get("appid", 0),
                    "check_id": dimensions.get("double_check_id", 0),
                    "cluster_id": cluster_obj.id,
                    "cluster_type": cluster_obj.cluster_type,
                    "immute_domain": cluster_obj.immute_domain,
                    "machine_type": dimensions.get("machine_type", ""),
                    "instance_role": dimensions.get("role", ""),
                    "ip": dimensions.get("server_ip", ""),
                    "port": dimensions.get("server_port", 0),
                    "event_create_time": data["callback_message"]["event"]["create_time"],
                    "dbha_gm_ip": dimensions.get("target", ""),
                    "context_master_host": dimensions.get("master_host", ""),
                    "context_master_port": dimensions.get("master_port", 0),
                    "context_master_log_file": dimensions.get("master_log_file", ""),
                    "context_master_log_pos": dimensions.get("master_log_pos", 0),
                    "status": dimensions.get("status", ""),  # 自愈用不到, 并且 event 传来的应该恒为 running
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
