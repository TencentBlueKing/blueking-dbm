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
from backend.tests.mock_data import constant
from backend.ticket.constants import TicketType

BK_BIZ_ID = constant.BK_BIZ_ID

# 定义MySQL语义检查场景的测试参数
MYSQL_SEMANTIC_CHECK_PARAMS = {
    "uid": 12345678,
    "created_by": "admin",
    "bk_biz_id": BK_BIZ_ID,  # 实际使用时会替换为常量值
    "ticket_type": TicketType.MYSQL_SEMANTIC_CHECK,  # 实际使用时会替换为常量值
    "params": {"act": "test_params"},  # 这里可以是任何字符串，表示传递给流程的数据
}

# 定义MySQL授权规则场景的测试参数
MYSQL_AUTHORIZE_RULES_PARAMS = {
    "uid": 12345678,
    "created_by": "admin",
    "bk_biz_id": BK_BIZ_ID,  # 实际使用时会替换为常量值
    "ticket_type": TicketType.MYSQL_AUTHORIZE_RULES,  # 实际使用时会替换为常量值
    "rules_set": [
        {
            "user": "admin",
            "access_dbs": ["dbnew", "user"],
            "source_ips": [{"ip": "1.1.1.1", "bk_host_id": 1}, {"ip": "2.2.2.2", "bk_host_id": 2}],
            "target_instances": ["gamedb.privtest55.blueking.db"],
            "cluster_type": "tendbha",
        },
    ],
}
