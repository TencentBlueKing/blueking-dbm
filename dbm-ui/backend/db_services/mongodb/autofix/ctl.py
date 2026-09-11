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
from typing import List

from backend.db_services.mongodb.autofix.enums import MongoAutofixCtlItem
from backend.db_services.mongodb.autofix.models import MongoAutofixCtl

logger = logging.getLogger("root")

# defaults: enable=off; empty whitelist + enable=on → allow all (灰度白名单仅在配置时生效)
CTL_DEFAULTS = {
    MongoAutofixCtlItem.ENABLE.value: "off",
    MongoAutofixCtlItem.BIZ_WHITELIST.value: "",
    MongoAutofixCtlItem.DOMAIN_WHITELIST.value: "",
    MongoAutofixCtlItem.DELAY_MINUTES.value: "10",
    MongoAutofixCtlItem.PEER_MIN_COUNT.value: "2",
    MongoAutofixCtlItem.ZONE_HOST_THRESHOLD.value: "3",
    MongoAutofixCtlItem.ZONE_PERCENT_THRESHOLD.value: "0.3",
    MongoAutofixCtlItem.CITY_HOST_THRESHOLD.value: "5",
    MongoAutofixCtlItem.ENABLE_CONFIGSVR.value: "off",
    MongoAutofixCtlItem.DRY_RUN.value: "off",
}


def get_ctl_value(ctl_name: str, default: str | None = None) -> str:
    """Read MongoAutofixCtl value; fall back to CTL_DEFAULTS / default."""
    if default is None:
        default = CTL_DEFAULTS.get(ctl_name, "")
    try:
        row = MongoAutofixCtl.objects.filter(ctl_name=ctl_name).first()
        if row is None:
            return default
        return row.ctl_value if row.ctl_value is not None else default
    except Exception as exc:  # noqa: BLE001 — ctl read must not break discovery
        logger.warning("mongo autofix ctl read failed name=%s err=%s", ctl_name, exc)
        return default


def is_autofix_enabled() -> bool:
    return get_ctl_value(MongoAutofixCtlItem.ENABLE.value).lower() == "on"


def is_dry_run() -> bool:
    return get_ctl_value(MongoAutofixCtlItem.DRY_RUN.value).lower() == "on"


def is_configsvr_enabled() -> bool:
    return get_ctl_value(MongoAutofixCtlItem.ENABLE_CONFIGSVR.value).lower() == "on"


def get_delay_minutes() -> int:
    try:
        return max(0, int(get_ctl_value(MongoAutofixCtlItem.DELAY_MINUTES.value)))
    except (TypeError, ValueError):
        return 10


def get_peer_min_count() -> int:
    try:
        return max(1, int(get_ctl_value(MongoAutofixCtlItem.PEER_MIN_COUNT.value)))
    except (TypeError, ValueError):
        return 2


def get_zone_host_threshold() -> int:
    try:
        return max(1, int(get_ctl_value(MongoAutofixCtlItem.ZONE_HOST_THRESHOLD.value)))
    except (TypeError, ValueError):
        return 3


def get_zone_percent_threshold() -> float:
    try:
        return float(get_ctl_value(MongoAutofixCtlItem.ZONE_PERCENT_THRESHOLD.value))
    except (TypeError, ValueError):
        return 0.3


def get_city_host_threshold() -> int:
    try:
        return max(1, int(get_ctl_value(MongoAutofixCtlItem.CITY_HOST_THRESHOLD.value)))
    except (TypeError, ValueError):
        return 5


def _parse_csv(raw: str) -> List[str]:
    if not raw or not str(raw).strip():
        return []
    return [part.strip() for part in str(raw).split(",") if part.strip()]


def get_biz_whitelist() -> List[int]:
    items = []
    for part in _parse_csv(get_ctl_value(MongoAutofixCtlItem.BIZ_WHITELIST.value)):
        try:
            items.append(int(part))
        except (TypeError, ValueError):
            logger.warning("mongo autofix biz_whitelist skip invalid: %s", part)
    return items


def get_domain_whitelist() -> List[str]:
    return _parse_csv(get_ctl_value(MongoAutofixCtlItem.DOMAIN_WHITELIST.value))


def is_biz_allowed(bk_biz_id: int) -> bool:
    """Empty whitelist → allow all when enable is on."""
    whitelist = get_biz_whitelist()
    if not whitelist:
        return True
    return int(bk_biz_id) in whitelist


def is_domain_allowed(immute_domain: str) -> bool:
    """Empty whitelist → allow all when enable is on."""
    whitelist = get_domain_whitelist()
    if not whitelist:
        return True
    return immute_domain in whitelist


def is_whitelist_allowed(bk_biz_id: int, immute_domain: str) -> bool:
    return is_biz_allowed(bk_biz_id) and is_domain_allowed(immute_domain)
