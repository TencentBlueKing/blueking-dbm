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

from backend.db_meta.models import Cluster
from backend.flow.engine.bamboo.scene.spider.validate.exception import GhostCollationFailedException
from backend.flow.engine.validate.mysql_base_validate import MysqlBaseValidator
from backend.flow.utils.mysql.rocksdb_ghost_collation_check import (
    check_rocksdb_ghost_collation,
    format_ghost_collation_findings,
)


class TenDBClusterOnlineDDLValidator(MysqlBaseValidator):
    """校验 TenDBCluster Online DDL 的 RocksDB gh-ost 字符集配置。"""

    def __call__(self):
        error_messages = []
        for cluster_id in self.data.get("cluster_ids", []):
            cluster = Cluster.objects.get(id=cluster_id)
            findings = check_rocksdb_ghost_collation(cluster)
            if findings:
                error_messages.append(format_ghost_collation_findings(findings))

        if error_messages:
            raise GhostCollationFailedException("\n".join(error_messages))

        return None
