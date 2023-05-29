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
import time

from django.core.cache import cache
from django.utils.translation import ugettext as _
from pipeline.component_framework.component import Component

from backend.db_services.mysql.sql_import.constants import (
    CACHE_SEMANTIC_AUTO_COMMIT_FIELD,
    CACHE_SEMANTIC_SKIP_PAUSE_FILED,
)
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.ticket.constants import TicketType


class FakeSemanticCheck(BaseService):
    """模拟语义执行，仅用作测试"""

    def _execute(self, data, parent_data, callback=None) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        global_data = data.get_one_of_inputs("global_data")

        root_id = kwargs.get("root_id")
        bk_biz_id = global_data.get("bk_biz_id")

        # 测试报错
        if kwargs.get("is_error"):
            logging.error("test error....")
            return False

        # 模拟语义执行
        time.sleep(5)

        # 查询是否能自动提交单据，默认为手动提交
        auto_commit_key = CACHE_SEMANTIC_AUTO_COMMIT_FIELD.format(bk_biz_id=bk_biz_id, root_id=root_id)
        skip_pause_key = CACHE_SEMANTIC_SKIP_PAUSE_FILED.format(bk_biz_id=bk_biz_id, root_id=root_id)
        is_auto_commit = cache.get(auto_commit_key) or False
        is_skip_pause = cache.get(skip_pause_key) or False
        self.log_info(
            f"-----------auto_commit_key: {auto_commit_key}-{is_auto_commit}, "
            f"skip_pause_key: {skip_pause_key}-{is_skip_pause}-------------"
        )

        # 构造单据信息
        trans_data = {
            "is_auto_commit": is_auto_commit,
            "ticket_data": {
                "remark": _("这是一个fake的模拟执行"),
                "ticket_type": TicketType.MYSQL_IMPORT_SQLFILE,
                "details": {"root_id": root_id, "skip_pause": is_skip_pause},
            },
        }

        data.outputs["trans_data"] = trans_data
        self.log_info(_("语义检查执行成功"))

        return True


class FakeSemanticCheckComponent(Component):
    name = __name__
    code = "fake_semantic_check"
    bound_service = FakeSemanticCheck
