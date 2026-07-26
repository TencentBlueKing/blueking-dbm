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
from typing import List

from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import Service

from backend.db_meta.api.cluster.mongocluster.reduce_shard import cluster_reduce_shard
from backend.flow.plugins.components.collections.common.base_service import BaseService

logger = logging.getLogger("json")


class ExecReduceShardMetaOperation(BaseService):
    """
    cluster 减少分片清理 meta
    """

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        try:
            cluster_reduce_shard(
                bk_biz_id=kwargs["bk_biz_id"],
                cluster_id=kwargs["cluster_id"],
                storages=kwargs["storages"],
                creator=kwargs.get("creator", ""),
                bk_cloud_id=kwargs["bk_cloud_id"],
            )
        except Exception as e:
            self.log_error("cluster reduce shard meta fail, error:{}".format(str(e)))
            return False
        self.log_info("cluster reduce shard meta successfully")
        return True

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]


class ExecReduceShardMetaOperationComponent(Component):
    name = __name__
    code = "cluster_reduce_shard_to_meta_operation"
    bound_service = ExecReduceShardMetaOperation
