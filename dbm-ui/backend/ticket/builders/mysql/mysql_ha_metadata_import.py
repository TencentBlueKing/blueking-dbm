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

from backend.flow.engine.controller.mysql import MySQLController
from backend.ticket import builders
from backend.ticket.builders.mysql.base import BaseMySQLTicketFlowBuilder, MySQLBaseOperateDetailSerializer
from backend.ticket.constants import FlowRetryType, TicketType


class MySQLHaMetadataImportDetailSerializer(MySQLBaseOperateDetailSerializer):
    file = serializers.FileField(help_text=_("元数据json文件"))
    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))
    db_module_id = serializers.IntegerField(help_text=_("模块ID"))
    proxy_spec_id = serializers.IntegerField(help_text=_("代理层规格ID"))
    storage_spec_id = serializers.IntegerField(help_text=_("存储层规格ID"))

    def validate(self, attrs):
        # 这里需要先做些检查 ToDo
        # 1. db module, proxy spec, storage spec 存在
        # 2. 集群版本和字符集满足 db module 的要求
        # 3. 集群机器配置符合 spec
        super().validate(attrs)
        return attrs


class MySQLHaMetadataImportFlowParamBuilder(builders.FlowParamBuilder):
    """MySQL HA 备份执行单据参数"""

    controller = MySQLController.mysql_ha_metadata_import_scene


@builders.BuilderFactory.register(TicketType.MYSQL_HA_METADATA_IMPORT)
class MySQLHaFullBackupFlowBuilder(BaseMySQLTicketFlowBuilder):
    serializer = MySQLHaMetadataImportDetailSerializer
    inner_flow_builder = MySQLHaMetadataImportFlowParamBuilder
    inner_flow_name = _("MySQL高可用元数据导入")
    retry_type = FlowRetryType.MANUAL_RETRY
