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

from backend.db_meta.models import Cluster
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.mysql.rocksdb_ghost_collation_check import (
    check_rocksdb_ghost_collation,
    format_ghost_collation_findings,
)


class CheckRocksDBGhostCollationService(BaseService):
    """检查 RocksDB 是否允许 gh-ost 临时表绕过严格字符集检查。"""

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        cluster = Cluster.objects.get(id=kwargs["cluster_id"])
        findings = check_rocksdb_ghost_collation(cluster)
        if findings:
            self.log_error(format_ghost_collation_findings(findings))
            return False
        return True


class CheckRocksDBGhostCollationComponent(Component):
    name = __name__
    code = "check_rocksdb_ghost_collation"
    bound_service = CheckRocksDBGhostCollationService
