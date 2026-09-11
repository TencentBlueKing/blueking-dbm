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
from django.utils.translation import gettext as _
from rest_framework import serializers

from backend.configuration.constants import DBType
from backend.db_meta.enums import ClusterType
from backend.ticket.builders import TicketFlowBuilder
from backend.ticket.builders.common.base import (
    BaseOperateResourceParamBuilder,
    BaseTicketFlowBuilderPatchMixin,
    ParamValidateSerializerMixin,
    SkipToRepresentationMixin,
    TicketBaseValidateSerializerMixin,
)


class BaseOracleTicketFlowBuilder(BaseTicketFlowBuilderPatchMixin, TicketFlowBuilder):
    group = DBType.Oracle.value
    cluster_types = [ClusterType.OraclePrimaryStandby.value]


class OracleOpsBaseDetailSerializer(
    TicketBaseValidateSerializerMixin, SkipToRepresentationMixin, ParamValidateSerializerMixin, serializers.Serializer
):
    # TODO: rules内部校验
    rules = serializers.JSONField(help_text=_("提取/删除/备份规则列表"))

    def validate(self, attrs):
        """
        公共校验：集群操作互斥校验
        """
        attrs = super().validate(attrs)
        attrs = super().validated_params(attrs=attrs)
        return attrs


class OracleOperateResourceParamBuilder(BaseOperateResourceParamBuilder):
    def format(self):
        super().format()

    def post_callback(self):
        super().post_callback()
