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
from backend.db_meta.enums import ClusterEntryType
from backend.db_meta.models import Cluster, ClusterEntry
from backend.db_services.dns_domain.dns_client import DnsDomainClient
from backend.db_services.dns_domain.format import normalize_domain
from backend.iam_app.dataclass.resources import ResourceEnum, ResourceMeta
from backend.iam_app.views.iam_provider import BaseModelResourceProvider

logger = logging.getLogger("root")


class DnsDomainResourceProvider(BaseModelResourceProvider):
    """完整域名资源。域名来自 DNS 服务和集群入口，不读本地表。"""

    resource_meta: ResourceMeta = ResourceEnum.DNS_DOMAIN

    def get_bk_iam_path(self, instance_ids, *args, **kwargs):
        """域名没有父资源，祖先路径为空。"""
        return {str(instance_id): "" for instance_id in instance_ids}

    def list_instance(self, filter, page, **options):
        keyword = (filter.get("search") or filter.get("keyword") or "").strip().lower()
        domains = self._domain_names()
        matched = sorted(domain for domain in domains if not keyword or keyword in domain)
        page_items = matched[page.slice_from : page.slice_to]
        results = [{"id": domain, "display_name": domain} for domain in page_items]
        return ListResult(results=results, count=len(matched))

    def _domain_names(self) -> set:
        """集群入口加上 DNS 服务里的域名。"""
        domains = set()
        for domain in Cluster.objects.exclude(immute_domain="").values_list("immute_domain", flat=True):
            normalized = normalize_domain(domain)
            if normalized:
                domains.add(normalized)
        entries = ClusterEntry.objects.filter(cluster_entry_type=ClusterEntryType.DNS.value).values_list(
            "entry", flat=True
        )
        for entry in entries:
            normalized = normalize_domain(entry)
            if normalized:
                domains.add(normalized)
        try:
            records = DnsDomainClient(PLAT_BIZ_ID, DEFAULT_BK_CLOUD_ID).list_records()
        except Exception:  # pylint: disable=broad-except
            logger.exception("list dns domains for iam failed")
            records = []
        for record in records:
            normalized = normalize_domain(record.get("domain_name") or record.get("domain") or "")
            if normalized:
                domains.add(normalized)
        return domains

    def search_instance(self, filter, page, **options):
        return self.list_instance(filter, page, **options)

    def fetch_instance_info(self, filter, **options):
        ids = [str(item) for item in (filter.ids or [])]
        results = [{"id": domain, "display_name": domain, "_bk_iam_path_": ""} for domain in ids]
        return ListResult(results=results, count=len(results))

    def list_instance_by_policy(self, filter, page, **options):
        if not getattr(filter, "expression", None):
            return ListResult(results=[], count=0)
        return self.list_instance(filter, page, **options)
