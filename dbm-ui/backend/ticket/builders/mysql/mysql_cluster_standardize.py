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

from backend.configuration.constants import DBType
from backend.flow.engine.controller.mysql import MySQLController
from backend.ticket import builders
from backend.ticket.builders import TicketFlowBuilder
from backend.ticket.builders.mysql.base import MySQLBaseOperateDetailSerializer
from backend.ticket.constants import FlowRetryType, TicketType


class MySQLClusterStandardizeDetailSerializer(MySQLBaseOperateDetailSerializer):
    """
    单据参数对比 flow 参数做了简化
    with_deploy_binary: [with_deploy_binary, with_bk_plugin, with_backup_client]
    with_push_config: [with_push_config, with_exporter_config]
    """

    bk_biz_id = serializers.IntegerField(help_text=_("业务ID"))
    cluster_ids = serializers.ListField(help_text=_("集群ID列表"), child=serializers.IntegerField(help_text=_("集群ID")))
    with_deploy_binary = serializers.BooleanField(help_text=_("是否推送二进制"), default=True)
    with_push_config = serializers.BooleanField(help_text=_("是否推送配置"), default=True)
    with_cc_standardize = serializers.BooleanField(help_text=_("是否CC模块标准"), default=False)
    with_instance_standardize = serializers.BooleanField(help_text=_("是否实例标准化. 高危"), default=False)


class MySQLClusterStandardizeFlowParamBuilder(builders.FlowParamBuilder):
    controller = MySQLController.cluster_standardize


@builders.BuilderFactory.register(TicketType.MYSQL_CLUSTER_STANDARDIZE)
class MySQLClusterStandardizeFlowBuilder(TicketFlowBuilder):
    default_need_itsm = False
    default_need_manual_confirm = True
    serializer = MySQLClusterStandardizeDetailSerializer
    inner_flow_builder = MySQLClusterStandardizeFlowParamBuilder
    inner_flow_name = _("MySQL集群标准化")
    retry_type = FlowRetryType.MANUAL_RETRY
    group = DBType.MySQL
