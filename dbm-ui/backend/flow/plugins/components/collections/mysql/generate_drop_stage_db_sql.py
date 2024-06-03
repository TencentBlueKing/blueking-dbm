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


class GenerateDropStageDBSqlService(BaseService):
    def _execute(self, data, parent_data) -> bool:
        """
        bk_cloud_id 统一由私有变量kwargs传入
        """
        kwargs = data.get_one_of_inputs("kwargs")
        trans_data = data.get_one_of_inputs("trans_data")

        old_new_map = trans_data.old_new_map

        drop_stage_db_cmds = []
        for old_db in old_new_map:
            stage_db = old_new_map[old_db]
            drop_stage_db_cmds.append("drop database if exists `{}`".format(stage_db))

        self.log_info("[{}] drop stage db cmds: {}".format(kwargs["node_name"], drop_stage_db_cmds))
        trans_data.drop_stage_db_cmds = drop_stage_db_cmds
        data.outputs["trans_data"] = trans_data
        return True


class GenerateDropStageDBSqlComponent(Component):
    name = __name__
    code = "generate_drop_stage_db_sql"
    bound_service = GenerateDropStageDBSqlService
