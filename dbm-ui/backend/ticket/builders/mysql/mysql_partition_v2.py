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
from backend.ticket.builders.mysql.base import (
    BaseMySQLTicketFlowBuilder,
    DBTableField,
    MySQLBaseOperateDetailSerializer,
)
from backend.ticket.constants import TicketType


class PartitionV2ConfObjectSerializer(serializers.Serializer):
    config_id = serializers.IntegerField(help_text=_("配置ID"))
    # dblikes = serializers.ListField(help_text=_("匹配库列表(支持通配)"), child=DBTableField(db_field=True))
    # tblikes = serializers.ListField(help_text=_("匹配表列表(不支持通配)"), child=DBTableField())
    dblike = DBTableField(help_text=_("匹配库列表(支持通配)"), db_field=True)
    tblike = DBTableField(help_text=_("匹配表列表(不支持通配)"))
    partition_column = serializers.CharField(help_text=_("分区字段"))
    partition_column_type = serializers.CharField(help_text=_("分区字段类型"))
    expire_time = serializers.IntegerField(help_text=_("过期时间"))
    partition_time_interval = serializers.IntegerField(help_text=_("分区间隔"))
    extra_partition = serializers.IntegerField(help_text=_("预留分区数"), required=False, default=15)
    partition_type = serializers.IntegerField(help_text=_("分区类型"))
    time_zone = serializers.CharField(help_text=_("时区"), allow_blank=True, allow_null=True)
    phase = serializers.CharField(help_text=_("是否禁用分区"))


class MySQLPartitionV2DetailSerializer(MySQLBaseOperateDetailSerializer):
    """
    分区v2 执行单据详情：
    - 与定时任务下发的数据结构保持一致，核心字段为 cluster_id / configs / force / partial_force
    """

    cluster_id = serializers.IntegerField(help_text=_("集群ID"))
    # configs 的结构由分区服务返回，这里作为通用列表透传给后续执行流程
    configs = serializers.ListField(help_text=_("分区配置列表"), child=PartitionV2ConfObjectSerializer())
    force = serializers.BooleanField(help_text=_("是否强制执行"), required=False, default=False)
    partial_force = serializers.BooleanField(help_text=_("是否部分强制执行"), required=False, default=False)


class MySQLPartitionV2ParamBuilder(builders.FlowParamBuilder):
    # 调用 v2 分区编排
    controller = MySQLController.mysql_partition_scene_v2

    def format_ticket_data(self):
        app = AppCache.objects.get(bk_biz_id=self.ticket_data["bk_biz_id"])
        self.ticket_data.update(bk_biz_name=app.bk_biz_name, db_app_abbr=app.db_app_abbr)


@builders.BuilderFactory.register(TicketType.MYSQL_PARTITION_V2, iam=ActionEnum.MYSQL_PARTITION_MANAGE)
class MysqlPartitionV2FlowBuilder(BaseMySQLTicketFlowBuilder):
    serializer = MySQLPartitionV2DetailSerializer
    inner_flow_builder = MySQLPartitionV2ParamBuilder
    inner_flow_name = _("分区管理执行v2")
    default_need_itsm = False
    default_need_manual_confirm = False
