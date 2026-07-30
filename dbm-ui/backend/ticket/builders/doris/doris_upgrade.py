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

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from backend.flow.engine.controller.doris import DorisController
from backend.iam_app.dataclass.actions import ActionEnum
from backend.ticket import builders
from backend.ticket.builders.common.base import ParamValidateSerializerMixin
from backend.ticket.builders.common.bigdata import BaseDorisTicketFlowBuilder, BigDataSingleClusterOpsDetailsSerializer
from backend.ticket.constants import TicketType

logger = logging.getLogger("root")


class DorisUpgradeDetailSerializer(ParamValidateSerializerMixin, BigDataSingleClusterOpsDetailsSerializer):
    new_version = serializers.CharField(help_text=_("目标升级版本号，格式 x.y.z"))
    remark = serializers.CharField(help_text=_("备注"), required=False, allow_blank=True, default="")

    def validate(self, attrs):
        # 先走父类（BigDataDetailsSerializer -> TicketBaseValidateSerializerMixin）的通用校验
        attrs = super().validate(attrs)
        # 再触发 ParamValidateSerializerMixin 的反射校验链路：
        # 会读取当前 ticket_type 对应 builder 上的 validator 属性并执行
        attrs = self.validated_params(attrs=attrs)
        return attrs


class DorisUpgradeFlowParamBuilder(builders.FlowParamBuilder):
    controller = DorisController.doris_upgrade_scene


@builders.BuilderFactory.register(TicketType.DORIS_UPGRADE, iam=ActionEnum.DORIS_MANAGE)
class DorisUpgradeFlowBuilder(BaseDorisTicketFlowBuilder):
    serializer = DorisUpgradeDetailSerializer
    inner_flow_builder = DorisUpgradeFlowParamBuilder
    inner_flow_name = _("Doris集群升级")
    # 接入 ParamValidateSerializerMixin 的反射校验链路：
    # ParamValidateSerializerMixin.validated_params 会读取 builder 类的 validator 属性并实例化，
    # 而 DorisController.doris_upgrade_scene 上的 @validates_with(DorisUpgradeValidator)
    # 已经把 DorisUpgradeValidator 挂在了方法对象的 .validator 属性上，这里直接转引。
    validator = DorisController.doris_upgrade_scene.validator
