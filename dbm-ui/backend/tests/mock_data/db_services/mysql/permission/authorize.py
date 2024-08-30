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

from backend import env

BK_BIZ_ID = env.DBA_APP_BK_BIZ_ID
BK_USERNAME = "admin"

ACCESS_DBS = ["datamain"]
TARGET_INSTANCES = ["blueking.db1.com", "blueking.db2.com"]
SOURCE_IPS = ["127.0.0.1", "127.0.0.2"]

AUTHORIZE_DATA = {
    "user": BK_USERNAME,
    "access_dbs": ACCESS_DBS,
    "source_ips": SOURCE_IPS,
    "target_instances": TARGET_INSTANCES,
    "cluster_type": "tendbha",
}

EXCEL_DATA_DICT__LIST = [
    {
        "账号(单个)": BK_USERNAME,
        "访问源(多个)": "\n".join(SOURCE_IPS),
        "访问集群域名(多个)": "\n".join(TARGET_INSTANCES),
        "访问DB名(多个)": "\n".join(ACCESS_DBS),
    }
]
