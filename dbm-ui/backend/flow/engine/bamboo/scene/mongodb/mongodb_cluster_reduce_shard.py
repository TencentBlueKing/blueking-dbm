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
import logging.config
from typing import Dict, Optional

from django.utils.translation import gettext as _
from rest_framework import serializers

from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.engine.bamboo.scene.mongodb.sub_task.cluster_reduce_shard import cluster_reduce_shard
from backend.flow.utils.mongodb.calculate_cluster import calculate_cluster_reduce_shard
from backend.flow.utils.mongodb.mongodb_dataclass import ActKwargs

logger = logging.getLogger("flow")

REDUCE_SHARD_MODE_BY_SHARD_NAMES = "by_shard_names"
REDUCE_SHARD_MODE_BY_COUNT = "by_count"


class MongoDBClusterReduceShardFlow(object):
    """MongoDB 分片集群减少 shard flow"""

    REDUCE_MODE_BY_SHARD_NAMES = REDUCE_SHARD_MODE_BY_SHARD_NAMES
    REDUCE_MODE_BY_COUNT = REDUCE_SHARD_MODE_BY_COUNT

    class Serializer(serializers.Serializer):
        class InfoRow(serializers.Serializer):
            cluster_id = serializers.IntegerField(min_value=1)
            reduce_mode = serializers.ChoiceField(
                choices=[
                    (REDUCE_SHARD_MODE_BY_SHARD_NAMES, REDUCE_SHARD_MODE_BY_SHARD_NAMES),
                    (REDUCE_SHARD_MODE_BY_COUNT, REDUCE_SHARD_MODE_BY_COUNT),
                ],
                required=False,
                default=REDUCE_SHARD_MODE_BY_SHARD_NAMES,
            )
            shard_names = serializers.ListField(
                child=serializers.CharField(allow_blank=False), required=False, allow_empty=True
            )
            reduce_shards_num = serializers.IntegerField(min_value=1, required=False)
            bk_cloud_id = serializers.IntegerField(required=False)

            def validate(self, attrs):
                mode = attrs.get("reduce_mode") or REDUCE_SHARD_MODE_BY_SHARD_NAMES
                attrs["reduce_mode"] = mode
                if mode == REDUCE_SHARD_MODE_BY_SHARD_NAMES:
                    shard_names = attrs.get("shard_names") or []
                    if not shard_names:
                        raise serializers.ValidationError(_("指定分片模式下 shard_names 不能为空"))
                    attrs["shard_names"] = shard_names
                    attrs.pop("reduce_shards_num", None)
                elif mode == REDUCE_SHARD_MODE_BY_COUNT:
                    if not attrs.get("reduce_shards_num"):
                        raise serializers.ValidationError(_("指定数量模式下 reduce_shards_num 不能为空"))
                    attrs.pop("shard_names", None)
                return attrs

        uid = serializers.CharField(allow_blank=False)
        ticket_id = serializers.CharField(required=False, allow_blank=True)
        bk_biz_id = serializers.IntegerField()
        bk_cloud_id = serializers.IntegerField(required=False)
        ticket_type = serializers.CharField(required=False)
        created_by = serializers.CharField()
        bk_app_abbr = serializers.CharField(required=False, allow_blank=True)
        infos = InfoRow(many=True, allow_empty=False)

        def validate_uid(self, value):
            if not str(value).strip():
                raise serializers.ValidationError(_("uid不能为空"))
            return value

    def __init__(self, root_id: str, data: Optional[Dict]):
        self.root_id = root_id
        serializer = self.Serializer(data=data or {})
        serializer.is_valid(raise_exception=True)
        self.data = calculate_cluster_reduce_shard(serializer.validated_data)
        self.get_kwargs = ActKwargs()
        self.get_kwargs.payload = self.data
        self.get_kwargs.get_file_path()

    def multi_cluster_reduce_shard_flow(self):
        """多个 cluster 减少 shard 并行"""

        pipeline = Builder(root_id=self.root_id, data=self.data)

        sub_pipelines = []
        for reduce_shard_info in self.data["cluster_reduce_shard_info"]:
            sub_pipeline = cluster_reduce_shard(
                root_id=self.root_id,
                ticket_data=self.data,
                sub_kwargs=self.get_kwargs,
                reduce_shard_info=reduce_shard_info,
            )
            sub_pipelines.append(sub_pipeline)

        pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        pipeline.run_pipeline()
