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
from backend.constants import DEFAULT_BK_CLOUD_ID


def format_sops_ip(ip: str, bk_cloud_id=None) -> str:
    """标准运维 IP 格式：默认管控区域用裸 IP，非 0 管控区域用「管控区域:IP」。"""
    try:
        cloud_id = int(bk_cloud_id)
    except (TypeError, ValueError):
        cloud_id = DEFAULT_BK_CLOUD_ID
    return f"{cloud_id}:{ip}" if cloud_id else ip
