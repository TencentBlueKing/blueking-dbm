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
import logging

from backend.components import DnsApi
from backend.db_services.dns_domain.format import display_record
from backend.flow.utils.dns_manage import DnsManage

logger = logging.getLogger("root")


class DnsDomainClient(object):
    """自主维护域名的解析读写。IP 集合的权威数据在 DBA dns-api，这里只做调用和差量。"""

    def __init__(self, bk_biz_id: int, bk_cloud_id: int):
        self.bk_biz_id = bk_biz_id
        self.bk_cloud_id = bk_cloud_id
        self._dns = DnsManage(bk_biz_id=bk_biz_id, bk_cloud_id=bk_cloud_id)

    def list_ips(self, domain: str) -> list:
        try:
            records = self._dns.get_domain(domain) or []
        except Exception:  # pylint: disable=broad-except
            logger.exception("get dns domain failed, domain=%s", domain)
            raise
        ips = []
        seen = set()
        for record in records:
            text = display_record(record)
            if text and text not in seen:
                seen.add(text)
                ips.append(text)
        return ips

    def has_mapping(self, domain: str) -> bool:
        return bool(self.list_ips(domain))

    def create_ips(self, domain: str, ips: list):
        self._dns.create_domain(instance_list=list(ips), add_domain_name=domain)

    def delete_domain(self, domain: str):
        payload = [{"domain_name": DnsManage.format_domain(domain)}]
        DnsApi.delete_domain({"app": str(self.bk_biz_id), "domains": payload, "bk_cloud_id": self.bk_cloud_id})

    def replace_ips(self, domain: str, ips: list):
        """用提交的 IP 集合覆盖原集合。返回新增、删除的展示值。"""
        current = self._current_instances(domain)
        target = [f"{ip}#0" for ip in ips]
        removed = [item for item in current if item not in target]
        added = [item for item in target if item not in current]
        if removed:
            self._dns.remove_domain_ip(domain, removed)
        if added:
            self._dns.create_domain(instance_list=added, add_domain_name=domain)
        return [display_record({"ip": item.split("#")[0], "port": item.split("#")[1]}) for item in added], [
            display_record({"ip": item.split("#")[0], "port": item.split("#")[1]}) for item in removed
        ]

    def _current_instances(self, domain: str) -> list:
        records = self._dns.get_domain(domain) or []
        instances = []
        for record in records:
            ip = record.get("ip") or record.get("target") or ""
            port = record.get("port") or 0
            if ip:
                instances.append(f"{ip}#{port}")
        return instances
