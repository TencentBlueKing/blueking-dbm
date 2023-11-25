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

from datetime import datetime

from django.db.models import Q
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from backend.db_meta.enums import InstanceInnerRole
from backend.db_meta.models import Cluster, StorageInstance
from backend.db_services.mysql.dataclass import DBInstance
from backend.flow.engine.controller.mysql import MySQLController
from backend.ticket import builders
from backend.ticket.builders.common.base import InstanceInfoSerializer
from backend.ticket.builders.common.constants import MySQLChecksumTicketMode, MySQLDataRepairTriggerMode
from backend.ticket.builders.mysql.base import (
    BaseMySQLTicketFlowBuilder,
    DBTableField,
    MySQLBaseOperateDetailSerializer,
)
from backend.ticket.constants import FlowRetryType, FlowType, TicketFlowStatus, TicketType
from backend.ticket.models import Flow
from backend.utils.time import str2datetime


class MySQLChecksumDetailSerializer(MySQLBaseOperateDetailSerializer):
    class ChecksumDataInfoSerializer(serializers.Serializer):
        slaves = serializers.ListField(help_text=_("slave信息列表"), child=InstanceInfoSerializer())
        db_patterns = serializers.ListField(help_text=_("匹配DB列表"), child=DBTableField(db_field=True))
        ignore_dbs = serializers.ListField(help_text=_("忽略DB列表"), child=DBTableField(db_field=True))
        table_patterns = serializers.ListField(help_text=_("匹配Table列表"), child=DBTableField())
        ignore_tables = serializers.ListField(help_text=_("忽略Table列表"), child=DBTableField())
        cluster_id = serializers.IntegerField(help_text=_("集群ID"))

    runtime_hour = serializers.IntegerField(help_text=_("超时时间"))
    timing = serializers.CharField(help_text=_("定时触发时间"))
    infos = serializers.ListField(help_text=_("数据校验信息列表"), child=ChecksumDataInfoSerializer())
    data_repair = serializers.DictField(help_text=_("数据修复信息"))
    is_sync_non_innodb = serializers.BooleanField(help_text=_("非innodb表是否修复"), required=False, default=False)

    def validate(self, attrs):
        """验证库表数据库的数据"""
        super().validate(attrs)

        # 库表选择器校验
        super().validate_database_table_selector(attrs)

        # 校验slave角色是否一致
        super().validate_instance_role(attrs, instance_key=["slaves"], role=InstanceInnerRole.SLAVE)

        # 校验slave的关联集群是否一致
        super().validate_instance_related_clusters(
            attrs, instance_key=["slaves"], cluster_key=["cluster_id"], role=InstanceInnerRole.SLAVE
        )

        # 校验定时时间不能早于当前时间
        if str2datetime(attrs["timing"]) < datetime.now():
            raise serializers.ValidationError(_("定时时间必须晚于当前时间"))

        return attrs


class MySQLChecksumFlowParamBuilder(builders.FlowParamBuilder):
    """MySQL 数据校验执行单据参数"""

    controller = MySQLController.mysql_checksum

    def format_ticket_data(self):
        pass

    def skip_data_repair(self, data_repair_name, pause_name):
        """是否跳过数据修复"""
        # 如果flow的状态不为成功，则不更新
        if self.ticket.current_flow().status != TicketFlowStatus.SUCCEEDED:
            return True

        # 如果校验结果一致则跳过人工确认和数据修复
        if set(self.ticket_data["is_consistent_list"].values()) == {True}:
            skip_filters = Q(
                ticket=self.ticket,
                details__controller_info__func_name=data_repair_name,
            )
            if self.ticket_data["data_repair"]["mode"] == MySQLChecksumTicketMode.MANUAL:
                skip_filters |= Q(ticket=self.ticket, details__pause_type=pause_name)

            Flow.objects.filter(skip_filters).update(status=TicketFlowStatus.SKIPPED)
            return True

        return False

    def make_repair_data(self, data_repair_name):
        """构造数据修复的数据"""
        # 更新每个实例的数据校验结果
        table_sync_flow = Flow.objects.get(ticket=self.ticket, details__controller_info__func_name=data_repair_name)
        address__inst_map = {}
        for info in table_sync_flow.details["ticket_data"]["infos"]:
            address__inst_map.update({f"{slave['ip']}:{slave['port']}": slave for slave in info["slaves"]})

        for address, is_consistent in self.ticket_data["is_consistent_list"].items():
            address__inst_map[address].update(is_consistent=is_consistent)

        # 更新校验表和触发类型 TODO: 考虑用serializer序列化数据
        table_sync_flow.details["ticket_data"].update(
            checksum_table=self.ticket_data["checksum_table"], trigger_type=MySQLDataRepairTriggerMode.MANUAL.value
        )
        table_sync_flow.save(update_fields=["details"])

    def post_callback(self):
        """根据数据校验的结果，填充上下文信息给数据修复"""
        if self.skip_data_repair(MySQLController.mysql_pt_table_sync_scene.__name__, TicketType.MYSQL_CHECKSUM):
            return

        self.make_repair_data(MySQLController.mysql_pt_table_sync_scene.__name__)


