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

BK_PKG_INSTALL_PATH = "/data/install"

BK_TRANSFER_REPO_PAYLOAD = {
    "bk_biz_id": 0,
    "file_target_path": BK_PKG_INSTALL_PATH,
    "transfer_mode": 2,
    "file_source_list": [],
    "target_server": {"ip_list": []},
    "account_alias": "root",
}

BK_PUSH_CONFIG_PAYLOAD = {
    "bk_scope_type": "biz_set",
    "bk_scope_id": env.JOB_BLUEKING_BIZ_ID,
    "account_alias": "root",
    "file_list": [],
    "target_server": {},
    "file_target_path": BK_PKG_INSTALL_PATH,
}
