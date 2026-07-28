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
from backend.components import CCApi
from backend.dbm_aiagent.mcp_tools.exceptions import DBMMcpForbiddenException


def check_operator(username: str, bk_host_ids: list[int]):
    unique_host_ids = list(set(bk_host_ids))
    kwargs = {
        "fields": ["bk_host_id"],
        "host_property_filter": {
            "condition": "AND",
            "rules": [
                {"field": "bk_host_id", "operator": "in", "value": unique_host_ids},
                {
                    "condition": "OR",
                    "rules": [
                        {"field": "operator", "operator": "equal", "value": username},
                        {"field": "bk_bak_operator", "operator": "equal", "value": username},
                    ],
                },
            ],
        },
    }

    res = CCApi.list_hosts_without_biz(kwargs, use_admin=True)
    match_host_ids = {ele["bk_host_id"] for ele in res.get("info", []) if ele.get("bk_host_id")}
    not_match_ids = set(unique_host_ids) - match_host_ids
    if not_match_ids:
        raise DBMMcpForbiddenException(msg=f"machines {sorted(not_match_ids)} are not operated by {username}")
