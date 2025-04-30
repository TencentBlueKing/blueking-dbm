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


from backend.db_meta.enums.cluster_type import ClusterType
from backend.tests.mock_data import constant

BK_USERNAME = "admin"
BK_BIZ_ID = constant.BK_BIZ_ID
CLUSTER_ID = 177


TENDBCLUSTER_FULL_BACKUP_DATA = {
    "bk_biz_id": BK_BIZ_ID,
    "details": {
        "backup_type": "logical",
        "file_tag": "DBFILE1M",
        "infos": [{"cluster_id": CLUSTER_ID, "backup_local": "master"}],
    },
    "remark": "",
    "ticket_type": "TENDBCLUSTER_FULL_BACKUP",
}

TENDBCLUSTER_CLUSTER_DATA = {
    "id": CLUSTER_ID,
    "creator": BK_USERNAME,
    "updater": BK_USERNAME,
    "name": "dev-ygctest-tendbcluster",
    "alias": "",
    "bk_biz_id": BK_BIZ_ID,
    "cluster_type": ClusterType.TenDBCluster,
    "db_module_id": 42,
    "immute_domain": "spider.dev-ygctest-tendbcluster.dba.db",
    "major_version": "MySQL-5.7",
    "phase": "online",
    "status": "normal",
    "bk_cloud_id": 0,
    "region": "",
    "time_zone": "+08:00",
    "disaster_tolerance_level": "NONE",
}
