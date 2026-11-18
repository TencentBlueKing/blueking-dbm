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

from backend.db_periodic_task.constants import FailoverDrillVersion, parse_failover_drill_versions

logger = logging.getLogger("root")


def rows_from_old(old, extra=None):
    """从旧演练配置拆出每座城市一行。没有城市映射时不造数据。"""
    city_map = getattr(old, "city_map", None)
    if old is None or not isinstance(city_map, dict):
        return []
    labels = old.labels if isinstance(old.labels, list) else []
    extra = extra or {}
    versions = sorted(parse_failover_drill_versions(getattr(old, "version", None)))
    rows = []
    for city, abbr in city_map.items():
        name = str(city or "").strip()
        if not name or name == "default":
            continue
        for version in versions:
            rows.append(
                {
                    "city": name,
                    "city_abbr": str(abbr or "").strip(),
                    "version": version,
                    "enabled": False,
                    "bk_biz_id": int(old.bk_biz_id or 0),
                    "bk_cloud_id": int(old.bk_cloud_id or 0),
                    "db_module_id": int(old.db_module_id or 0),
                    "labels": list(labels),
                    "creator": "system",
                    "updater": "system",
                    **extra,
                }
            )
    return rows


def ensure_default_configs(sender=None, **kwargs):
    """新表缺城市时，从旧 TenDBHA / TenDBCluster 配置各抄一行。已有的行不改，新行默认不演练。"""
    try:
        created = _ensure_default_configs()
    except Exception as err:  # pylint: disable=broad-except
        logger.warning("skip mysql failover drill v1 default config: %s", err)
        return
    if created:
        logger.info("mysql failover drill v1 default config inserted: %s", created)


def _ensure_default_configs():
    from backend.db_meta.enums import ClusterType
    from backend.db_periodic_task.models import FailoverDrillConfig, MysqlFailoverDrillV1Config

    created = 0
    # TenDBCluster 的接入端口沿用旧 spider 演练的 25000，只在缺行时写入。
    extras = {ClusterType.TenDBCluster.value: {"start_proxy_port": 25000}}
    for cluster_type in (ClusterType.TenDBHA.value, ClusterType.TenDBCluster.value):
        old = FailoverDrillConfig.objects.filter(cluster_type=cluster_type).order_by("id").first()
        for row in rows_from_old(old, extras.get(cluster_type)):
            city = row.pop("city")
            version = row.pop("version", FailoverDrillVersion.V1.value)
            _, is_created = MysqlFailoverDrillV1Config.objects.get_or_create(
                cluster_type=cluster_type,
                city=city,
                version=version,
                defaults=row,
            )
            if is_created:
                created += 1
    return created
