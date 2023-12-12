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
from datetime import datetime

from django.utils.translation import ugettext as _
from pipeline.component_framework.component import Component

from backend.flow.consts import STAGE_DB_HEADER
from backend.flow.plugins.components.collections.common.base_service import BaseService


class TruncateDataGenerateStageDatabaseNameService(BaseService):
    def _execute(self, data, parent_data) -> bool:
        trans_data = data.get_one_of_inputs("trans_data")

        targets = trans_data.targets

        old_new_map = {}
        for db in targets:
            stage_db_name = self.generate_truncate_dbname(db)
            old_new_map[db] = stage_db_name

        self.log_info(_("生成备份库名完成"))
        trans_data.old_new_map = old_new_map
        data.outputs["trans_data"] = trans_data
        return True

    @staticmethod
    def generate_truncate_dbname(db: str) -> str:
        # TODO: 改为带时区的时间字符串是否影响？
        return "{}_{}_{}".format(STAGE_DB_HEADER, datetime.now().strftime("%Y%m%d%H%M%S"), db)


class TruncateDataGenerateStageDatabaseNameComponent(Component):
    name = __name__
    code = "truncate_data_generate_stage_database_name"
    bound_service = TruncateDataGenerateStageDatabaseNameService
