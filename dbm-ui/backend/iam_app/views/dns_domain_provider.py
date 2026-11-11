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
from django.db import models
from iam.resource.provider import ListResult

from backend.db_meta.enums import ClusterEntryType
from backend.db_meta.models import Cluster, ClusterEntry
from backend.db_services.dns_domain.format import normalize_domain
from backend.db_services.dns_domain.models import DnsDomain
from backend.iam_app.dataclass.resources import ResourceEnum, ResourceMeta
from backend.iam_app.views.iam_provider import BaseModelResourceProvider


class DnsDomainResourceProvider(BaseModelResourceProvider):
    """完整域名资源。自主维护域名来自域名表，集群托管域名来自集群入口。"""

    model: models.Model = DnsDomain
    resource_meta: ResourceMeta = ResourceEnum.DNS_DOMAIN

    def get_bk_iam_path(self, instance_ids, *args, **kwargs):
        return {str(instance_id): "" for instance_id in instance_ids}

    def list_instance(self, filter, page, **options):
        keyword = (filter.get("search") or filter.get("keyword") or "").strip().lower()
        domains = set(DnsDomain.objects.values_list("domain", flat=True))
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
        matched = sorted(domain for domain in domains if not keyword or keyword in domain)
        page_items = matched[page.slice_from : page.slice_to]
        results = [{"id": domain, "display_name": domain} for domain in page_items]
        return ListResult(results=results, count=len(matched))

    def search_instance(self, filter, page, **options):
        return self.list_instance(filter, page, **options)

    def fetch_instance_info(self, filter, **options):
        ids = [str(item) for item in (filter.ids or [])]
        creators = dict(DnsDomain.objects.filter(domain__in=ids).values_list("domain", "creator"))
        results = [
            {"id": domain, "display_name": domain, "creator": creators.get(domain, ""), "_bk_iam_path_": ""}
            for domain in ids
        ]
        return ListResult(results=results, count=len(results))

    def list_instance_by_policy(self, filter, page, **options):
        key_mapping = {
            f"{self.resource_meta.id}.id": "domain",
            f"{self.resource_meta.id}.creator": "creator",
        }
        return self._list_instance_by_policy(
            data_source=self.model,
            value_list=["domain", "domain"],
            key_mapping=key_mapping,
            value_hooks={},
            filter=filter,
            page=page,
        )
