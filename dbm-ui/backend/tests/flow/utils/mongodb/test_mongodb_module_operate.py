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

from unittest.mock import patch

import pytest

from backend.flow.utils.mongodb.mongodb_module_operate import MongoDBCCTopoOperator


@pytest.mark.parametrize(
    "relations,resource_module_id,expected",
    [
        ([], 100, True),
        ([{"bk_module_id": 100}], 100, False),
        ([{"bk_module_id": 200}], 100, True),
    ],
)
def test_resolve_replicaset_deploy_is_increment(relations, resource_module_id, expected):
    with patch(
        "backend.flow.utils.mongodb.mongodb_module_operate.CCApi.find_host_biz_relations",
        return_value=relations,
    ):
        assert MongoDBCCTopoOperator.resolve_replicaset_deploy_is_increment(1, resource_module_id) is expected