class MySQLChecksumPauseParamBuilder(builders.PauseParamBuilder):
    """MySQL 数据修复人工确认执行的单据参数"""

    def format(self):
        self.params["pause_type"] = TicketType.MYSQL_CHECKSUM


class MySQLDataRepairFlowParamBuilder(builders.FlowParamBuilder):
    """MySQL 数据修复执行的单据参数"""

    controller = MySQLController.mysql_pt_table_sync_scene

    def format_ticket_data(self):
        # 修改单据类型
        self.ticket_data["ticket_type"] = TicketType.MYSQL_DATA_REPAIR


@builders.BuilderFactory.register(TicketType.MYSQL_CHECKSUM)
class MySQLChecksumFlowBuilder(BaseMySQLTicketFlowBuilder):
    serializer = MySQLChecksumDetailSerializer
    # 流程构造类
    checksum_flow_builder = MySQLChecksumFlowParamBuilder
    pause_flow_builder = MySQLChecksumPauseParamBuilder
    data_repair_flow_builder = MySQLDataRepairFlowParamBuilder

    def patch_ticket_detail(self):
        super().patch_ticket_detail()

        cluster_ids = [info["cluster_id"] for info in self.ticket.details["infos"]]
        masters = StorageInstance.objects.select_related("machine").filter(
            cluster__id__in=cluster_ids, instance_inner_role=InstanceInnerRole.MASTER
        )
        cluster_id__master_map = {
            master.cluster.first().id: {
                "id": master.id,
                "instance_inner_role": master.instance_inner_role,
                **DBInstance.from_inst_obj(master).as_dict(),
            }
            for master in masters
        }
        for info in self.ticket.details["infos"]:
            # 填充master信息
            info["master"] = cluster_id__master_map[info["cluster_id"]]
            # 补充slave信息
            slave_insts = StorageInstance.find_insts_by_addresses(info["slaves"])
            ip_port__slave_info = {f"{slave['ip']}:{slave['port']}": slave for slave in info.pop("slaves")}
            info["slaves"] = [
                {
                    "id": slave.id,
                    "instance_inner_role": slave.instance_inner_role,
                    **ip_port__slave_info[slave.ip_port],
                }
                for slave in slave_insts
            ]

        self.ticket.save(update_fields=["details"])

    def custom_ticket_flows(self):
        flows = [
            Flow(
                ticket=self.ticket,
                flow_type=FlowType.INNER_FLOW.value,
                details=self.checksum_flow_builder(self.ticket).get_params(),
                flow_alias=_("数据校验执行"),
                retry_type=FlowRetryType.MANUAL_RETRY.value,
            ),
        ]

        if self.ticket.details["data_repair"]["is_repair"]:
            if self.ticket.details["data_repair"]["mode"] == MySQLChecksumTicketMode.MANUAL:
                flows.append(
                    Flow(
                        ticket=self.ticket,
                        flow_type=FlowType.PAUSE.value,
                        details=self.pause_flow_builder(self.ticket).get_params(),
                        flow_alias=_("人工确认"),
                    ),
                )

            if self.ticket.details["data_repair"]["mode"] == MySQLChecksumTicketMode.MANUAL:
                is_auto_describe, retry_type = _("手动"), FlowRetryType.MANUAL_RETRY.value
            else:
                is_auto_describe, retry_type = _("自动"), FlowRetryType.AUTO_RETRY.value

            flows.append(
                Flow(
                    ticket=self.ticket,
                    flow_type=FlowType.INNER_FLOW.value,
                    retry_type=retry_type,
                    details=self.data_repair_flow_builder(self.ticket).get_params(),
                    flow_alias=_("数据修复{}执行").format(is_auto_describe),
                ),
            )

        return flows

    @classmethod
    def describe_ticket_flows(cls, flow_config_map):
        flow_desc = cls._add_itsm_pause_describe(flow_desc=[], flow_config_map=flow_config_map)
        flow_desc.extend([_("数据校验执行"), _("人工确认"), _("数据修复执行")])
        return flow_desc
