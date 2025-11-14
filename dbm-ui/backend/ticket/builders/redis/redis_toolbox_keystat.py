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
from typing import List

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from backend.db_meta.enums import ClusterType
from backend.db_services.redis.hot_key_analysis.models import RedisHotKeyRecord
from backend.db_services.redis.redis_keystat_report.models import ReportRecord
from backend.flow.consts import StateType
from backend.flow.engine.bamboo.scene.redis.validate.redis_keystat_validator import RedisKeyStatFlowValidator
from backend.flow.engine.controller.redis import RedisController
from backend.ticket import builders
from backend.ticket.builders.common.base import DisplayInfoSerializer
from backend.ticket.builders.redis.base import (
    ClusterValidateMixin,
    RedisALLInstanceTicketFlowBuilder,
    RedisBaseOperateDetailSerializer,
)
from backend.ticket.constants import TicketFlowStatus, TicketType


class RedisKeyStatSerializer(RedisBaseOperateDetailSerializer):
    """内存分析参数序列化器"""

    class InfoSerializer(DisplayInfoSerializer, ClusterValidateMixin, serializers.Serializer):
        class InstanceSerializer(serializers.Serializer):
            addr = serializers.CharField(help_text=_("实例地址"))
            # display fields
            key_num = serializers.IntegerField(help_text=_("key数量"), required=False)
            memory_total = serializers.IntegerField(help_text=_("内存大小"), required=False)

        cluster_id = serializers.IntegerField(help_text=_("集群ID"))
        check_last_visit = serializers.BooleanField(help_text=_("是否上次访问"), required=False, default=True)
        ins = serializers.ListField(help_text=_("实例列表"), child=InstanceSerializer())
        immute_domain = serializers.CharField(help_text=_("域名"))
        delimiter = serializers.CharField(help_text=_("域名"), required=False, default="#@_-")
        cluster_type = serializers.ChoiceField(help_text=_("集群类型"), choices=ClusterType.get_choices())

    bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"))
    analysis_time = serializers.IntegerField(help_text=_("分析时长"), required=False, default=0)
    infos = serializers.ListField(help_text=_("批量操作参数列表"), child=InfoSerializer())


class RedisKeyStatParamBuilder(builders.FlowParamBuilder):
    controller = RedisController.redis_keystat
    validator = RedisKeyStatFlowValidator

    def post_callback(self):
        flow = self.ticket.current_flow()
        # 更新记录表状态
        record_ids = [info["record_id"] for info in self.ticket_data["infos"]]
        if flow.status == TicketFlowStatus.SUCCEEDED.value:
            RedisHotKeyRecord.objects.filter(id__in=record_ids, status=StateType.RUNNING).update(
                status=StateType.FINISHED
            )
        else:
            RedisHotKeyRecord.objects.filter(id__in=record_ids, status=StateType.RUNNING).update(status=flow.status)


@builders.BuilderFactory.register(TicketType.REDIS_KEYSTAT)
class RedisKeyStatFlowBuilder(RedisALLInstanceTicketFlowBuilder):
    serializer = RedisKeyStatSerializer
    inner_flow_builder = RedisKeyStatParamBuilder
    inner_flow_name = _("Redis 内存分析")

    def create_keystat_infos(self):
        # 创建热key记录
        record_infos: List[RedisHotKeyRecord] = []
        for index, info in enumerate(self.ticket.details["infos"]):
            record_info = ReportRecord(
                bk_biz_id=self.ticket.bk_biz_id,
                source_addr_list=info["ins"],
                cluster_id=info["cluster_id"],
                cluster_type=info["cluster_type"],
                immute_domain=info["immute_domain"],
                analysis_time=self.ticket.details["analysis_time"],
                ticket_id=self.ticket.id,
                status=StateType.READY,
                creator=self.ticket.creator,
            )
            record_infos.append(record_info)

        ReportRecord.objects.bulk_create(record_infos)
        record_infos = ReportRecord.objects.filter(ticket_id=self.ticket.id)

        record_info_map = defaultdict(dict)
        for record_info in record_infos:
            record_info_map[record_info.ticket_id][record_info.cluster_id] = record_info.record_id

        for info in self.ticket.details["infos"]:
            info["record_id"] = record_info_map[self.ticket.id][info["cluster_id"]]

    def patch_ticket_detail(self):
        self.create_keystat_infos()
        super().patch_ticket_detail()
