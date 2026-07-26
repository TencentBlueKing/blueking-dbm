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

from rest_framework import serializers

from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.engine.bamboo.scene.mongodb.sub_task.cluster_reduce_shard import cluster_reduce_shard
from backend.flow.utils.mongodb.calculate_cluster import calculate_cluster_reduce_shard
from backend.flow.utils.mongodb.mongodb_dataclass import ActKwargs

logger = logging.getLogger("flow")


class MongoDBClusterReduceShardFlow(object):
    """MongoDB 分片集群减少 shard flow"""

    class Serializer(serializers.Serializer):
        class InfoRow(serializers.Serializer):
            cluster_id = serializers.IntegerField(min_value=1)
            shard_names = serializers.ListField(child=serializers.CharField(allow_blank=False), allow_empty=False)
            bk_cloud_id = serializers.IntegerField(required=False)

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
                raise serializers.ValidationError("uid can not be empty")
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
