# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

资源申请协议适配（v1 / v2）

两套协议的区别：
- v1 `POST /resource/apply`：location_spec 用 `city`（逻辑城）+ `sub_zone_ids`（园区 ID），
  选机算法按园区槽位打散；
- v2 `POST /v2/resource/apply`：location_spec 用 `bk_cloud_region`（云地域）+ `bk_cloud_zone_list`（云可用区），
  主维默认 `bk_cloud_zone`，跨可用区/指定可用区按云可用区判定。

dbm-ui 内部（单据 details、builder、计费参数）仍然沿用 v1 的 key：`city` / `sub_zone_ids`，
只是部署页改成选可用区后，值已经是可用区字符串（如 `ap-chongqing-1`）。因此统一下发前在这里做归一化：
- v1：资源池只认园区 ID，所以可用区要反向展开成园区 ID（`BKSubzone` 查询）；缺 city 时用可用区反查逻辑城。
  如果值本来就是园区 ID 或没有位置条件，请求体原样透传，老链路不变；
- v2：把 location_spec / current_hosts 转成新协议。数字的园区 ID 用 `BKSubzone` 反查云可用区，
  已经是可用区字符串的直接使用；反查不到的丢掉并记日志，不因此拒单。

开关：`env.RESOURCE_APPLY_API_VERSION`，取值 `v1`（默认）/ `v2`。前端已经按可用区提交，
只有开 v2 才能真的按「跨可用区」选机；v1 下「跨可用区」只能退化成「跨园区」。
"""
import logging
import random
import re
import uuid
from collections import defaultdict
from typing import Any, Dict, Iterable, List, Tuple

from backend import env
from backend.components.dbresource.client import DBResourceApi
from backend.configuration.constants import AffinityEnum
from backend.db_meta.models.city_map import BKSubzone

logger = logging.getLogger("root")

API_VERSION_V1 = "v1"
API_VERSION_V2 = "v2"

# 云可用区主维的取值，v2 显式传，避免服务端按老园区口径兜底
CLOUD_ZONE_DIMENSION = "bk_cloud_zone"

# 腾讯云地域形如 ap-chongqing / ap-nanjing / na-ashburn，
# 用于判断上游传的 city 是否已经是云地域（老前端传的是逻辑城名，如「南京」）
_CLOUD_REGION_PATTERN = re.compile(r"^[a-z]{2}-[a-z0-9-]+$")

# 这些容灾级别在 v2 下要求 bk_cloud_zone_list 至少 2 个可用区，
# 上游选「随机」时列表为空，需要后端在所选地域内补齐
_AFFINITY_REQUIRE_MULTI_ZONE = {AffinityEnum.CROS_SUBZONE.value}


def get_apply_api_version() -> str:
    """当前生效的资源申请协议版本"""
    version = str(getattr(env, "RESOURCE_APPLY_API_VERSION", "") or API_VERSION_V1).strip().lower()
    if version not in (API_VERSION_V1, API_VERSION_V2):
        logger.warning("unknown RESOURCE_APPLY_API_VERSION=%s, fallback to %s", version, API_VERSION_V1)
        return API_VERSION_V1
    return version


def is_v2_enabled() -> bool:
    return get_apply_api_version() == API_VERSION_V2


class CloudZoneIndex(object):
    """一次申请内的园区/可用区索引，避免逐条查库

    数据量不大（园区表是人工登记的基础数据），一次申请查一次即可。
    """

    def __init__(self):
        # bk_sub_zone_id(str) -> bk_cloud_zone
        self.zone_by_subzone_id: Dict[str, str] = {}
        # bk_sub_zone_id(str) -> bk_cloud_region
        self.region_by_subzone_id: Dict[str, str] = {}
        # bk_sub_zone -> bk_cloud_zone
        self.zone_by_subzone_name: Dict[str, str] = {}
        # bk_cloud_zone -> bk_cloud_region
        self.region_by_zone: Dict[str, str] = {}
        # 逻辑城 -> {bk_cloud_zone}
        self.zones_by_city: Dict[str, set] = defaultdict(set)
        # bk_cloud_zone -> [bk_sub_zone_id]（v1 只认园区 ID，需要反向展开）
        self.subzone_ids_by_zone: Dict[str, List[str]] = defaultdict(list)
        # bk_cloud_zone -> 逻辑城名（v1 必须带 city）
        self.city_by_zone: Dict[str, str] = {}

        rows = BKSubzone.objects.values(
            "bk_sub_zone", "bk_sub_zone_id", "bk_cloud_zone", "bk_cloud_region", "bk_city__logical_city__name"
        )
        for row in rows:
            zone = (row["bk_cloud_zone"] or "").strip()
            region = (row["bk_cloud_region"] or "").strip()
            subzone_id = str(row["bk_sub_zone_id"] or "")
            subzone_name = (row["bk_sub_zone"] or "").strip()
            city = (row["bk_city__logical_city__name"] or "").strip()

            if zone:
                if subzone_id:
                    self.zone_by_subzone_id[subzone_id] = zone
                    self.subzone_ids_by_zone[zone].append(subzone_id)
                if subzone_name:
                    self.zone_by_subzone_name[subzone_name] = zone
                if region:
                    self.region_by_zone.setdefault(zone, region)
                if city:
                    self.zones_by_city[city].add(zone)
                    self.city_by_zone.setdefault(zone, city)
            if subzone_id and region:
                self.region_by_subzone_id[subzone_id] = region

    def subzone_ids_of_zone(self, zone: str) -> List[str]:
        """一个可用区下登记过的园区 ID 列表"""
        return sorted(set(self.subzone_ids_by_zone.get(zone, [])))

    def city_of_zone(self, zone: str) -> str:
        return self.city_by_zone.get(zone, "")

    def resolve_zone(self, value: Any) -> str:
        """把上游给的位置值归一化成云可用区

        支持三种输入：云可用区字符串、园区 ID（数字或数字字符串）、园区名。
        """
        if value is None:
            return ""
        text = str(value).strip()
        if not text:
            return ""
        if text.isdigit():
            return self.zone_by_subzone_id.get(text, "")
        if text in self.region_by_zone:
            # 已经是云可用区
            return text
        # 兼容上游传园区全称的情况
        return self.zone_by_subzone_name.get(text, text)

    def zones_of_city(self, city: str) -> List[str]:
        return sorted(self.zones_by_city.get((city or "").strip(), set()))


def _dedup(values: Iterable[str]) -> List[str]:
    """去重并保持顺序"""
    return list(dict.fromkeys([value for value in values if value]))


def _resolve_cloud_zones(values: Any, index: CloudZoneIndex, field: str) -> List[str]:
    """把位置列表归一化成云可用区列表，反查不到的值丢掉并记日志"""
    if not values:
        return []
    if isinstance(values, (str, int)):
        values = [values]
    zones, unresolved = [], []
    for value in values:
        zone = index.resolve_zone(value)
        if zone:
            zones.append(zone)
        else:
            unresolved.append(str(value))
    if unresolved:
        logger.error(
            "resource apply: cannot resolve cloud zone for %s=%s, dropped. check BKSubzone register for these zones",
            field,
            unresolved,
        )
    return _dedup(zones)


def _resolve_region(location_spec: Dict[str, Any], index: CloudZoneIndex, zones: List[str]) -> Tuple[str, str]:
    """解析云地域，返回 (region, region 来源)

    优先级：
    1. 上游显式给的 bk_cloud_region；
    2. 已选可用区所属的地域（可用区只属于一个地域，最权威）；
    3. city 本身就是云地域（新前端/集群 bk_cloud_region）；
    4. city 是逻辑城名，用 BKSubzone 反查出唯一地域。
    """
    region = str(location_spec.get("bk_cloud_region") or "").strip()
    if region:
        return region, "location_spec.bk_cloud_region"

    zone_regions = _dedup([index.region_by_zone.get(zone, "") for zone in zones])
    if len(zone_regions) == 1:
        return zone_regions[0], "cloud_zone"
    if len(zone_regions) > 1:
        logger.error("resource apply: selected cloud zones %s belong to multiple regions %s", zones, zone_regions)

    city = str(location_spec.get("city") or "").strip()
    if city and city != "default":
        if _CLOUD_REGION_PATTERN.match(city):
            return city, "city"
        city_zones = index.zones_of_city(city)
        city_regions = _dedup([index.region_by_zone.get(zone, "") for zone in city_zones])
        if len(city_regions) == 1:
            return city_regions[0], "logical_city"

    return "", ""


def _coerce_affinity(affinity: Any) -> str:
    """亲和性常量统一成字符串，v2 不会把 None 收成 NONE，需要自己兜底"""
    if affinity is None:
        return ""
    value = getattr(affinity, "value", affinity)
    value = str(value).strip()
    return value


def _build_v2_location_spec(
    location_spec: Dict[str, Any], index: CloudZoneIndex, affinity: str, group_mark: str
) -> Dict[str, Any]:
    # 老协议用 include_or_exclue=False 表示「sub_zone_ids 是排除列表」，v2 有独立的排除字段
    is_exclude = location_spec.get("include_or_exclue") is False
    include_values = (
        [] if is_exclude else (location_spec.get("bk_cloud_zone_list") or location_spec.get("sub_zone_ids"))
    )
    zones = _resolve_cloud_zones(include_values, index, "bk_cloud_zone_list")
    region, region_source = _resolve_region(location_spec, index, zones)

    # 「跨可用区 + 随机」：上游给的是空列表，v2 要求至少 2 个可用区，这里在所选地域内补齐
    if not is_exclude and not zones and affinity in _AFFINITY_REQUIRE_MULTI_ZONE and region:
        candidates = sorted([zone for zone, zone_region in index.region_by_zone.items() if zone_region == region])
        if len(candidates) >= 2:
            zones = random.sample(candidates, 2)
            logger.info(
                "resource apply: %s affinity=%s with empty zone list, randomly picked %s in %s",
                group_mark,
                affinity,
                zones,
                region,
            )
        else:
            logger.error(
                "resource apply: %s affinity=%s needs 2 cloud zones but region %s only has %s",
                group_mark,
                affinity,
                region,
                candidates,
            )

    new_location_spec: Dict[str, Any] = {}
    if region:
        new_location_spec["bk_cloud_region"] = region
    if zones:
        new_location_spec["bk_cloud_zone_list"] = zones

    exclude_zones = _resolve_cloud_zones(
        location_spec.get("exclude_bk_cloud_zone_list") or location_spec.get("exclude_sub_zone_ids"),
        index,
        "exclude_bk_cloud_zone_list",
    )
    if is_exclude:
        exclude_zones = _dedup(
            exclude_zones
            + _resolve_cloud_zones(location_spec.get("sub_zone_ids"), index, "exclude_bk_cloud_zone_list")
        )
    if exclude_zones:
        new_location_spec["exclude_bk_cloud_zone_list"] = exclude_zones

    # v2 文档未声明支持机架排除，但服务端对未知字段是忽略而不是拒单，
    # 保留可以让「排除机架」类单据在服务端支持后自动生效
    if location_spec.get("exclude_rack_ids"):
        new_location_spec["exclude_rack_ids"] = location_spec["exclude_rack_ids"]

    if not new_location_spec:
        # 随机地域 / 无可用区：不传位置条件，等价于「不限地域、不限可用区」
        logger.info(
            "resource apply: %s has no usable location condition (city=%s, region_source=%s), "
            "location_spec is omitted",
            group_mark,
            location_spec.get("city"),
            region_source,
        )
    return new_location_spec


def _build_v2_current_hosts(current_hosts: List[Dict[str, Any]], index: CloudZoneIndex, group_mark: str) -> List[Dict]:
    """current_hosts 补上云可用区；补不出来的主机丢掉，避免整单被服务端拒绝"""
    result, dropped = [], []
    for host in current_hosts or []:
        host = dict(host)
        zone = host.get("bk_cloud_zone") or index.resolve_zone(host.get("sub_zone_id") or host.get("sub_zone"))
        if not zone:
            dropped.append(host.get("ip") or host.get("bk_host_id"))
            continue
        host["bk_cloud_zone"] = zone
        result.append(host)
    if dropped:
        logger.error(
            "resource apply: %s current_hosts %s have no cloud zone, they are ignored in affinity/tolerance",
            group_mark,
            dropped,
        )
    return result


def _build_v2_detail(detail: Dict[str, Any], index: CloudZoneIndex) -> Dict[str, Any]:
    """单组申请参数从 v1 结构转成 v2 结构"""
    group_mark = detail.get("group_mark", "")
    new_detail = dict(detail)
    affinity = _coerce_affinity(detail.get("affinity"))
    if affinity:
        new_detail["affinity"] = affinity
    else:
        new_detail.pop("affinity", None)

    # 指定主机申请时没有 location_spec，跳过位置转换（也不能给 v2 传 null）
    location_spec = detail.get("location_spec")
    new_detail.pop("location_spec", None)
    if location_spec:
        new_location_spec = _build_v2_location_spec(location_spec, index, affinity, group_mark)
        if new_location_spec:
            new_detail["location_spec"] = new_location_spec
            # 主维默认就是云可用区，上游显式指定 sub_zone 时保持原样（兼容老园区口径的单据）
            new_detail["affinity_dimension"] = detail.get("affinity_dimension") or CLOUD_ZONE_DIMENSION
        # 解析不出地域（随机地域）且没有可用区时 location_spec 保持缺省：
        # v2 的 bk_cloud_region 是必填字段，不能塞 "default" 这种假地域，
        # 整组不传等价于 v1 的「city 为空 = 不做位置过滤」

    if detail.get("current_hosts"):
        new_detail["current_hosts"] = _build_v2_current_hosts(detail["current_hosts"], index, group_mark)

    return new_detail


def build_v2_apply_params(params: Dict[str, Any]) -> Dict[str, Any]:
    """把内部申请参数转成 `/v2/resource/apply` 的入参

    只保留 v2 文档里声明的顶层字段，其余（如 dry_run）按需透传。
    """
    index = CloudZoneIndex()
    new_params = dict(params)
    new_params["details"] = [_build_v2_detail(detail, index) for detail in params.get("details") or []]
    return new_params


def _expand_zone_values_to_subzone_ids(values: Any, index: CloudZoneIndex, field: str) -> Tuple[List[str], bool]:
    """把位置列表里的可用区展开成它下面的园区 ID

    v1 的资源池只认园区 ID，而部署页已经改成选可用区，所以下发前要反向展开。
    - 数字（园区 ID）原样保留；
    - 可用区展开成若干园区 ID；
    - 展开不出来（园区表没登记）时保留原值，让 v1 依然报「资源不足」，而不是悄悄放宽成不限位置。
    """
    if not values:
        return [], False
    if isinstance(values, (str, int)):
        values = [values]

    result, changed, unresolved = [], False, []
    for value in values:
        text = str(value).strip()
        if not text:
            continue
        if text.isdigit():
            result.append(text)
            # 资源池按 []string 解析，园区 ID 是 int 时顺手转成字符串
            if not isinstance(value, str):
                changed = True
            continue
        zone = index.resolve_zone(text)
        subzone_ids = index.subzone_ids_of_zone(zone) if zone else []
        if subzone_ids:
            result.extend(subzone_ids)
            changed = True
        else:
            unresolved.append(text)
            result.append(text)
    if unresolved:
        logger.error(
            "resource apply(v1): cannot expand %s=%s to subzone ids, keep as is. "
            "check BKSubzone register for these zones",
            field,
            unresolved,
        )
    return _dedup(result), changed


def _to_v1_location_spec(location_spec: Dict[str, Any], index: CloudZoneIndex) -> Tuple[Dict[str, Any], bool]:
    """v1 位置参数归一化：可用区展开成园区 ID，缺城市时补逻辑城"""
    new_location_spec = dict(location_spec)
    changed = False

    # 先记下原始的位置值（可能是可用区字符串），展开后会被替换成园区 ID，
    # 后面补 city 还得靠它
    raw_zone_values = [
        value
        for value in (location_spec.get("bk_cloud_zone_list") or location_spec.get("sub_zone_ids") or [])
        if not str(value).strip().isdigit()
    ]

    # 前端如果直接用新字段 bk_cloud_zone_list，这里落到 v1 的 sub_zone_ids 上
    if location_spec.get("bk_cloud_zone_list"):
        new_location_spec["sub_zone_ids"] = list(location_spec["bk_cloud_zone_list"])
        new_location_spec.pop("bk_cloud_zone_list", None)
        changed = True

    include_field = "sub_zone_ids"
    if new_location_spec.get(include_field):
        subzone_ids, expanded = _expand_zone_values_to_subzone_ids(
            new_location_spec[include_field], index, include_field
        )
        if expanded:
            new_location_spec[include_field] = subzone_ids
            changed = True

    if location_spec.get("exclude_sub_zone_ids"):
        exclude_ids, expanded = _expand_zone_values_to_subzone_ids(
            location_spec["exclude_sub_zone_ids"], index, "exclude_sub_zone_ids"
        )
        if expanded:
            new_location_spec["exclude_sub_zone_ids"] = exclude_ids
            changed = True

    # 内部新增的可用区排除字段，v1 不认，转成 exclude_sub_zone_ids
    if location_spec.get("exclude_bk_cloud_zone_list"):
        exclude_ids, _ = _expand_zone_values_to_subzone_ids(
            location_spec["exclude_bk_cloud_zone_list"], index, "exclude_bk_cloud_zone_list"
        )
        if exclude_ids:
            merged = _dedup(list(new_location_spec.get("exclude_sub_zone_ids") or []) + exclude_ids)
            new_location_spec["exclude_sub_zone_ids"] = merged
            changed = True
        new_location_spec.pop("exclude_bk_cloud_zone_list", None)

    # v1 的 city 必填（服务端按逻辑城查 IDC 城市），只有可用区时用可用区反查逻辑城
    if not new_location_spec.get("city") and raw_zone_values:
        zones = [index.resolve_zone(value) for value in raw_zone_values]
        cities = _dedup([index.city_of_zone(zone) for zone in zones if zone])
        if len(cities) == 1:
            new_location_spec["city"] = cities[0]
            changed = True

    return new_location_spec, changed


def build_v1_apply_params(params: Dict[str, Any]) -> Dict[str, Any]:
    """v1 下发的入参

    部署页改成选可用区后，v1 的资源池服务只认园区 ID，这里做一次反向展开。
    没有可用区字符串（全是园区 ID 或没有位置条件）时原样返回，老链路请求体不变。
    """
    details = params.get("details") or []
    need_convert = any(
        (not str(value).strip().isdigit())
        for detail in details
        for field in ("sub_zone_ids", "bk_cloud_zone_list", "exclude_sub_zone_ids", "exclude_bk_cloud_zone_list")
        for value in (detail.get("location_spec") or {}).get(field) or []
    )
    need_city = any(
        (
            (detail.get("location_spec") or {}).get("sub_zone_ids")
            or (detail.get("location_spec") or {}).get("bk_cloud_zone_list")
        )
        and not (detail.get("location_spec") or {}).get("city")
        for detail in details
    )
    if not need_convert and not need_city:
        return params

    index = CloudZoneIndex()
    new_details = []
    for detail in details:
        location_spec = detail.get("location_spec")
        if not location_spec:
            new_details.append(detail)
            continue
        new_location_spec, changed = _to_v1_location_spec(location_spec, index)
        new_details.append({**detail, "location_spec": new_location_spec} if changed else detail)

    return {**params, "details": new_details}


def build_apply_request(params: Dict[str, Any]) -> Tuple[str, Dict[str, Any]]:
    """按开关返回 (协议版本, 实际下发参数)

    v1：可用区反展开成园区 ID（部署页改成选可用区后需要），没有可用区字符串时原样透传；
    v2：转成云地域 + 云可用区的新协议。
    """
    version = get_apply_api_version()
    if version == API_VERSION_V2:
        return version, build_v2_apply_params(params)
    return version, build_v1_apply_params(params)


def apply_resource(params: Dict[str, Any], raw: bool = True, **kwargs) -> Dict[str, Any]:
    """资源申请统一入口，按开关走 v1 / v2

    v2 需要 X-Request-ID，服务端拿不到请求号不会选机，这里固定生成一个。
    """
    version, payload = build_apply_request(params)
    if version == API_VERSION_V2:
        headers = {"X-Request-ID": (kwargs.pop("headers", None) or {}).get("X-Request-ID") or uuid.uuid4().hex}
        logger.info(
            "resource apply via v2, bill_id=%s task_id=%s groups=%s",
            payload.get("bill_id"),
            payload.get("task_id"),
            [_d.get("group_mark") for _d in payload.get("details") or []],
        )
        return DBResourceApi.resource_apply_v2(params=payload, raw=raw, headers=headers, **kwargs)
    return DBResourceApi.resource_apply(params=payload, raw=raw, **kwargs)


def expand_zone_subzone_ids(zones: List[str]) -> List[str]:
    """把云可用区展开成它下面登记过的园区 ID 列表

    资源池 `/resource/spec/sum` 目前只认 city + sub_zone_ids，所以按可用区统计时
    先用这个函数展开，再带上原来的 city 做统计。库存行的园区原值不会被改写。
    """
    if not zones:
        return []
    index = CloudZoneIndex()
    zone_set = set(zones)
    return [subzone_id for subzone_id, zone in index.zone_by_subzone_id.items() if zone in zone_set]
