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
import logging

from django.utils.translation import ugettext_lazy as _
from rest_framework import serializers

from backend.db_meta.enums.instance_role import InstanceRole
from backend.db_services.dbbase.constants import IpSource
from backend.flow.engine.controller.hdfs import HdfsController
from backend.ticket import builders
from backend.ticket.builders.common.bigdata import (
    BaseHdfsTicketFlowBuilder,
    BigDataReplaceDetailSerializer,
    BigDataReplaceResourceParamBuilder,
)
from backend.ticket.constants import TicketType

logger = logging.getLogger("root")


class HdfsReplaceDetailSerializer(BigDataReplaceDetailSerializer):
    def validate(self, attrs):
        super().validate(attrs)
        # 目前只支持对datanode角色进行替换
        replace_role_set = set(attrs["old_nodes"].keys())
        invalid_role_list = [InstanceRole.HDFS_ZOOKEEPER, InstanceRole.HDFS_NAME_NODE, InstanceRole.HDFS_JOURNAL_NODE]
        if set(invalid_role_list) & replace_role_set:
            raise serializers.ValidationError(_("hdfs替换只支持datanode角色"))

        return attrs


class HdfsReplaceFlowParamBuilder(builders.FlowParamBuilder):
    controller = HdfsController.hdfs_replace_scene

    def format_ticket_data(self):
        super().format_ticket_data()


class HdfsResourceParamBuilder(BigDataReplaceResourceParamBuilder):
    pass


@builders.BuilderFactory.register(TicketType.HDFS_REPLACE)
class HdfsReplaceFlowBuilder(BaseHdfsTicketFlowBuilder):
    serializer = HdfsReplaceDetailSerializer
    inner_flow_builder = HdfsReplaceFlowParamBuilder
    inner_flow_name = _("HDFS 集群替换")
    resource_apply_builder = HdfsResourceParamBuilder
