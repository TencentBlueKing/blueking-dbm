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

from backend.flow.engine.controller.mysql import MySQLController
from backend.ticket import builders
from backend.ticket.builders.mysql.base import (
    BaseMySQLTicketFlowBuilder,
    DBTableField,
    MySQLBaseOperateDetailSerializer,
)
from backend.ticket.constants import TicketType


class InitPartitionSerializer(serializers.Serializer):
    sql = serializers.CharField(help_text=_("初始化分区语句"))
    need_size = serializers.IntegerField(help_text=_("所需空间Byte"))


class ExecuteObjectSerializer(serializers.Serializer):
    config_id = serializers.IntegerField(help_text=_("配置ID"))
    dblike = DBTableField(help_text=_("库名匹配规则"), db_field=True)
    tblike = DBTableField(help_text=_("表明匹配规则"))
    init_partition = serializers.ListField(help_text=_("初始化分区表"), child=InitPartitionSerializer())
    add_partition = serializers.ListField(help_text=_("添加分区"), child=serializers.CharField())
    drop_partition = serializers.ListField(help_text=_("删除分区"), child=serializers.CharField())


class PartitionObjectSerializer(serializers.Serializer):
    ip = serializers.CharField(help_text=_("ip"))
    port = serializers.IntegerField(help_text=_("port"))
    shard_name = serializers.CharField(help_text=_("分片名"))
    execute_objects = serializers.ListField(help_text=_("执行对象列表"), child=ExecuteObjectSerializer())


class MySQLPartitionDetailSerializer(MySQLBaseOperateDetailSerializer):
    class PartitionInfoSerializer(serializers.Serializer):
        config_id = serializers.IntegerField(help_text=_("配置ID列表"))
        cluster_id = serializers.IntegerField(help_text=_("集群ID"))
        bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"))
        immute_domain = serializers.CharField(help_text=_("集群域名"))
        partition_objects = serializers.ListField(help_text=_("分区执行对象列表"), child=PartitionObjectSerializer())

    infos = serializers.ListSerializer(help_text=_("分区信息"), child=PartitionInfoSerializer())


class MySQLPartitionParamBuilder(builders.FlowParamBuilder):
    controller = MySQLController.mysql_partition

    def format_ticket_data(self):
        pass


@builders.BuilderFactory.register(TicketType.MYSQL_PARTITION)
class MysqlPartitionFlowBuilder(BaseMySQLTicketFlowBuilder):
    serializer = MySQLPartitionDetailSerializer
    inner_flow_builder = MySQLPartitionParamBuilder
    inner_flow_name = _("分区管理执行")
    default_need_itsm = False
    default_need_manual_confirm = False
