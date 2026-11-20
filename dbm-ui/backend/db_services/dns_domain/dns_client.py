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
from backend.db_services.dns_domain.constants import DOMAIN_TYPE_SELF
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

    def search_domains(self, domain_name="", domain_type=None, manager="", page=1, page_size=20) -> dict:
        """按域名、维护方式、负责人检索。分页和总数以 DNS 服务返回为准。"""
        params = {"page": page, "page_size": page_size}
        if domain_name:
            params["domain_name"] = domain_name
        if domain_type is not None:
            params["domain_type"] = domain_type
        if manager:
            params["manager"] = manager
        try:
            res = DnsApi.search_domain(params) or {}
        except Exception:  # pylint: disable=broad-except
            logger.exception("search dns domains failed")
            raise
        return self._page_result(res)

    @staticmethod
    def _page_result(res) -> dict:
        if isinstance(res, dict):
            return {"detail": res.get("detail") or [], "rowsNum": res.get("rowsNum") or 0}
        records = list(res or [])
        return {"detail": records, "rowsNum": len(records)}

    def write_oplogs(self, logs: list):
        """把操作日志交给 DNS 服务。空列表不请求。"""
        if not logs:
            return
        DnsApi.create_oplog({"logs": logs})

    def search_oplogs(
        self,
        scope,
        domain_name="",
        operator="",
        op_type="",
        start_time="",
        end_time="",
        page=1,
        page_size=20,
    ) -> dict:
        """有域名走 /oplog/domain，否则走 /oplog/all。分页和总数以 DNS 服务返回为准。"""
        params = {"page": page, "page_size": page_size}
        if operator:
            params["operator"] = operator
        if op_type:
            params["op_type"] = op_type
        if start_time:
            params["start_time"] = start_time
        if end_time:
            params["end_time"] = end_time
        if scope == "domain":
            params["domain_name"] = domain_name
            api = DnsApi.search_domain_oplog
        else:
            api = DnsApi.search_all_oplog
        try:
            res = api(params) or {}
        except Exception:  # pylint: disable=broad-except
            logger.exception("search dns oplog failed, scope=%s", scope)
            raise
        return self._page_result(res)

    def list_records(self) -> list:
        """列出该云区域下 DNS 服务里的解析。域名数据以 DNS 服务为准。"""
        try:
            res = DnsApi.get_all_domain_list({"app": str(self.bk_biz_id), "bk_cloud_id": self.bk_cloud_id})
        except Exception:  # pylint: disable=broad-except
            logger.exception("list dns domains failed, bk_cloud_id=%s", self.bk_cloud_id)
            raise
        if isinstance(res, dict):
            return res.get("detail") or []
        return list(res or [])

    def create_ips(self, domain: str, ips: list, manager="", remark=""):
        """创建自主维护域名。创建接口的 domain_type 是字符串。"""
        item = {
            "domain_name": DnsManage.format_domain(domain),
            "instances": list(ips),
            "domain_type": DOMAIN_TYPE_SELF,
        }
        if manager:
            item["manager"] = manager
        if remark:
            item["remark"] = remark
        payload = [item]
        DnsApi.create_domain({"app": str(self.bk_biz_id), "domains": payload, "bk_cloud_id": self.bk_cloud_id})

    def delete_domain(self, domain: str):
        payload = [{"domain_name": DnsManage.format_domain(domain)}]
        DnsApi.delete_domain({"app": str(self.bk_biz_id), "domains": payload, "bk_cloud_id": self.bk_cloud_id})

    def replace_ips(self, domain: str, ips: list):
        """用提交的 IP 集合覆盖原集合。已有记录的 IP 变更走 DNS 更新接口。返回新增、删除的展示值。"""
        current = self._current_instances(domain)
        target = [f"{ip}#0" for ip in ips]
        removed = [item for item in current if item not in target]
        added = [item for item in target if item not in current]
        # 更新接口一次只替换一条实例。能配对的走更新，多出来的再删或增。
        for old_instance, new_instance in zip(removed, added):
            self._dns.update_domain(old_instance, new_instance, domain)
        extra_removed = removed[len(added) :]
        extra_added = added[len(removed) :]
        if extra_removed:
            self._dns.remove_domain_ip(domain, extra_removed)
        if extra_added:
            self._dns.create_domain(instance_list=extra_added, add_domain_name=domain)
        return [self._display_instance(item) for item in added], [self._display_instance(item) for item in removed]

    @staticmethod
    def _display_instance(instance: str) -> str:
        ip, _, port = instance.partition("#")
        return display_record({"ip": ip, "port": port})

    def _current_instances(self, domain: str) -> list:
        records = self._dns.get_domain(domain) or []
        instances = []
        for record in records:
            ip = record.get("ip") or record.get("target") or ""
            port = record.get("port") or 0
            if ip:
                instances.append(f"{ip}#{port}")
        return instances
