# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.

资源申请协议适配（v2）

`POST /v2/resource/apply`：location_spec 用 `bk_cloud_region`（云地域）+ `bk_cloud_zone_list`（云可用区），
主维默认 `bk_cloud_zone`，跨可用区 / 指定可用区都按云可用区判定。

dbm-ui 内部的单据 details 和 builder 历史上有两种写法：
- 新协议：`bk_cloud_region` + `bk_cloud_zone_list`；
- 存量写法：`city`（逻辑城）+ `sub_zone_ids`（园区 ID 或可用区字符串）。

下发前统一归一化成 v2：数字园区 ID 用 `BKSubzone` 反查云可用区，可用区字符串直接使用。
`bk_cloud_region="default"` 表示部署时地域选了随机，按「不限地域」处理。
地域和可用区都拿不到时不传 location_spec（等价于不限位置），这是「随机」的合法表达；
但如果上游明确给了位置、只是解析不出来，会直接抛 `ResourceApplyException` 而不是悄悄降级成
「不限位置」——容灾场景下捞到别的可用区的机器，比单据失败更难收拾。
"""
import logging
import re
import uuid
from collections import defaultdict
from typing import Any, Dict, Iterable, List, Optional, Tuple

from django.utils.translation import gettext as _

from backend.components.dbresource.client import DBResourceApi
from backend.db_meta.models.city_map import BKSubzone
from backend.db_services.dbresource.exceptions import ResourceApplyException

logger = logging.getLogger("root")

# 部署时地域选「随机」存进集群的值，不是真实地域，申请时按「不限」处理
RANDOM_REGION = "default"

# 云可用区主维的取值，v2 显式传，避免服务端按老园区口径兜底
CLOUD_ZONE_DIMENSION = "bk_cloud_zone"

# 「跨可用区」语义的亲和性：count 为 1 时服务端会降级成 NONE，需要自己补可用区约束
CROSS_ZONE_AFFINITIES = {"CROS_SUBZONE", "CROSS_SUBZONE_STRONG", "CROSS_SUBZONE_WEAK"}

# 腾讯云地域形如 ap-chongqing / ap-nanjing / na-ashburn，
# 用于判断上游传的 city 是否已经是云地域（老前端传的是逻辑城名，如「南京」）
_CLOUD_REGION_PATTERN = re.compile(r"^[a-z]{2}-[a-z0-9-]+$")


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

        支持三种输入：云可用区字符串、园区 ID（数字或数字字符串）、园区名（含「南京-江宁」这种全称）。
        识别不出来的返回空串，由调用方决定是报错还是忽略，不再把原值当可用区透传给资源池。
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
        if text in self.zone_by_subzone_name:
            return self.zone_by_subzone_name[text]
        # 园区全称自带城市前缀（如「南京-江宁」），登记表里可能只记了「江宁」
        if "-" in text:
            return self.zone_by_subzone_name.get(text.split("-", 1)[1], "")
        return ""

    def zones_of_city(self, city: str) -> List[str]:
        return sorted(self.zones_by_city.get((city or "").strip(), set()))


def _dedup(values: Iterable[str]) -> List[str]:
    """去重并保持顺序"""
    return list(dict.fromkeys([value for value in values if value]))


def _resolve_cloud_zones(values: Any, index: CloudZoneIndex, field: str) -> List[str]:
    """把位置列表归一化成云可用区列表

    解析不出来的值直接抛错：位置条件被悄悄丢掉，会导致机器落在没被允许的可用区，
    比单据失败更难发现。
    """
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
        logger.error("resource apply: cannot resolve cloud zone for %s=%s", field, unresolved)
        raise ResourceApplyException(_("资源申请位置解析失败：{} 中的 {} 无法识别为云可用区，请检查园区与可用区的登记关系").format(field, unresolved))
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
    # 部署时地域选「随机」会存成 default，它不是真实地域，继续用可用区 / 城市推
    if region == RANDOM_REGION:
        region = ""
    if region:
        return region, "location_spec.bk_cloud_region"

    zone_regions = _dedup([index.region_by_zone.get(zone, "") for zone in zones])
    if len(zone_regions) == 1:
        return zone_regions[0], "cloud_zone"
    if len(zone_regions) > 1:
        logger.error("resource apply: selected cloud zones %s belong to multiple regions %s", zones, zone_regions)

    city = str(location_spec.get("city") or "").strip()
    if city and city != RANDOM_REGION:
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


def _build_v2_location_spec(location_spec: Dict[str, Any], index: CloudZoneIndex, group_mark: str) -> Dict[str, Any]:
    # 老协议用 include_or_exclue=False 表示「sub_zone_ids 是排除列表」，v2 有独立的排除字段
    is_exclude = location_spec.get("include_or_exclue") is False
    include_values = (
        [] if is_exclude else (location_spec.get("bk_cloud_zone_list") or location_spec.get("sub_zone_ids"))
    )
    zones = _resolve_cloud_zones(include_values, index, "bk_cloud_zone_list")
    region, region_source = _resolve_region(location_spec, index, zones)
    # v2 的 location_spec 里 bk_cloud_region 是必填；只有可用区、推不出地域时不能硬发，
    # 否则不是被服务端拒单，就是按错误的维度选机
    if zones and not region:
        logger.error(
            "resource apply: %s cloud zones %s have no cloud region, city=%s",
            group_mark,
            zones,
            location_spec.get("city"),
        )
        raise ResourceApplyException(_("资源申请位置解析失败：可用区 {} 查不到所属云地域，请检查可用区登记信息").format(zones))

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
        # 排除模式下，可用区列表可能放在新字段里（sqlserver_restore_slave 等已切到 bk_cloud_zone_list），
        # 也可能还是存量的 sub_zone_ids
        exclude_zones = _dedup(
            exclude_zones
            + _resolve_cloud_zones(
                location_spec.get("bk_cloud_zone_list") or location_spec.get("sub_zone_ids"),
                index,
                "exclude_bk_cloud_zone_list",
            )
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


def _enforce_single_host_cross_zone(
    new_detail: Dict[str, Any],
    affinity: str,
    group_mark: str,
) -> None:
    """单台申请时，把「跨可用区」落成显式的可用区排除条件

    v2 在 `count` 为 1 时会把 affinity 按 `NONE` 处理（`tolerance` 也不参与打散），
    这样「新从库要与主库不在同一可用区」（需求 §6）就没人保证了。
    这里按同组已有主机的情况补一条约束：
    - 已有主机分布在 2 个及以上可用区：随便落在哪都满足「至少分布在 2 个可用区」，不用干预；
    - 已有主机都在同一个可用区：显式排除这个可用区，强制新主机换区。
    """
    if affinity not in CROSS_ZONE_AFFINITIES:
        return
    try:
        count = int(new_detail.get("count") or 0)
    except (TypeError, ValueError):
        return
    if count != 1:
        return
    # 老园区口径的单据主维是 sub_zone，不能用可用区条件去约束
    dimension = new_detail.get("affinity_dimension") or CLOUD_ZONE_DIMENSION
    if dimension != CLOUD_ZONE_DIMENSION:
        return

    current_zones = {
        host.get("bk_cloud_zone") for host in (new_detail.get("current_hosts") or []) if host.get("bk_cloud_zone")
    }
    if len(current_zones) != 1:
        return
    occupied_zone = current_zones.pop()

    # 地域随机（没有 location_spec）时表达不了「排除某个可用区」，只能记日志放行
    if not new_detail.get("location_spec"):
        logger.warning(
            "resource apply: %s count=1 with affinity=%s but no location_spec, "
            "cannot keep the new host out of cloud zone %s",
            group_mark,
            affinity,
            occupied_zone,
        )
        return

    location_spec = new_detail["location_spec"]
    include_zones = list(location_spec.get("bk_cloud_zone_list") or [])
    if include_zones:
        # 排除条件优先于包含条件，同一个可用区不能既包含又排除
        remain_zones = [zone for zone in include_zones if zone != occupied_zone]
        if remain_zones:
            location_spec["bk_cloud_zone_list"] = remain_zones
        else:
            location_spec.pop("bk_cloud_zone_list", None)
    exclude_zones = list(location_spec.get("exclude_bk_cloud_zone_list") or [])
    if occupied_zone not in exclude_zones:
        exclude_zones.append(occupied_zone)
    location_spec["exclude_bk_cloud_zone_list"] = exclude_zones
    logger.info(
        "resource apply: %s count=1 with affinity=%s, exclude occupied cloud zone %s",
        group_mark,
        affinity,
        occupied_zone,
    )


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
        new_location_spec = _build_v2_location_spec(location_spec, index, group_mark)
        if new_location_spec:
            new_detail["location_spec"] = new_location_spec
            # 主维默认就是云可用区，上游显式指定 sub_zone 时保持原样（兼容老园区口径的单据）
            new_detail["affinity_dimension"] = detail.get("affinity_dimension") or CLOUD_ZONE_DIMENSION
        # 解析不出地域（随机地域）且没有可用区时 location_spec 保持缺省：
        # v2 的 bk_cloud_region 是必填字段，不能塞 "default" 这种假地域，
        # 整组不传等价于 v1 的「city 为空 = 不做位置过滤」

    if detail.get("current_hosts"):
        new_detail["current_hosts"] = _build_v2_current_hosts(detail["current_hosts"], index, group_mark)
        # count 为 1 时亲和性会被服务端降级，靠排除条件兜住「跨可用区」
        _enforce_single_host_cross_zone(new_detail, affinity, group_mark)

    return new_detail


def build_v2_apply_params(params: Dict[str, Any]) -> Dict[str, Any]:
    """把内部申请参数转成 `/v2/resource/apply` 的入参

    只保留 v2 文档里声明的顶层字段，其余（如 dry_run）按需透传。
    """
    index = CloudZoneIndex()
    new_params = dict(params)
    new_params["details"] = [_build_v2_detail(detail, index) for detail in params.get("details") or []]
    return new_params


def _build_request_id(payload: Dict[str, Any]) -> str:
    """生成 X-Request-ID

    v2 没有请求号不会选机，这里必须兜底。优先用单据号/任务号拼出来，
    排查时能直接从资源池日志对回 dbm 的单据；都没有才退化成随机值。
    """
    bill_id = str(payload.get("bill_id") or "").strip()
    task_id = str(payload.get("task_id") or "").strip()
    if bill_id and task_id:
        request_id = "dbm-{}-{}".format(bill_id, task_id)
    elif bill_id or task_id:
        request_id = "dbm-{}".format(bill_id or task_id)
    else:
        request_id = "dbm-{}".format(uuid.uuid4().hex)
    return request_id[:64]


def apply_resource(params: Dict[str, Any], raw: bool = True, **kwargs) -> Dict[str, Any]:
    """资源申请统一入口，只走 v2 协议

    v2 需要 X-Request-ID，服务端拿不到请求号不会选机，这里固定生成一个。
    """
    payload = build_v2_apply_params(params)
    headers = {"X-Request-ID": (kwargs.pop("headers", None) or {}).get("X-Request-ID") or _build_request_id(payload)}
    logger.info(
        "resource apply via v2, bill_id=%s task_id=%s request_id=%s groups=%s",
        payload.get("bill_id"),
        payload.get("task_id"),
        headers["X-Request-ID"],
        [_d.get("group_mark") for _d in payload.get("details") or []],
    )
    return DBResourceApi.resource_apply_v2(params=payload, raw=raw, headers=headers, **kwargs)


def expand_zone_subzone_ids(zones: List[str], index: Optional[CloudZoneIndex] = None) -> List[str]:
    """把云可用区展开成它下面登记过的园区 ID 列表

    资源池 `/resource/spec/sum` 目前只认 city + sub_zone_ids，所以按可用区统计时
    先用这个函数展开，再带上原来的 city 做统计。库存行的园区原值不会被改写。

    @param index: 可复用调用方的园区/可用区索引，批量统计时避免重复全表查询
    """
    if not zones:
        return []
    index = index or CloudZoneIndex()
    zone_set = set(zones)
    return sorted(subzone_id for subzone_id, zone in index.zone_by_subzone_id.items() if zone in zone_set)
