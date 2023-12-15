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

from backend.db_meta.models import Cluster
from backend.db_meta.models.extra_process import ExtraProcessInstance
from backend.ticket.constants import FlowType, TicketFlowStatus, TicketStatus, TicketType
from backend.ticket.models import Flow, Ticket

from . import mock_data
from .models import DumperSubscribeConfig


class DumperSubscribeConfigSerializer(serializers.ModelSerializer):
    class SubscribeInfoSerializer(serializers.Serializer):
        db_name = serializers.CharField(help_text=_("DB名称"))
        table_names = serializers.ListField(help_text=_("表名列表"), child=serializers.CharField())

    repl_tables = serializers.ListSerializer(help_text=_("配置表信息"), child=SubscribeInfoSerializer())
    instance_count = serializers.SerializerMethodField(help_text=_("dumper实例数"), read_only=True)
    dumper_instances = serializers.SerializerMethodField(help_text=_("dumper实例列表"), read_only=True)
    running_tasks = serializers.SerializerMethodField(help_text=_("正在部署dumper的任务列表"), read_only=True)

    class Meta:
        model = DumperSubscribeConfig
        fields = "__all__"
        swagger_schema_fields = {"example": mock_data.DUMPER_CONFIG_DATA}

    def get_instance_count(self, obj):
        return len(obj.dumper_process_ids)

    def get_dumper_instances(self, obj):
        """补充dumper配置关联的dumper实例信息，这个字段只在详情展示"""
        if self.context["view"].action != "retrieve":
            return None

        # 获取dumper配置关联的dumper instance
        dumpers = ExtraProcessInstance.objects.filter(id__in=obj.dumper_process_ids)
        cluster_ids = [dumper.cluster_id for dumper in dumpers]
        cluster_id__domain = {
            cluster.id: cluster.immute_domain for cluster in Cluster.objects.filter(id__in=cluster_ids)
        }
        # 获取dumper实例的同步方式、源集群、接收端协议、接收端地址和dumper id
        dumper_data_list = [
            {
                "source_cluster_domain": cluster_id__domain[dumper.cluster_id],
                "protocol_type": dumper.extra_config["protocol_type"],
                "dumper_id": dumper.extra_config["dumper_id"],
                "target_address": f"{dumper.extra_config['target_address']}:{dumper.extra_config['target_port']}",
                "add_type": dumper.extra_config["add_type"],
            }
            for dumper in dumpers
        ]
        return dumper_data_list

    def get_running_tasks(self, obj):
        """获取正在运行的任务，这个字段只在详情展示"""
        if self.context["view"].action != "retrieve":
            return None

        ticket_ids = Ticket.objects.filter(
            bk_biz_id=obj.bk_biz_id,
            ticket_type=TicketType.TBINLOGDUMPER_INSTALL,
            status=TicketStatus.RUNNING,
            details__name=obj.name,
        ).values_list("id", flat=True)

        flow_obj_ids = Flow.objects.filter(
            ticket_id__in=list(ticket_ids), flow_type=FlowType.INNER_FLOW, status=TicketFlowStatus.RUNNING
        ).values_list("flow_obj_id", flat=True)

        return list(flow_obj_ids)


class DumperInstanceConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = ExtraProcessInstance
        fields = "__all__"
        swagger_schema_fields = {"example": mock_data.DUMPER_INSTANCE_LIST_DATA}


class VerifyDuplicateNamsSerializer(serializers.Serializer):
    name = serializers.CharField(help_text=_("订阅配置名称"))
