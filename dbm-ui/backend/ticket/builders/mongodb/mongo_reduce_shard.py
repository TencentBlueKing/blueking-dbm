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
from backend.flow.engine.controller.mongodb import MongoDBController
from backend.iam_app.dataclass.actions import ActionEnum
from backend.ticket import builders
from backend.ticket.builders.mongodb.base import BaseMongoDBOperateDetailSerializer, BaseMongoShardedTicketFlowBuilder
from backend.ticket.constants import TicketType

REDUCE_MODE_BY_SHARD_NAMES = "by_shard_names"
REDUCE_MODE_BY_COUNT = "by_count"


class MongoDBReduceShardDetailSerializer(BaseMongoDBOperateDetailSerializer):
    class ReduceShardDetailSerializer(serializers.Serializer):
        cluster_id = serializers.IntegerField(help_text=_("集群ID"), min_value=1)
        reduce_mode = serializers.ChoiceField(
            help_text=_("缩容模式"),
            choices=[
                (REDUCE_MODE_BY_SHARD_NAMES, _("指定分片")),
                (REDUCE_MODE_BY_COUNT, _("指定数量")),
            ],
            required=False,
            default=REDUCE_MODE_BY_SHARD_NAMES,
        )
        shard_names = serializers.ListField(
            help_text=_("待缩容分片列表"),
            child=serializers.CharField(allow_blank=False),
            required=False,
            allow_empty=True,
        )
        reduce_shards_num = serializers.IntegerField(help_text=_("缩容分片数"), min_value=1, required=False)

        def validate(self, attrs):
            reduce_mode = attrs.get("reduce_mode") or REDUCE_MODE_BY_SHARD_NAMES
            attrs["reduce_mode"] = reduce_mode
            if reduce_mode == REDUCE_MODE_BY_SHARD_NAMES:
                shard_names = attrs.get("shard_names") or []
                if not shard_names:
                    raise serializers.ValidationError(_("指定分片模式下 shard_names 不能为空"))
                attrs["shard_names"] = shard_names
                attrs.pop("reduce_shards_num", None)
            else:
                if not attrs.get("reduce_shards_num"):
                    raise serializers.ValidationError(_("指定数量模式下 reduce_shards_num 不能为空"))
                attrs.pop("shard_names", None)
            return attrs

    bk_cloud_id = serializers.IntegerField(help_text=_("云区域ID"), required=False)
    infos = serializers.ListSerializer(help_text=_("缩容分片信息"), child=ReduceShardDetailSerializer())


class MongoDBReduceShardFlowParamBuilder(builders.FlowParamBuilder):
    controller = MongoDBController.cluster_reduce_shard

    def format_ticket_data(self):
        bk_biz_id = self.ticket_data["bk_biz_id"]
        self.ticket_data["bk_app_abbr"] = AppCache.objects.get(bk_biz_id=bk_biz_id).db_app_abbr


@builders.BuilderFactory.register(TicketType.MONGODB_REDUCE_SHARD, is_recycle=True, iam=ActionEnum.MONGODB_MANAGE)
class MongoDBReduceShardFlowBuilder(BaseMongoShardedTicketFlowBuilder):
    serializer = MongoDBReduceShardDetailSerializer
    inner_flow_builder = MongoDBReduceShardFlowParamBuilder
    inner_flow_name = _("MongoDB 缩容分片数")
