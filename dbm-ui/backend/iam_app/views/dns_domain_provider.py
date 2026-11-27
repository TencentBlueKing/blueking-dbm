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

from iam.resource.provider import ListResult

from backend.configuration.constants import PLAT_BIZ_ID
from backend.constants import DEFAULT_BK_CLOUD_ID
from backend.db_services.dns_domain.dns_client import DnsDomainClient
from backend.db_services.dns_domain.format import normalize_domain
from backend.iam_app.dataclass.resources import ResourceEnum, ResourceMeta
from backend.iam_app.views.iam_provider import BaseInterfaceResourceProvider

logger = logging.getLogger("root")


class DnsDomainResourceProvider(BaseInterfaceResourceProvider):
    """完整域名资源。实例来自 DNS 检索接口。"""

    resource_meta: ResourceMeta = ResourceEnum.DNS_DOMAIN

    def get_bk_iam_path(self, instance_ids, *args, **kwargs):
        """域名没有父资源，祖先路径为空。"""
        return {str(instance_id): "" for instance_id in instance_ids}

    def list_instance(self, filter, page, **options):
        filter.data_source = self._query_domains
        filter.value_list = [self.resource_meta.lookup_field, *self.resource_meta.display_fields]
        filter.keyword_field = "domain_name"
        return super().list_instance(filter, page, **options)

    def search_instance(self, filter, page, **options):
        return self.list_instance(filter, page, **options)

    def fetch_instance_info(self, filter, **options):
        ids = [str(item) for item in (filter.ids or [])]
        results = [{"id": domain, "display_name": domain, "_bk_iam_path_": ""} for domain in ids]
        return ListResult(results=results, count=len(results))

    def _list_instance(self, data_source, condition, value_list, page):
        """DNS 检索用 page/page_size，总数用 rowsNum。"""
        condition = self.convert_condition_field(dict(condition or {}))
        condition.update(limit=page.limit, offset=page.offset)
        payload = data_source(params=condition) or {}
        data = payload.get("results") or []
        results = [
            {
                "id": str(item[value_list[0]]),
                "display_name": ":".join([str(item[value]) for value in value_list[1:]]),
            }
            for item in data
        ]
        return ListResult(results=results, count=payload.get("count", len(results)))

    def _query_domains(self, params):
        """把 IAM 的分页和关键字转成 DNS 检索结果。"""
        if params.get("ids") is not None:
            domains = []
            seen = set()
            for raw in params.get("ids") or []:
                name = normalize_domain(str(raw))
                if name and name not in seen:
                    seen.add(name)
                    domains.append({"domain": name})
            return {"results": domains, "count": len(domains)}

        limit = params.get("limit") or 20
        offset = params.get("offset") or 0
        try:
            page_size = int(limit)
            page = int(offset) // page_size + 1
        except (TypeError, ValueError, ZeroDivisionError):
            page, page_size = 1, 20
        try:
            data = DnsDomainClient(PLAT_BIZ_ID, DEFAULT_BK_CLOUD_ID).search_domains(
                domain_name=params.get("domain_name") or "", page=page, page_size=page_size
            )
        except Exception:  # pylint: disable=broad-except
            logger.exception("list dns domains for iam failed")
            return {"results": [], "count": 0}

        results = []
        seen = set()
        for record in data.get("detail") or []:
            name = normalize_domain(record.get("domain_name") or record.get("domain") or "")
            if name and name not in seen:
                seen.add(name)
                results.append({"domain": name})
        return {"results": results, "count": data.get("rowsNum") or 0}
