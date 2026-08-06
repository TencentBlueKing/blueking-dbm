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
from unittest.mock import MagicMock, patch

import pytest
from rest_framework.exceptions import ValidationError

from backend.db_meta.models import Cluster
from backend.dbm_aiagent.mcp_tools.mongodb.impl import cluster_meta


@pytest.mark.parametrize(
    "func", [cluster_meta.cluster_overview, cluster_meta.cluster_mongos, cluster_meta.cluster_shards]
)
def test_unknown_domain_raises_validation_error(func):
    """域名不存在时返回 400 而不是未捕获的 DoesNotExist（500）"""
    queryset = MagicMock()
    queryset.get.side_effect = Cluster.DoesNotExist
    queryset.prefetch_related.return_value = queryset
    with patch.object(cluster_meta.Cluster, "objects", queryset):
        with pytest.raises(ValidationError):
            func("not-exists.dba.db")
