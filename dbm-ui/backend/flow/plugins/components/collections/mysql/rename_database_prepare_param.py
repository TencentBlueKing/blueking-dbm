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
from django.utils.translation import ugettext as _
from pipeline.component_framework.component import Component

from backend.flow.plugins.components.collections.common.base_service import BaseService


class RenameDatabasePrepareParamService(BaseService):
    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        trans_data = data.get_one_of_inputs("trans_data")
        global_data = data.get_one_of_inputs("global_data")

        old_new_map = {}
        for job in global_data["jobs"]:
            old_new_map[job["from_database"]] = job["to_database"]

        self.log_info(_("[{}] 构造 old_new_map 完成: {}").format(kwargs["node_name"], old_new_map))
        trans_data.old_new_map = old_new_map
        data.outputs["trans_data"] = trans_data
        return True


class RenameDatabasePrepareParamComponent(Component):
    name = __name__
    code = "rename_database_prepare_param"
    bound_service = RenameDatabasePrepareParamService
