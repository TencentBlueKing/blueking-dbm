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


def format_managers(owners) -> str:
    """多个管理人用英文逗号拼接。去掉空格和重复项，与 dns-api 写入规则一致。"""
    names = []
    seen = set()
    for raw in owners or []:
        for part in str(raw or "").replace("，", ",").split(","):
            name = part.strip()
            if name and name not in seen:
                seen.add(name)
                names.append(name)
    return ",".join(names)


def as_instances(values) -> list:
    """实例写成 ip#port。只给 IP 时端口记为 0。"""
    instances = []
    for raw in values or []:
        text = str(raw or "").strip()
        if not text:
            continue
        if "#" not in text:
            text = f"{text}#0"
        instances.append(text)
    return instances


def clamp_page_size(page_size, default=20) -> int:
    """dns-api 的 page_size 只接受 1~1000，超出范围会报错。负数表示尽量取满。"""
    try:
        size = int(page_size)
    except (TypeError, ValueError):
        return default
    if size < 0 or size > 1000:
        return 1000
    if size < 1:
        return default
    return size


def page_from_limit_offset(limit, offset=0, default=20):
    """把 limit/offset 收成 dns-api 的 page、page_size。page 从 1 开始。"""
    page_size = clamp_page_size(limit, default)
    try:
        start = int(offset or 0)
    except (TypeError, ValueError):
        start = 0
    if start < 0:
        start = 0
    return start // page_size + 1, page_size


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
