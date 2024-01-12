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
import itertools

from django.db.models import Q
from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from backend.db_meta.enums import ClusterType, InstanceInnerRole
from backend.db_meta.enums.extra_process_type import ExtraProcessType
from backend.db_meta.models.extra_process import ExtraProcessInstance
from backend.flow.engine.controller.mysql import MySQLController
from backend.flow.engine.controller.tbinlogdumper import TBinlogDumperController
from backend.ticket import builders
from backend.ticket.builders.common.base import HostInfoSerializer
from backend.ticket.builders.mysql.base import (
    BaseMySQLTicketFlowBuilder,
    MySQLBaseOperateDetailSerializer,
    MySQLBasePauseParamBuilder,
)
from backend.ticket.constants import FlowRetryType, FlowType, TicketFlowStatus, TicketType
from backend.ticket.models import Flow


class MysqlMasterSlaveSwitchDetailSerializer(MySQLBaseOperateDetailSerializer):
    class InfoSerializer(serializers.Serializer):
        master_ip = HostInfoSerializer(help_text=_("主库 IP"))
        slave_ip = HostInfoSerializer(help_text=_("从库 IP"))
        cluster_ids = serializers.ListField(help_text=_("集群ID列表"), child=serializers.IntegerField())

    infos = serializers.ListField(help_text=_("单据信息"), child=InfoSerializer())
    is_check_process = serializers.BooleanField(help_text=_("是否检测连接"), default=False, required=False)
    is_check_delay = serializers.BooleanField(
        help_text=_("是否检测数据同步延时情况(互切单据延时属于强制检测，故必须传True)"), default=False, required=False
    )
    is_verify_checksum = serializers.BooleanField(help_text=_("是否检测历史数据检验结果"), default=False, required=False)

    def validate(self, attrs):
        # 校验集群是否可用，集群类型为高可用
        super().validate_cluster_can_access(attrs)
        super().validate_cluster_type(attrs, ClusterType.TenDBHA)

        # 校验master和slave的关联集群是否一致
        super().validate_instance_related_clusters(
            attrs, instance_key=["master_ip"], cluster_key=["cluster_ids"], role=InstanceInnerRole.MASTER
        )
        super().validate_instance_related_clusters(
            attrs, instance_key=["slave_ip"], cluster_key=["cluster_ids"], role=InstanceInnerRole.SLAVE
        )

        # 校验从库的is_stand_by标志必须为true
        super().validate_slave_is_stand_by(attrs)

        return attrs


class MysqlMasterSlaveSwitchParamBuilder(builders.FlowParamBuilder):
    controller = MySQLController.mysql_ha_switch_scene

    def post_callback(self):
        # 如果当前流程并没有执行成功，则忽略
        if self.ticket.current_flow().status != TicketFlowStatus.SUCCEEDED:
            return

        dumper_migrate_flow = self.ticket.next_flow()
        # 如果没有有效的切换信息，就跳过dumper切换流程
        switch_infos = [info for info in self.ticket_data.get("switch_infos", []) if info["switch_instances"]]
        if not switch_infos:
            flow_filter = Q(
                ticket=self.ticket,
                details__controller_info__func_name=MysqlDumperMigrateParamBuilder.controller.__name__,
            )
            # 用save方法来触发ticket单据更新的信号
            for flow in Flow.objects.filter(flow_filter):
                flow.status = TicketFlowStatus.SKIPPED
                flow.save(update_fields=["status"])
            return

        dumper_migrate_flow.details["ticket_data"]["infos"] = switch_infos
        dumper_migrate_flow.save(update_fields=["details"])


class MysqlDumperMigrateParamBuilder(builders.FlowParamBuilder):
    controller = TBinlogDumperController.switch_nodes_scene

    def format_ticket_data(self):
        # 默认以安全模式迁移
        self.ticket_data["ticket_type"] = TicketType.TBINLOGDUMPER_SWITCH_NODES
        self.ticket_data["is_safe"] = True


@builders.BuilderFactory.register(TicketType.MYSQL_MASTER_SLAVE_SWITCH)
class MysqlMasterSlaveSwitchFlowBuilder(BaseMySQLTicketFlowBuilder):
    serializer = MysqlMasterSlaveSwitchDetailSerializer
    inner_flow_builder = MysqlMasterSlaveSwitchParamBuilder
    inner_flow_name = _("主从互换执行")
    dumper_flow_builder = MysqlDumperMigrateParamBuilder
    retry_type = FlowRetryType.MANUAL_RETRY
    pause_node_builder = MySQLBasePauseParamBuilder

    def check_cluster_dumper_migrate(self):
        cluster_ids = list(itertools.chain(*[info["cluster_ids"] for info in self.ticket.details["infos"]]))
        dumper_instances = ExtraProcessInstance.objects.filter(
            cluster_id__in=cluster_ids, proc_type=ExtraProcessType.TBINLOGDUMPER
        )
        # 补充单据详情的dumper_instance_ids，用于dumper迁移状态查询
        if dumper_instances.exists():
            dumper_instance_ids = [dumper.id for dumper in dumper_instances]
            self.ticket.update_details(dumper_instance_ids=dumper_instance_ids)
        return dumper_instances.exists()

    def custom_ticket_flows(self):
        # 主从切换流程
        flows = [
            Flow(
                ticket=self.ticket,
                flow_type=FlowType.INNER_FLOW.value,
                details=self.inner_flow_builder(self.ticket).get_params(),
                flow_alias=self.inner_flow_name,
                retry_type=self.retry_type,
            )
        ]
        # 如果存在dumper，则串dumper迁移流程
        if self.check_cluster_dumper_migrate():
            flows.append(
                Flow(
                    ticket=self.ticket,
                    flow_type=FlowType.INNER_FLOW.value,
                    details=self.dumper_flow_builder(self.ticket).get_params(),
                    flow_alias=_("dumper 迁移"),
                    retry_type=self.retry_type,
                )
            )

        return flows
