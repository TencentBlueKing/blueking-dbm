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
from typing import Dict, List

from django.db import transaction
from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import Service

from backend.db_meta.models import Cluster
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.mongodb.mongodb_conf_file import (
    migrate_mongodb_cluster_to_role,
    mongodb_conf_file_candidates,
    resolve_cluster_dbconf_level_value,
)
from backend.flow.utils.mongodb.version_utils import (
    extract_mongodb_major_minor,
    is_mongodb_major_minor_only,
    lookup_mongodb_package,
    normalize_mongodb_full_version,
    resolve_mongodb_metadata_versions,
    resolve_mongodb_persist_version,
)


class MongoUpdateVersionService(BaseService):
    """Persist MongoDB version to storage/proxy/cluster metadata."""

    @staticmethod
    def _resolve_conf_source_version(old_major_version: str, target_cluster_version: str) -> str:
        """Resolve a version hint for probing legacy/versioned dbconf conf_file names."""
        if not old_major_version:
            return target_cluster_version
        try:
            return "mongodb-{}".format(extract_mongodb_major_minor(old_major_version))
        except ValueError:
            pass
        if old_major_version.startswith("Mongodb-"):
            legacy_major = old_major_version.split("-", 1)[1]
            try:
                target_mm = extract_mongodb_major_minor(target_cluster_version)
                if legacy_major == target_mm.split(".", 1)[0]:
                    return "mongodb-{}".format(target_mm)
            except ValueError:
                pass
            return "mongodb-{}.0".format(legacy_major)
        return old_major_version

    @staticmethod
    def _migrate_cluster_conf_on_version_update(
        *,
        cluster,
        bk_biz_id: int,
        old_major_version: str,
        target_cluster_version: str,
    ) -> Dict:
        """Migrate versioned CLUSTER dbconf into role conf_files (no version hop)."""
        level_value = resolve_cluster_dbconf_level_value(cluster)
        source_version = MongoUpdateVersionService._resolve_conf_source_version(
            old_major_version, target_cluster_version
        )
        return migrate_mongodb_cluster_to_role(
            bk_biz_id=bk_biz_id,
            namespace=cluster.cluster_type,
            level_value=level_value,
            version=source_version,
        )

    @classmethod
    def _resolve_target_version(cls, raw_target: str) -> str:
        package = lookup_mongodb_package(raw_target)
        if is_mongodb_major_minor_only(raw_target):
            if not package:
                raise ValueError("no mongodb package found for major.minor target version {}".format(raw_target))
            return resolve_mongodb_persist_version(raw_target, package=package)
        return normalize_mongodb_full_version(raw_target)

    @classmethod
    def _resolve_metadata_versions(cls, raw_target: str) -> dict:
        package = lookup_mongodb_package(raw_target)
        instance_version = cls._resolve_target_version(raw_target)
        return resolve_mongodb_metadata_versions(instance_version, package=package)

    @staticmethod
    def _snapshot_cluster_versions(cluster) -> Dict:
        instances = []
        for row in cluster.storageinstance_set.values("port", "version", "machine__ip"):
            instances.append(
                {
                    "type": "storage",
                    "ip": row["machine__ip"],
                    "port": row["port"],
                    "old_version": row["version"] or "",
                }
            )
        for row in cluster.proxyinstance_set.values("port", "version", "machine__ip"):
            instances.append(
                {
                    "type": "proxy",
                    "ip": row["machine__ip"],
                    "port": row["port"],
                    "old_version": row["version"] or "",
                }
            )
        return {
            "cluster_id": cluster.id,
            "domain": cluster.immute_domain,
            "old_major_version": cluster.major_version or "",
            "instances": instances,
        }

    def _log_cluster_version_updates(
        self, snapshot: Dict, target_cluster_version: str, target_instance_version: str
    ) -> None:
        lines = [
            _("[mongo version persist] cluster={} (id={})").format(snapshot["domain"], snapshot["cluster_id"]),
            "  {}: {} -> {}".format(
                _("major_version"),
                snapshot["old_major_version"] or "-",
                target_cluster_version,
            ),
        ]
        for inst in snapshot["instances"]:
            old_version = inst["old_version"] or "-"
            unchanged_suffix = " (unchanged)" if old_version == target_instance_version else ""
            lines.append(
                "  {} {}:{}: {} -> {}{}".format(
                    inst["type"],
                    inst["ip"],
                    inst["port"],
                    old_version,
                    target_instance_version,
                    unchanged_suffix,
                )
            )
        self.log_info("\n".join(lines))

    def _log_conf_file_migration(
        self, snapshot: Dict, source_version: str, target_cluster_version: str, migration: Dict
    ) -> None:
        probe_version = source_version or target_cluster_version or ""
        source_candidates = "/".join(mongodb_conf_file_candidates(probe_version)) if probe_version else "(none)"
        target_files = ",".join(migration.get("target_conf_files") or []) or "role-conf"
        migrated = migration.get("migrated", False)
        status = "done" if migrated else "skip"
        deleted = list(migration.get("deleted_conf_files") or [])
        deleted_one = migration.get("deleted_conf_file")
        if deleted_one and deleted_one not in deleted:
            deleted.insert(0, deleted_one)
        extra = ", deleted={}".format(",".join(deleted)) if deleted else ""
        self.log_info(
            "[mongo conf_file migrate] cluster={} (id={}) {}: {} -> {}{}".format(
                snapshot["domain"],
                snapshot["cluster_id"],
                status,
                source_candidates,
                target_files,
                extra,
            )
        )

    @transaction.atomic
    def _persist_cluster_metadata(
        self,
        clusters,
        target_instance_version: str,
        target_cluster_version: str,
    ):
        """Persist version fields in DB only; dbconfig migration runs outside this transaction."""
        storage_count = 0
        proxy_count = 0
        cluster_domains = []
        for cluster in clusters:
            storage_count += cluster.storageinstance_set.update(version=target_instance_version)
            proxy_count += cluster.proxyinstance_set.update(version=target_instance_version)
            cluster.major_version = target_cluster_version
            cluster.save(update_fields=["major_version"])
            cluster_domains.append(cluster.immute_domain)
        return storage_count, proxy_count, cluster_domains

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        cluster_kwargs = kwargs["cluster"]
        cluster_id_list = cluster_kwargs["cluster_id_list"]
        clusters = list(Cluster.objects.filter(id__in=cluster_id_list, bk_biz_id=cluster_kwargs["bk_biz_id"]))
        if not clusters:
            raise Cluster.DoesNotExist(
                "no mongodb clusters found for ids {} in bk_biz_id {}".format(
                    cluster_id_list, cluster_kwargs["bk_biz_id"]
                )
            )

        raw_target = cluster_kwargs["target_version"]
        versions = self._resolve_metadata_versions(raw_target)
        target_instance_version = versions["instance"]
        target_cluster_version = versions["cluster"]
        package = (
            lookup_mongodb_package(raw_target)
            or lookup_mongodb_package(target_instance_version)
            or lookup_mongodb_package(target_cluster_version)
        )
        if package is None:
            raise ValueError("no mongodb package found for target version {}".format(target_instance_version))

        snapshots = []
        for cluster in clusters:
            snapshot = self._snapshot_cluster_versions(cluster)
            snapshots.append(snapshot)
            migration = self._migrate_cluster_conf_on_version_update(
                cluster=cluster,
                bk_biz_id=cluster_kwargs["bk_biz_id"],
                old_major_version=snapshot["old_major_version"],
                target_cluster_version=target_cluster_version,
            )
            self._log_conf_file_migration(snapshot, snapshot["old_major_version"], target_cluster_version, migration)

        storage_count, proxy_count, cluster_domains = self._persist_cluster_metadata(
            clusters, target_instance_version, target_cluster_version
        )

        for snapshot in snapshots:
            self._log_cluster_version_updates(snapshot, target_cluster_version, target_instance_version)

        self.log_info(
            "mongo clusters [{}] persist cluster_version=[{}] instance_version=[{}] done, storage={}, proxy={}".format(
                ",".join(cluster_domains),
                target_cluster_version,
                target_instance_version,
                storage_count,
                proxy_count,
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
