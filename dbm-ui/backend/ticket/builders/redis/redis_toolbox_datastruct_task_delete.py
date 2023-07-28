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

from backend.flow.engine.controller.redis import RedisController
from backend.ticket import builders
from backend.ticket.builders.redis.base import BaseRedisTicketFlowBuilder
from backend.ticket.constants import SwitchConfirmType, TicketType


class RedisDataStructureTaskDeleteDetailSerializer(serializers.Serializer):
    """数据构造与实例销毁"""

    class InfoSerializer(serializers.Serializer):
        cluster_id = serializers.IntegerField(help_text=_("集群ID"))
        related_rollback_bill_id = serializers.CharField(help_text=_("关联单据ID"))
        prod_cluster = serializers.CharField(help_text=_("集群域名"))
        bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"))

    infos = serializers.ListField(help_text=_("批量操作参数列表"), child=InfoSerializer())


class RedisDataStructureTaskDeleteParamBuilder(builders.FlowParamBuilder):
    controller = RedisController.redis_data_structure_task_delete


@builders.BuilderFactory.register(TicketType.REDIS_DATA_STRUCTURE_TASK_DELETE)
class RedisDataStructureTaskDeleteFlowBuilder(BaseRedisTicketFlowBuilder):
    serializer = RedisDataStructureTaskDeleteDetailSerializer
    inner_flow_builder = RedisDataStructureTaskDeleteParamBuilder
    inner_flow_name = _("Redis 销毁构造实例")

    @property
    def need_itsm(self):
        return False
