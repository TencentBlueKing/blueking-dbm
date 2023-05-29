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
from pipeline.component_framework.component import Component

from backend.flow.plugins.components.collections.common.base_service import BaseService


class TruncateDatabaseOldNewMapAdapterService(BaseService):
    def _execute(self, data, parent_data):
        kwargs = data.get_one_of_inputs("kwargs")
        trans_data = data.get_one_of_inputs("trans_data")
        global_data = data.get_one_of_inputs("global_data")

        shard_id = global_data["shard_id"]

        self.log_info("[{}] #################### global_data: {}".format(kwargs["node_name"], global_data))

        # 这是在中控生成的, 不带 shard_id
        # 只要给 old_new_map 中的新, 老库都拼个 shard_id 就可以了
        cluster_old_new_map = trans_data.old_new_map
        self.log_info("[{}] cluster old_new_map: {}".format(kwargs["node_name"], cluster_old_new_map))

        remote_old_new_map = {}
        for k, v in cluster_old_new_map.items():
            remote_old_new_map["{}_{}".format(k, shard_id)] = "{}_{}".format(v, shard_id)

        self.log_info("[{}] remote old_new_map: {}".format(kwargs["node_name"], remote_old_new_map))

        trans_data.old_new_map = remote_old_new_map
        data.outputs["trans_data"] = trans_data
        return True


class TruncateDatabaseOldNewMapAdapterComponent(Component):
    name = __name__
    code = "truncate_database_old_new_map_adapter"
    bound_service = TruncateDatabaseOldNewMapAdapterService
