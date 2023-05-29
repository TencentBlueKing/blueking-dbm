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

from backend.flow.consts import ROLLBACK_DB_TAIL, STAGE_DB_HEADER, SYSTEM_DBS
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.mysql.db_table_filter import DbTableFilter


class DatabaseTableFilterRegexBuilderService(BaseService):
    """
    需要在 context 中增加
    db_table_filter_regex: str = None
    db_filter_regex: str = None

    会往 trans_data 中写入
    db_table_filter_regex: str
    db_filter_regex: str
    """

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        trans_data = data.get_one_of_inputs("trans_data")
        global_data = data.get_one_of_inputs("global_data")

        db_table_filter = DbTableFilter(
            include_db_patterns=global_data["db_patterns"],
            include_table_patterns=global_data["table_patterns"],
            exclude_db_patterns=global_data["ignore_dbs"],
            exclude_table_patterns=global_data["ignore_tables"],
        )
        db_table_filter.inject_system_dbs(SYSTEM_DBS + ["{}%".format(STAGE_DB_HEADER), "%{}".format(ROLLBACK_DB_TAIL)])
        trans_data.db_table_filter_regex = db_table_filter.table_filter_regexp()
        trans_data.db_filter_regex = db_table_filter.db_filter_regexp()

        self.log_info(
            _("[{}] 成功: db_table_filter_regex: {}, db_filter_regex: {}").format(
                kwargs["node_name"], trans_data.db_table_filter_regex, trans_data.db_filter_regex
            )
        )

        data.outputs["trans_data"] = trans_data
        return True


class DatabaseTableFilterRegexBuilderComponent(Component):
    name = __name__
    code = "database_table_filter_regex_builder"
    bound_service = DatabaseTableFilterRegexBuilderService
