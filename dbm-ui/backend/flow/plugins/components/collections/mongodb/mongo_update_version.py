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
from typing import List

from django.db import transaction
from django.db.models import Q
from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import Service

from backend.configuration.constants import DBType
from backend.db_meta.models import Cluster
from backend.db_package.models import Package
from backend.flow.consts import MediumEnum
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.mongodb.version_utils import normalize_mongodb_full_version


class MongoUpdateVersionService(BaseService):
    """Persist MongoDB version to storage/proxy/cluster metadata."""

    @transaction.atomic
    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        cluster_kwargs = kwargs["cluster"]
        cluster_id_list = cluster_kwargs["cluster_id_list"]
        clusters = Cluster.objects.filter(id__in=cluster_id_list, bk_biz_id=cluster_kwargs["bk_biz_id"])
        if not clusters.exists():
            raise Cluster.DoesNotExist(
                "no mongodb clusters found for ids {} in bk_biz_id {}".format(
                    cluster_id_list, cluster_kwargs["bk_biz_id"]
                )
            )

        target_version = normalize_mongodb_full_version(cluster_kwargs["target_version"])
        # Defensive check: only persist metadata when package line exists.
        raw_version = target_version.removeprefix("mongodb-")
        major_minor = ".".join(raw_version.split(".", 2)[:2])
        package_exists = Package.objects.filter(
            Q(version=target_version)
            | Q(version=raw_version)
            | Q(version__startswith="{}.".format(major_minor))
            | Q(version__startswith="mongodb-{}.".format(major_minor)),
            pkg_type=MediumEnum.MongoDB,
            db_type=DBType.MongoDB,
            enable=True,
        ).exists()
        if not package_exists:
            raise ValueError("no mongodb package found for target version {}".format(target_version))

        storage_count = 0
        proxy_count = 0
        cluster_domains = []
        for cluster in clusters:
            storage_count += cluster.storageinstance_set.update(version=target_version)
            proxy_count += cluster.proxyinstance_set.update(version=target_version)
            cluster.major_version = target_version
            cluster.save(update_fields=["major_version"])
            cluster_domains.append(cluster.immute_domain)

        self.log_info(
            "mongo clusters [{}] persist version [{}] done, storage={}, proxy={}".format(
                ",".join(cluster_domains), target_version, storage_count, proxy_count
            )
        )
        return True

    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]


class MongoUpdateVersionComponent(Component):
    name = __name__
    code = "mongo_update_version"
    bound_service = MongoUpdateVersionService
