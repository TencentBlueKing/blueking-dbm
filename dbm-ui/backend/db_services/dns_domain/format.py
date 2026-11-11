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


def normalize_domain(domain: str) -> str:
    return (domain or "").strip().lower().rstrip(".")


def display_instance(instance: str) -> str:
    """ip#port 展示为 IP。端口 0 只保留 IP，其余保留 ip:port。"""
    ip, separator, port = (instance or "").partition("#")
    if not separator or port in ("", "0"):
        return ip
    return f"{ip}:{port}"


def display_record(record: dict) -> str:
    ip = record.get("ip") or record.get("target") or ""
    port = record.get("port") or 0
    try:
        port_number = int(port)
    except (TypeError, ValueError):
        port_number = 0
    if port_number == 0:
        return str(ip)
    return f"{ip}:{port_number}"
