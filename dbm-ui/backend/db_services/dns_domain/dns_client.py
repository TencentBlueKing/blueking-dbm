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
from backend.db_services.dns_domain.format import as_instances, clamp_page_size, display_record, format_managers
from backend.flow.utils.dns_manage import DnsManage

logger = logging.getLogger("root")


class DnsDomainClient(object):
    """非 db 域名管理。只调用 /nodb 接口，不走集群使用的域名接口。"""

    def __init__(self, bk_biz_id: int, bk_cloud_id: int):
        self.bk_biz_id = bk_biz_id
        self.bk_cloud_id = bk_cloud_id

    def list_ips(self, domain: str) -> list:
        ips = []
        seen = set()
        for record in self.list_instance_records(domain):
            text = display_record(record)
            if text and text not in seen:
                seen.add(text)
                ips.append(text)
        return ips

    def list_instance_records(self, domain: str) -> list:
        """按域名查询实例记录。一行一个实例，不分页。"""
        params = self._scope()
        params["domain_name"] = DnsManage.format_domain(domain)
        try:
            res = DnsApi.get_nodb_domain(params) or {}
        except Exception:  # pylint: disable=broad-except
            logger.exception("get nodb domain failed, domain=%s", domain)
            raise
        if isinstance(res, dict):
            return res.get("detail") or []
        return list(res or [])

    def has_mapping(self, domain: str) -> bool:
        return bool(self.list_ips(domain))

    def search_domains(self, domain_name="", domain_type=None, manager="", page=1, page_size=20) -> dict:
        """按域名、维护方式、负责人检索。一行一个域名，分页和总数以 DNS 服务返回为准。"""
        page, page_size = self._clamp_page(page, page_size)
        params = {"page": page, "page_size": page_size}
        if domain_name:
            params["domain_name"] = domain_name
        if domain_type is not None:
            params["domain_type"] = domain_type
        if manager:
            params["manager"] = manager
        try:
            res = DnsApi.search_nodb_domain(params) or {}
        except Exception:  # pylint: disable=broad-except
            logger.exception("search nodb domains failed")
            raise
        return self._page_result(res)

    @staticmethod
    def _page_result(res) -> dict:
        if isinstance(res, dict):
            return {"detail": res.get("detail") or [], "rowsNum": res.get("rowsNum") or 0}
        records = list(res or [])
        return {"detail": records, "rowsNum": len(records)}

    def search_oplogs(
        self,
        domain_name="",
        operator="",
        op_type="",
        page=1,
        page_size=20,
    ) -> dict:
        """查询域名操作日志。domain_name 可选，按包含关系模糊匹配。"""
        page, page_size = self._clamp_page(page, page_size)
        params = {"page": page, "page_size": page_size}
        if domain_name:
            params["domain_name"] = domain_name
        if operator:
            params["operator"] = operator
        if op_type:
            params["op_type"] = op_type
        try:
            res = DnsApi.search_nodb_all_oplog(params) or {}
        except Exception:  # pylint: disable=broad-except
            logger.exception("search dns oplog failed, domain=%s", domain_name)
            raise
        return self._page_result(res)

    def search_domain_oplogs(
        self,
        domain_name,
        operator="",
        op_type="",
        page=1,
        page_size=20,
    ) -> dict:
        """查询指定域名的操作日志。域名精确匹配。"""
        page, page_size = self._clamp_page(page, page_size)
        params = {
            "page": page,
            "page_size": page_size,
            "domain_name": DnsManage.format_domain(domain_name),
        }
        if operator:
            params["operator"] = operator
        if op_type:
            params["op_type"] = op_type
        try:
            res = DnsApi.search_nodb_domain_oplog(params) or {}
        except Exception:  # pylint: disable=broad-except
            logger.exception("search dns domain oplog failed, domain=%s", domain_name)
            raise
        return self._page_result(res)

    def list_records(self) -> list:
        """列出该云区域下的非 db 域名。检索接口一行一个域名。"""
        page = 1
        page_size = 1000
        records = []
        while True:
            data = self.search_domains(page=page, page_size=page_size)
            detail = data["detail"]
            records.extend(detail)
            if not detail or len(records) >= data["rowsNum"]:
                break
            page += 1
        return records

    def create_ips(self, domain: str, ips: list, manager="", remark="", operator=""):
        """添加非 db 域名。不传 operator 时，服务端用域名管理人作为更新人。"""
        item = {
            "domain_name": DnsManage.format_domain(domain),
            "instances": as_instances(ips),
            "domain_type": int(DOMAIN_TYPE_SELF),
            "remark": remark or "",
        }
        manager_text = format_managers([manager] if manager else [])
        if manager_text:
            item["manager"] = manager_text
        payload = self._scope()
        payload["domains"] = [item]
        self._set_operator(payload, operator)
        DnsApi.create_nodb_domain(payload)

    def delete_domain(self, domain: str, operator=""):
        """删除域名下的全部实例。"""
        payload = self._scope()
        payload["domains"] = [{"domain_name": DnsManage.format_domain(domain), "instances": []}]
        self._set_operator(payload, operator)
        DnsApi.delete_nodb_domain(payload)

    def update_domain_record(self, domain: str, ips: list, operator="", manager="", remark=""):
        """按保留实例列表同步域名，同时写入管理人和备注。"""
        payload = self._scope()
        payload.update(
            {
                "domain_name": DnsManage.format_domain(domain),
                "instances": as_instances(ips),
                "remark": remark or "",
            }
        )
        manager_text = format_managers([manager] if manager else [])
        if manager_text:
            payload["manager"] = manager_text
        self._set_operator(payload, operator)
        DnsApi.update_nodb_domain(payload)

    def _scope(self) -> dict:
        return {"app": str(self.bk_biz_id), "bk_cloud_id": self.bk_cloud_id}

    @staticmethod
    def _set_operator(payload: dict, operator: str):
        operator_text = (operator or "").strip()
        if operator_text:
            payload["operator"] = operator_text

    @staticmethod
    def _clamp_page(page, page_size):
        try:
            page_number = int(page)
        except (TypeError, ValueError):
            page_number = 1
        if page_number < 1:
            page_number = 1
        return page_number, clamp_page_size(page_size)
