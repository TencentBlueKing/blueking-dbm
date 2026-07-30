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

from backend.db_meta.models import AppCache
from backend.flow.engine.controller.mysql import MySQLController
from backend.iam_app.dataclass.actions import ActionEnum
from backend.ticket import builders
from backend.ticket.builders.mysql.base import BaseMySQLTicketFlowBuilder, MySQLBaseOperateDetailSerializer
from backend.ticket.constants import TicketType


class InitPartitionSerializer(serializers.Serializer):
    sql = serializers.CharField(help_text=_("初始化分区语句"))
    need_size = serializers.IntegerField(help_text=_("所需空间Byte"))
    has_unique_key = serializers.BooleanField(help_text=_("表是否包含唯一键或者主键"))


class ExecuteConfObjectSerializer(serializers.Serializer):
    config_id = serializers.IntegerField(help_text=_("配置ID"))
    dblike = serializers.CharField(help_text=_("库名匹配规则"))
    tblike = serializers.CharField(help_text=_("表明匹配规则"))
    init_partition = serializers.ListField(help_text=_("初始化分区表"), child=InitPartitionSerializer())
    add_partition = serializers.ListField(help_text=_("添加分区"), child=serializers.CharField())
    drop_partition = serializers.ListField(help_text=_("删除分区"), child=serializers.CharField())


class PartitionObjectSerializer(serializers.Serializer):
    ip = serializers.CharField(help_text=_("ip"))
    port = serializers.IntegerField(help_text=_("port"))
    shard_name = serializers.CharField(help_text=_("分片名"))
    execute_objects = serializers.ListField(help_text=_("执行对象列表"), child=ExecuteConfObjectSerializer())


class PartitionConfigObjectSerializer(serializers.Serializer):
    config_id = serializers.IntegerField(help_text=_("配置ID"))
    dblike = serializers.CharField(help_text=_("匹配库列表（支持通配）"))
    tblike = serializers.CharField(help_text=_("匹配表列表（不支持通配）"))
    partition_column = serializers.CharField(help_text=_("分区字段"))
    partition_column_type = serializers.CharField(help_text=_("分区字段类型"))
    expire_time = serializers.IntegerField(help_text=_("过期时间"))
    partition_time_interval = serializers.IntegerField(help_text=_("分区间隔"))
    extra_partition = serializers.IntegerField(help_text=_("预留分区数"))
    partition_type = serializers.IntegerField(help_text=_("分区类型"))
    time_zone = serializers.CharField(help_text=_("时区"))
    phase = serializers.CharField(help_text=_("是否禁用分区"))


class PartitionV2ConfObjectSerializer(serializers.Serializer):
    cluster_id = serializers.IntegerField(help_text=_("集群id"))
    config = serializers.ListSerializer(help_text=_("配置列表"), child=PartitionConfigObjectSerializer())
    force = serializers.BooleanField(help_text=_("否表示是否强制执行,True 表示重新初始化"), default=False)


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
        app = AppCache.objects.get(bk_biz_id=self.ticket_data["bk_biz_id"])
        self.ticket_data.update(bk_biz_name=app.bk_biz_name, db_app_abbr=app.db_app_abbr)


@builders.BuilderFactory.register(TicketType.MYSQL_PARTITION, iam=ActionEnum.MYSQL_PARTITION_MANAGE)
class MysqlPartitionFlowBuilder(BaseMySQLTicketFlowBuilder):
    serializer = MySQLPartitionDetailSerializer
    inner_flow_builder = MySQLPartitionParamBuilder
    inner_flow_name = _("分区管理执行")
    default_need_itsm = False
    default_need_manual_confirm = False
