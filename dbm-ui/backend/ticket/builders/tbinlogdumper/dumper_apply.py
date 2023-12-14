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

from collections import defaultdict
from typing import Dict, List

from django.db.transaction import atomic
from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from backend.db_meta.enums.extra_process_type import ExtraProcessType
from backend.db_meta.models.extra_process import ExtraProcessInstance
from backend.db_services.mysql.dumper.models import DumperSubscribeConfig
from backend.flow.consts import TBinlogDumperAddType
from backend.flow.engine.controller.tbinlogdumper import TBinlogDumperController
from backend.ticket import builders
from backend.ticket.builders.common.constants import DumperProtocolType
from backend.ticket.builders.tendbcluster.base import BaseDumperTicketFlowBuilder, BaseTendbTicketFlowBuilder
from backend.ticket.constants import TicketType


class TbinlogdumperApplyDetailSerializer(serializers.Serializer):
    class DBTableDetailSerializer(serializers.Serializer):
        db_name = serializers.CharField(help_text=_("订阅库名"))
        table_names = serializers.ListField(help_text=_("订阅表名列表"), child=serializers.CharField())

    class ReceiverDetailSerializer(serializers.Serializer):
        cluster_id = serializers.IntegerField(help_text=_("数据库原源群"))
        db_module_id = serializers.IntegerField(help_text=_("集群module id"))
        dumper_id = serializers.IntegerField(help_text=_("部署的dumper id"))
        protocol_type = serializers.ChoiceField(help_text=_("接收端类型"), choices=DumperProtocolType.get_choices())
        target_address = serializers.CharField(help_text=_("接收端集群域名/IP"), required=False)
        target_port = serializers.IntegerField(help_text=_("接收端端口"), required=False)
        # 接收端配置可选项
        l5_modid = serializers.IntegerField(help_text=_("l5_modid配置"), required=False)
        l5_cmdid = serializers.IntegerField(help_text=_("l5_cmdid配置"), required=False)
        kafka_user = serializers.CharField(help_text=_("kafka用户名"), required=False)
        kafka_pwd = serializers.CharField(help_text=_("kafka密码"), required=False)

    name = serializers.CharField(help_text=_("订阅名称"))
    add_type = serializers.ChoiceField(help_text=_("数据同步方式"), choices=TBinlogDumperAddType.get_choices())
    repl_tables = serializers.ListSerializer(help_text=_("订阅库表"), child=DBTableDetailSerializer())
    infos = serializers.ListSerializer(help_text=_("dumper配置信息"), child=ReceiverDetailSerializer())
    dumper_config_id = serializers.IntegerField(help_text=_("dumper配置ID"), required=False)

    def validate_dumpers_unique(self, attrs):
        # 必须保证dumper_id--receive_type--table的库表不能重复，考虑dumper数量很少，就全量查询比较
        dumpers = ExtraProcessInstance.objects.filter(proc_type=ExtraProcessType.TBINLOGDUMPER)
        dumper_instance_map: Dict[int, Dict[str, List]] = defaultdict(lambda: defaultdict(list))
        for dumper in dumpers:
            dumper_id, protocol_type = int(dumper.extra_config["dumper_id"]), dumper.extra_config["protocol_type"]
            dumper_instance_map[dumper_id][protocol_type].extend(dumper.extra_config["repl_tables"])

        for info in attrs["infos"]:
            dumper_id, protocol_type = info["dumper_id"], info["protocol_type"]
            intersect_tables = set(attrs["repl_tables"]).intersection(dumper_instance_map[dumper_id][protocol_type])
            if intersect_tables:
                raise serializers.ValidationError(
                    _("dumper_id:{}--接收端:{} 存在重复的库表部署记录: {}").format(dumper_id, protocol_type, intersect_tables)
                )

    def validate(self, attrs):
        # 校验类型和配置可选项的匹配
        for info in attrs["infos"]:
            if info["protocol_type"] == DumperProtocolType.KAFKA and not (info["kafka_user"] and info["kafka_pwd"]):
                raise serializers.ValidationError(_("接收端协议选择KAFKA时，请填写kafka用户名和密码"))
            if info["protocol_type"] == DumperProtocolType.L5_AGENT and not (info["l5_modid"] and info["l5_cmdid"]):
                raise serializers.ValidationError(_("接收端协议选择L5_AGENT时，请填写l5_modid和l5_cmdid"))

        # 因为一次提单的库表都一样，所以必须保证dumper id--接收端不同
        dumper_id__protocol_tuples = [(info["dumper_id"], info["protocol_type"]) for info in attrs["infos"]]
        if len(set(dumper_id__protocol_tuples)) != len(dumper_id__protocol_tuples):
            raise serializers.ValidationError(_("请保证输入的dumper id与接收端类型不能有重复"))

        with atomic():
            # 尝试创建配置规则
            dumper_config, created = DumperSubscribeConfig.objects.get_or_create(
                bk_biz_id=self.context["bk_biz_id"],
                name=attrs["name"],
                defaults={"add_type": attrs["add_type"], "repl_tables": attrs.pop("repl_tables")},
            )
            attrs["repl_tables"] = dumper_config.get_subscribe_info()
            # 校验dumper是否配置重复
            self.validate_dumpers_unique(attrs)
            attrs["dumper_config_id"] = dumper_config.id

        return attrs

    def to_representation(self, instance):
        return instance


class TbinlogdumperApplyFlowParamBuilder(builders.FlowParamBuilder):
    controller = TBinlogDumperController.add_nodes_scene

    def format_ticket_data(self):
        # 将相同集群的dumper配置聚合到一起
        cluster_id__dumper_config = defaultdict(list)
        for info in self.ticket_data["infos"]:
            info["area_name"] = info["dumper_id"]
            info["repl_tables"] = self.ticket_data["repl_tables"]
            info["add_type"] = self.ticket_data["add_type"]
            cluster_id__dumper_config[info["cluster_id"]].append(info)

        self.ticket_data["infos"] = []
        for cluster_id, add_confs in cluster_id__dumper_config.items():
            protocol_types = [add_conf["protocol_type"] for add_conf in add_confs]
            self.ticket_data["infos"].append(
                {
                    "cluster_id": cluster_id,
                    "add_confs": add_confs,
                    "is_install_l5_agent": DumperProtocolType.L5_AGENT in protocol_types,
                }
            )


@builders.BuilderFactory.register(TicketType.TBINLOGDUMPER_INSTALL)
class TbinlogdumperApplyFlowBuilder(BaseDumperTicketFlowBuilder):
    serializer = TbinlogdumperApplyDetailSerializer
    inner_flow_builder = TbinlogdumperApplyFlowParamBuilder
    inner_flow_name = _("Tbinlogdumper 上架")
