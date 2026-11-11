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

`POST /v2/resource/apply` 的位置参数由**请求级** `affinity_dimension` 决定，整单只能用一种模式。
dbm-ui 只用 cloud（`bk_cloud_zone`）模式：location_spec 只允许 `bk_cloud_region` /
`bk_cloud_zone_list` / `exclude_bk_cloud_zone_list`，选机主维是云可用区。

园区口径（`city` / `sub_zone_ids` / `exclude_sub_zone_ids` / `include_or_exclue`）已经下线：
上游只会传云地域 + 云可用区，出现老字段说明单据还是改造前的格式，直接报错而不是悄悄降级——
容灾场景下捞到别的可用区的机器，比单据失败更难收拾。

`bk_cloud_region="default"` 表示部署时地域选了随机，按「不限地域」处理。

`POST /resource/spec/sum` 的位置字段是**顶层**的 `bk_cloud_region` + `bk_cloud_zone_list`（数组 IN），
这个接口由资源池侧保证，仍然是叠加关系。
"""
import logging
import math
import uuid
from collections import Counter
from typing import Any, Dict, Iterable, List, Tuple

from django.utils.translation import gettext as _

from backend.components.dbresource.client import DBResourceApi
from backend.db_meta.models.city_map import RANDOM_REGION, BKSubzone
from backend.db_services.dbresource.exceptions import ResourceApplyException

logger = logging.getLogger("root")

# 云可用区主维的取值，v2 显式传，避免服务端按老园区口径兜底
CLOUD_ZONE_DIMENSION = "bk_cloud_zone"

# 「跨可用区」语义的亲和性：count 为 1 时服务端会降级成 NONE，需要自己补可用区约束
CROSS_ZONE_AFFINITIES = {"CROS_SUBZONE", "CROSS_SUBZONE_STRONG", "CROSS_SUBZONE_WEAK"}

# 「同位置」亲和性要求必须给云地域
SAME_LOCATION_AFFINITIES = {"SAME_SUBZONE", "SAME_SUBZONE_CROSS_SWTICH"}

# 亲和性要求的最少可用区数：
# count > 1 时用来校验指定的可用区列表，count == 1 时用来反推每个可用区的台数上限
MIN_ZONE_COUNT_BY_AFFINITY = {"CROS_SUBZONE": 2, "CROSS_SUBZONE_WEAK": 2, "CROSS_SUBZONE_STRONG": 3}

# 巡检里带 tolerance 比例规则的亲和性：强 ceil(n/3)、弱 ceil(n/2)。
# `CROS_SUBZONE` 巡检只看「>=2 个可用区」，没有比例上限，
# 不能拿 builders 传的 tolerance（如 mysql proxy 的 0.5）去收紧，否则比巡检还严。
TOLERANCE_CAPPED_AFFINITIES = {"CROSS_SUBZONE_STRONG", "CROSS_SUBZONE_WEAK"}


class CloudZoneIndex(object):
    """一次申请内的云可用区索引（可用区 -> 云地域），避免逐条查库

    只认登记过云可用区的值：园区 ID / 园区名属于 v1 口径，这里不再反查，
    出现了就由调用方报错，避免把园区 ID 当成可用区发给资源池。
    """

    def __init__(self):
        # bk_cloud_zone -> bk_cloud_region
        self.region_by_zone: Dict[str, str] = {}

        rows = BKSubzone.objects.values("bk_cloud_zone", "bk_cloud_region")
        for row in rows:
            zone = (row["bk_cloud_zone"] or "").strip()
            region = (row["bk_cloud_region"] or "").strip()
            if zone and region:
                self.region_by_zone.setdefault(zone, region)


def _dedup(values: Iterable[str]) -> List[str]:
    """去重并保持顺序"""
    return list(dict.fromkeys([value for value in values if value]))


def _resolve_cloud_zones(values: Any, index: CloudZoneIndex, field: str) -> List[str]:
    """把位置列表归一化成云可用区列表

    只接受登记过的云可用区。解析不出来的值直接抛错：位置条件被悄悄丢掉，
    会导致机器落在没被允许的可用区，比单据失败更难发现。
    """
    if not values:
        return []
    if isinstance(values, (str, int)):
        values = [values]
    zones, unresolved = [], []
    for value in values:
        zone = str(value).strip()
        if zone in index.region_by_zone:
            zones.append(zone)
        else:
            unresolved.append(zone)
    if unresolved:
        logger.error("resource apply: cannot resolve cloud zone for %s=%s", field, unresolved)
        raise ResourceApplyException(_("资源申请位置解析失败：{} 中的 {} 无法识别为云可用区，请检查园区与可用区的登记关系").format(field, unresolved))
    return _dedup(zones)


def _resolve_region(location_spec: Dict[str, Any], index: CloudZoneIndex, zones: List[str]) -> Tuple[str, str]:
    """解析云地域，返回 (region, region 来源)

    优先级：
    1. 上游显式给的 bk_cloud_region；
    2. 已选可用区所属的地域（可用区只属于一个地域，最权威）。

    不再从 city 反推：城市口径（逻辑城 / 把云地域塞在 city 里）已经在本次改造中下线，
    上游只会传 bk_cloud_region。
    """
    region = str(location_spec.get("bk_cloud_region") or "").strip()
    # 部署时地域选「随机」会存成 default，它不是真实地域，继续用可用区推
    if region == RANDOM_REGION:
        region = ""
    if region:
        return region, "location_spec.bk_cloud_region"

    zone_regions = _dedup([index.region_by_zone.get(zone, "") for zone in zones])
    if len(zone_regions) == 1:
        return zone_regions[0], "cloud_zone"
    if len(zone_regions) > 1:
        logger.error("resource apply: selected cloud zones %s belong to multiple regions %s", zones, zone_regions)

    return "", ""


# 已经下线的园区口径位置字段：出现即说明上游还在按 v1 拼参数，
# 静默丢弃会悄悄放宽容灾约束（单据照样成功），所以这里直接报错。
LEGACY_LOCATION_FIELDS = ("sub_zone_ids", "exclude_sub_zone_ids", "exclude_rack_ids", "exclude_net_device_ids")


def _reject_legacy_location_spec(location_spec: Dict[str, Any], group_mark: str) -> None:
    """申请参数里还带园区口径字段时直接报错

    `city="default"` 是存量单据里「地域随机」的哨兵值，本身不表达约束，忽略即可；
    `include_or_exclue=True` 等价于新口径的默认包含语义，也不拦。
    """
    legacy = [field for field in LEGACY_LOCATION_FIELDS if location_spec.get(field)]
    city = str(location_spec.get("city") or "").strip()
    if city and city != RANDOM_REGION:
        legacy.append("city")
    if location_spec.get("include_or_exclue") is False:
        legacy.append("include_or_exclue")
    if not legacy:
        return

    logger.error("resource apply: %s location_spec still contains legacy fields %s", group_mark, legacy)
    raise ResourceApplyException(_("资源申请参数仍在使用已下线的园区口径字段 {}，请按云地域 + 云可用区重新提单").format(legacy))


def _coerce_affinity(affinity: Any) -> str:
    """亲和性常量统一成字符串，v2 不会把 None 收成 NONE，需要自己兜底"""
    if affinity is None:
        return ""
    value = getattr(affinity, "value", affinity)
    value = str(value).strip()
    return value


def _build_v2_location_spec(location_spec: Dict[str, Any], index: CloudZoneIndex, group_mark: str) -> Dict[str, Any]:
    """v2 location_spec：只允许云口径字段

    只认 `bk_cloud_region` / `bk_cloud_zone_list` / `exclude_bk_cloud_zone_list`，
    园区口径字段由 `_reject_legacy_location_spec` 拦掉。
    """
    _reject_legacy_location_spec(location_spec, group_mark)

    zones = _resolve_cloud_zones(location_spec.get("bk_cloud_zone_list"), index, "bk_cloud_zone_list")
    region, region_source = _resolve_region(location_spec, index, zones)
    # 有可用区却推不出地域时不能硬发：不是被拒单，就是按错误维度选机
    if zones and not region:
        logger.error(
            "resource apply: %s cloud zones %s have no cloud region, region_source=%s",
            group_mark,
            zones,
            region_source,
        )
        raise ResourceApplyException(_("资源申请位置解析失败：可用区 {} 查不到所属云地域，请检查可用区登记信息").format(zones))

    new_location_spec: Dict[str, Any] = {}
    if region:
        new_location_spec["bk_cloud_region"] = region
    if zones:
        new_location_spec["bk_cloud_zone_list"] = zones

    exclude_zones = _resolve_cloud_zones(
        location_spec.get("exclude_bk_cloud_zone_list"), index, "exclude_bk_cloud_zone_list"
    )
    if exclude_zones:
        new_location_spec["exclude_bk_cloud_zone_list"] = exclude_zones

    if not new_location_spec:
        # 随机地域 / 无可用区：不传位置条件，等价于「不限地域、不限可用区」
        logger.info(
            "resource apply: %s has no usable location condition (region_source=%s), location_spec is omitted",
            group_mark,
            region_source,
        )
    return new_location_spec


def _build_v2_current_hosts(current_hosts: List[Dict[str, Any]], group_mark: str) -> List[Dict]:
    """current_hosts 只保留能给出 `bk_cloud_zone` 的主机

    不再从园区 ID 反查可用区：拿不到就直接把这台主机从亲和计算里剔掉，
    避免用推断出来的位置影响整单选机。
    """
    result, dropped = [], []
    for host in current_hosts or []:
        host = dict(host)
        zone = str(host.get("bk_cloud_zone") or "").strip()
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


def _zone_capacity(total: int, tolerance: float, min_zones: int, affinity: str = "") -> int:
    """每个可用区最多能放几台（口径与巡检 `check_affinity_rules` 一致）

    - 强/弱亲和 + 有 tolerance（mongodb 的 0.33 / 0.5）：上限 = ceil(total * tolerance)，
      对应巡检的 `max(zone_counter) > ceil(n / 3)` / `ceil(n / 2)`；
    - 其余情况（`CROS_SUBZONE`、没给 tolerance）：按亲和性要求的最少可用区数均分，
      上限 = ceil(total / min_zones)。巡检对 `CROS_SUBZONE` 只要求 >= 2 个可用区，
      所以这里不看 tolerance，避免比平台标准更严。
    """
    if total <= 0:
        return 1
    try:
        tolerance = float(tolerance or 0)
    except (TypeError, ValueError):
        tolerance = 0
    if tolerance > 0 and affinity in TOLERANCE_CAPPED_AFFINITIES:
        return max(1, math.ceil(total * tolerance))
    return max(1, math.ceil(total / max(min_zones, 1)))


def _enforce_single_host_cross_zone(new_detail: Dict[str, Any], affinity: str, group_mark: str) -> None:
    """某个 detail 只申请 1 台时，把「跨可用区」落成显式的可用区排除条件

    `count` 是这一组的申请台数，和单据类型无关：部署 / 扩容 / 替换 / 故障自愈
    都可能出现 `count == 1`。v2 在 `count` 为 1 时会把 affinity 按 `NONE` 处理
    （`tolerance` 也不参与打散），「新机器要和存量主机分散到不同可用区」
    （需求 §6）就没人保证了，这里按「最终分布要满足容灾要求」反推可用区约束：

    - 已有可用区里已经达到每区上限的（上限见 `_zone_capacity`）不能再放；
    - 已有可用区数还不够亲和性下限时，落在任何已有可用区都不会增加覆盖数，
      只能整组排除，逼新机器开新区（`CROS_SUBZONE` / `WEAK` 的单区排除是它的特例）；
    - 已有分布既够数、又都没到上限：放哪都合规，不干预。
    """
    if affinity not in CROSS_ZONE_AFFINITIES:
        return
    try:
        count = int(new_detail.get("count") or 0)
    except (TypeError, ValueError):
        return
    if count != 1:
        return

    zone_counter = Counter(
        host.get("bk_cloud_zone") for host in (new_detail.get("current_hosts") or []) if host.get("bk_cloud_zone")
    )
    if not zone_counter:
        return

    total = sum(zone_counter.values()) + count
    min_zones = MIN_ZONE_COUNT_BY_AFFINITY.get(affinity, 2)
    capacity = _zone_capacity(total, new_detail.get("tolerance"), min_zones, affinity)
    excluded_zones = {zone for zone, used in zone_counter.items() if used >= capacity}

    if len(zone_counter) < min_zones:
        # 还没有达到下限：只能开新区，否则覆盖数永远是 len(zone_counter)
        excluded_zones |= set(zone_counter)
        if len(zone_counter) + count < min_zones:
            logger.warning(
                "resource apply: %s affinity=%s needs at least %s cloud zones, only %s occupied, "
                "1 more host cannot fix it (best effort: force a new zone)",
                group_mark,
                affinity,
                min_zones,
                len(zone_counter),
            )

    if not excluded_zones:
        return

    # 地域随机（没有 location_spec）时表达不了「排除某个可用区」，只能记日志放行
    location_spec = new_detail.get("location_spec")
    if not location_spec:
        logger.warning(
            "resource apply: %s count=1 with affinity=%s but no location_spec, "
            "cannot keep the new host out of cloud zone %s",
            group_mark,
            affinity,
            sorted(excluded_zones),
        )
        return

    include_zones = list(location_spec.get("bk_cloud_zone_list") or [])
    if include_zones:
        # 排除条件优先于包含条件，同一个可用区不能既包含又排除
        remain_zones = [zone for zone in include_zones if zone not in excluded_zones]
        if remain_zones:
            location_spec["bk_cloud_zone_list"] = remain_zones
        else:
            # 勾选的可用区全被占满：为了容灾只能放宽成「同地域内排除已占用区」
            location_spec.pop("bk_cloud_zone_list", None)
            logger.warning(
                "resource apply: %s affinity=%s include zones %s are all at capacity, "
                "fallback to exclude-only within region %s",
                group_mark,
                affinity,
                include_zones,
                location_spec.get("bk_cloud_region"),
            )

    exclude_zones = list(location_spec.get("exclude_bk_cloud_zone_list") or [])
    for zone in sorted(excluded_zones):
        if zone not in exclude_zones:
            exclude_zones.append(zone)
    location_spec["exclude_bk_cloud_zone_list"] = exclude_zones
    logger.info(
        "resource apply: %s count=1 affinity=%s tolerance=%s capacity=%s, exclude cloud zones %s",
        group_mark,
        affinity,
        new_detail.get("tolerance"),
        capacity,
        exclude_zones,
    )


def _validate_cloud_zone_count(new_detail: Dict[str, Any], affinity: str, group_mark: str) -> None:
    """本地提前校验「指定可用区时的数量下限」

    服务端同样会拦，但本地拦下来能直接告诉提单人差什么，不用去翻资源池日志。
    只在显式给了可用区列表、且 count > 1 时校验（count=1 会被降级成 NONE，不适用）。
    """
    min_count = MIN_ZONE_COUNT_BY_AFFINITY.get(affinity)
    if not min_count:
        return
    try:
        count = int(new_detail.get("count") or 0)
    except (TypeError, ValueError):
        return
    if count <= 1:
        return
    zones = (new_detail.get("location_spec") or {}).get("bk_cloud_zone_list") or []
    if zones and len(zones) < min_count:
        raise ResourceApplyException(_("亲和性 {} 要求至少指定 {} 个可用区，当前只有 {}").format(affinity, min_count, len(zones)))


def _build_v2_detail(detail: Dict[str, Any], index: CloudZoneIndex) -> Dict[str, Any]:
    """单组申请参数从 v1 结构转成 v2 结构

    `affinity_dimension` 是请求级字段，detail 里不允许出现，这里顺手清掉。
    """
    group_mark = detail.get("group_mark", "")
    new_detail = dict(detail)
    new_detail.pop("affinity_dimension", None)
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
        # 解析不出地域（随机地域）且没有可用区时 location_spec 保持缺省：
        # 整组不传等价于「不限位置」，不能塞 "default" 这种假地域
        elif affinity in SAME_LOCATION_AFFINITIES:
            # SAME_* 要求非空 bk_cloud_region，本地给个可读的错误
            raise ResourceApplyException(_("亲和性 {} 要求指定地域，但申请参数里没有可用的云地域").format(affinity))

    if detail.get("current_hosts"):
        new_detail["current_hosts"] = _build_v2_current_hosts(detail["current_hosts"], group_mark)
        # count 为 1 时亲和性会被服务端降级，靠排除条件兜住「跨可用区」
        _enforce_single_host_cross_zone(new_detail, affinity, group_mark)

    _validate_cloud_zone_count(new_detail, affinity, group_mark)

    return new_detail


def build_v2_apply_params(params: Dict[str, Any]) -> Dict[str, Any]:
    """把内部申请参数转成 `/v2/resource/apply` 的入参

    只保留 v2 文档里声明的顶层字段，其余（如 dry_run）按需透传。
    `affinity_dimension` 整单一个值，放在请求顶层。
    """
    index = CloudZoneIndex()
    new_params = dict(params)
    # 位置模式整单统一一个值，放在请求顶层
    new_params["details"] = [_build_v2_detail(detail, index) for detail in params.get("details") or []]
    new_params["affinity_dimension"] = CLOUD_ZONE_DIMENSION
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


def normalize_location_zones(source: Dict[str, Any], strict: bool = True) -> List[str]:
    """把位置来源规范化成云可用区列表（ap-xxx-N）

    写集群元数据、资源申请都走这里，保证口径一致。只接受登记过的云可用区：
    园区 ID / 园区名属于已下线的 v1 口径，不再反查，出现即报错。

    兼容两套字段名：集群元数据用 `cloud_zone_list` / `zone_list`，
    location_spec 用 `bk_cloud_zone_list`。

    @param strict: 解析不出来时抛 ValueError。写元数据场景必须为 True，
        避免把园区 ID 之类写进 `Cluster.cloud_zone_list`。
    """
    source = source or {}
    values = source.get("cloud_zone_list") or source.get("bk_cloud_zone_list") or source.get("zone_list") or []
    if not values:
        return []

    index = CloudZoneIndex()
    zones, unresolved = [], []
    for value in values:
        zone = str(value).strip()
        if zone in index.region_by_zone:
            zones.append(zone)
        else:
            unresolved.append(zone)

    if unresolved and strict:
        raise ValueError(f"cannot resolve cloud zone for {unresolved}, check BKSubzone")

    return list(dict.fromkeys(zones))
