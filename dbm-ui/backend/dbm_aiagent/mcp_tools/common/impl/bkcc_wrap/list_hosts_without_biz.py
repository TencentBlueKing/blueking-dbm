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
from backend.dbm_aiagent.mcp_tools.common.serializers.bkcc_wrap.list_hosts_without_biz import CCHostInfoSerializer


def list_hosts_without_biz(bk_cloud_id: int, ips: list[str]):
    kwargs = {
        "fields": list(CCHostInfoSerializer().fields.keys()),
        "host_property_filter": {
            "condition": "AND",
            "rules": [
                {"field": "bk_host_innerip", "operator": "in", "value": ips},
                {"field": "bk_cloud_id", "operator": "equal", "value": bk_cloud_id},
            ],
        },
    }

    res = CCApi.list_hosts_without_biz(kwargs, use_admin=True)
    return res["info"]
