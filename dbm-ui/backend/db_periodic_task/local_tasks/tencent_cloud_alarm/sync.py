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
import json
import logging
import os
import re
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from django.core.cache import cache

from backend.bk_web import constants
from backend.components.bkmonitorv3.client import BKMonitorV3EventApi
from backend.configuration.constants import SystemSettingsEnum
from backend.configuration.models import SystemSettings
from backend.db_meta.models.app import AppCache
from backend.db_meta.models.cluster_entry import CLBEntryDetail
from backend.db_monitor.constants import MonitorEventType
from backend.db_monitor.dataclass import BaseEventBody, MonitorEvent
from backend.db_monitor.models.tencent_cloud_alarm import TencentCloudAlarmRecord

from .client import (
    CLB_NAMESPACE,
    DEFAULT_DOMAIN,
    REDIS_NAMESPACE,
    TencentCloudCredential,
    fetch_alarm_histories,
    fetch_redis_tags,
)

logger = logging.getLogger("celery")
_missing_credential_logged = False

TZ = timezone(timedelta(hours=8))
OVERLAP_SECONDS = 180
INITIAL_LOOKBACK_SECONDS = 24 * 60 * 60
EVENT_BATCH = 50
LOCK_KEY = "tencent_cloud_alarm_sync_lock"
LOCK_TIMEOUT = 30 * 60
FIELD_SPLIT = re.compile(r"\s*\|\s*")
KEY_VALUE = re.compile(r"^\s*([^:：]+)\s*[:：]\s*(.*)$")
IP_PORT = re.compile(r"^(\d{1,3}(?:\.\d{1,3}){3})(?::(\d+))?$")
INLINE_TAG = re.compile(r"\(([^()]*)\)")
PRODUCT_CLB = "clb"
PRODUCT_REDIS = "redis"
SYNC_PRODUCTS = (
    (CLB_NAMESPACE, PRODUCT_CLB),
    (REDIS_NAMESPACE, PRODUCT_REDIS),
)


def resolve_start(watermark, now):
    if watermark <= 0:
        return now - INITIAL_LOOKBACK_SECONDS
    return max(watermark - OVERLAP_SECONDS, 0)


def clean(value):
    return str(value or "").replace("\t", " ").replace("\r", " ").replace("\n", " ").strip()


def parse_address(ip_port, vip):
    matched = IP_PORT.match((ip_port or "").strip())
    if matched:
        ip_address, port = matched.group(1), matched.group(2)
        if port and port != "0":
            return "{}:{}".format(ip_address, port)
        return ip_address
    return (vip or "").strip()


def parse_instance(alarm_object, dimensions=""):
    fields = {}
    for part in FIELD_SPLIT.split(alarm_object or ""):
        matched = KEY_VALUE.match(part)
        if not matched:
            continue
        key = re.sub(r"\s+", "", matched.group(1)).lower()
        fields[key] = matched.group(2).strip()
    instance_id = fields.get("id") or fields.get("instanceid") or ""
    instance_name = fields.get("instancename") or fields.get("name") or ""
    address = parse_address(fields.get("ipport", ""), fields.get("vip", ""))
    extra = _load_dimensions(dimensions)
    instance_id = instance_id or str(extra.get("instanceid") or extra.get("InstanceId") or "")
    if not address:
        address = str(extra.get("vip") or extra.get("Vip") or "")
    return {"实例ID": instance_id, "实例名称": instance_name, "实例地址": address}


def _load_dimensions(dimensions):
    if isinstance(dimensions, dict):
        return dimensions
    if not dimensions:
        return {}
    try:
        extra = json.loads(dimensions)
    except (TypeError, ValueError):
        return {}
    return extra if isinstance(extra, dict) else {}


def parse_inline_tags(text):
    if "对象标签" not in (text or ""):
        return []
    section = text.split("对象标签", 1)[1]
    tags = []
    for item in INLINE_TAG.findall(section):
        item = item.strip()
        if not item:
            continue
        if "_" in item:
            key, value = item.split("_", 1)
            tags.append({"键": key, "值": value})
        else:
            tags.append({"键": item, "值": ""})
    return tags


# 腾讯云 AlarmLevel：Remind、Warn 都进预警，Serious 进致命。
_ALARM_LEVEL = {
    "remind": "warning",
    "warn": "warning",
    "serious": "critical",
}


def alarm_level_of(raw):
    """把原始 AlarmLevel 转成策略使用的 alarm_level。"""
    text = clean(raw).lower()
    return _ALARM_LEVEL.get(text, text)


def to_record(item):
    occurred = datetime.fromtimestamp(int(item.get("FirstOccurTime") or 0), TZ)
    record = {
        "时间": occurred.strftime("%Y-%m-%d %H:%M:%S"),
        "产品": item.get("_product") or PRODUCT_CLB,
        "告警类型": clean(item.get("AlarmType")),
        "状态": clean(item.get("AlarmStatus")),
        "地域": clean(item.get("Region")),
        "策略": clean(item.get("PolicyName")),
        "timestamp_ms": int(item.get("FirstOccurTime") or 0) * 1000,
    }
    record.update(parse_instance(item.get("AlarmObject") or "", item.get("Dimensions") or ""))
    record["标签"] = parse_inline_tags(item.get("AlarmObject") or "")
    record["内容"] = clean(item.get("Content"))
    record["级别"] = alarm_level_of(item.get("AlarmLevel"))
    record["告警ID"] = clean(item.get("AlarmId"))
    record["对象"] = clean(item.get("AlarmObject"))
    return record


def vip_of(address):
    address = (address or "").strip()
    if ":" in address:
        return address.split(":", 1)[0]
    return address


def cluster_by_vip(vips):
    if not vips:
        return {}
    details = CLBEntryDetail.objects.filter(clb_ip__in=list(vips)).select_related("entry__cluster")
    found = {}
    for detail in details:
        if not detail.entry_id:
            continue
        found[detail.clb_ip] = detail.entry.cluster
    biz_ids = [cluster.bk_biz_id for cluster in found.values() if cluster.bk_biz_id]
    abbrs = AppCache.batch_get_app_attr(biz_ids) if biz_ids else {}
    for cluster in found.values():
        cluster.db_app_abbr = abbrs.get(cluster.bk_biz_id, "") or ""
    return found


def _setting_text(configured, key):
    if not isinstance(configured, dict):
        return ""
    return str(configured.get(key) or "").strip()


def _monitor_env(name):
    """云监控专用账号，避免和以后别的腾讯云应用共用 TENCENTCLOUD_*。"""
    return os.environ.get("DBM_TENCENTCLOUD_MONITOR_{}".format(name), "").strip()


def load_credentials():
    configured = SystemSettings.get_setting_value(SystemSettingsEnum.TENCENT_CLOUD_MONITOR.value, default={}) or {}
    secret_id = _monitor_env("SECRET_ID") or _setting_text(configured, "secret_id")
    secret_key = _monitor_env("SECRET_KEY") or _setting_text(configured, "secret_key")
    if not secret_id or not secret_key:
        return None
    token = _monitor_env("TOKEN") or _setting_text(configured, "token")
    region = _monitor_env("REGION") or _setting_text(configured, "region") or "ap-guangzhou"
    domain = _monitor_env("DOMAIN") or _setting_text(configured, "domain") or DEFAULT_DOMAIN
    return TencentCloudCredential(
        secret_id=secret_id, secret_key=secret_key, token=token, region=region, domain=domain
    )


def load_state():
    state = SystemSettings.get_setting_value(SystemSettingsEnum.TENCENT_CLOUD_ALARM_SYNC.value, default={}) or {}
    if not isinstance(state, dict):
        state = {}
    try:
        watermark = int(state.get("watermark") or 0)
    except (TypeError, ValueError):
        watermark = 0
    return {"watermark": watermark}


def save_state(state):
    SystemSettings.insert_setting_value(
        key=SystemSettingsEnum.TENCENT_CLOUD_ALARM_SYNC.value,
        value={"watermark": int(state["watermark"])},
        value_type="dict",
        user="system",
    )


def _clip(value, limit):
    return clean(value)[:limit]


def build_event(record, cluster):
    content = "{content}\n实例: {name} {address}\n地域: {region} 策略: {policy} 状态: {status}".format(
        content=record["内容"],
        name=record["实例名称"],
        address=record["实例地址"],
        region=record["地域"],
        policy=record["策略"],
        status=record["状态"],
    )
    tags = record.get("标签") or []
    if tags:
        content += "\n标签: " + ",".join("{}={}".format(item.get("键", ""), item.get("值", "")) for item in tags)
    dimension = {
        "alarm_id": record["告警ID"],
        "alarm_status": record["状态"],
        "alarm_type": record["告警类型"],
        "region": record["地域"],
        "policy_name": record["策略"][:128],
        "instance_name": record["实例名称"][:128],
        "vip": record["实例地址"][:128],
        "alarm_content": record["内容"][:256],
        "alarm_level": record.get("级别") or "",
        "app": record.get("app") or "",
        "appid": 0,
        "bk_target_cloud_id": 0,
        "cluster_domain": "",
        "cluster_type": "",
    }
    if cluster is not None:
        dimension["appid"] = cluster.bk_biz_id
        dimension["cluster_domain"] = cluster.immute_domain
        dimension["cluster_type"] = cluster.cluster_type
    target = record["实例地址"] or record["实例名称"] or "tencentyun-lb"
    return MonitorEvent(
        event_name=MonitorEventType.TENCENT_LB_ALARM,
        target=target,
        event=BaseEventBody(content=content),
        dimension=dimension,
        timestamp=record["timestamp_ms"],
    )


def _new_records(histories, seen):
    records = []
    for item in histories:
        record = to_record(item)
        alarm_id = record["告警ID"]
        if not alarm_id or alarm_id in seen:
            continue
        seen.add(alarm_id)
        records.append(record)
    return records


def existing_alarm_ids(alarm_ids):
    if not alarm_ids:
        return set()
    return set(TencentCloudAlarmRecord.objects.filter(alarm_id__in=list(alarm_ids)).values_list("alarm_id", flat=True))


def build_row(record, cluster):
    """未匹配到平台 CLB 时 cluster_id 为 0，后续不会上报事件。"""
    occurred = datetime.fromtimestamp(int(record.get("timestamp_ms") or 0) / 1000, TZ)
    tags = record.get("标签") or []
    if not isinstance(tags, list):
        tags = []
    return TencentCloudAlarmRecord(
        creator="system",
        updater="system",
        alarm_id=_clip(record.get("告警ID"), constants.LEN_MIDDLE),
        product=_clip(record.get("产品") or PRODUCT_CLB, constants.LEN_SHORT),
        occurred_at=occurred,
        alarm_type=_clip(record.get("告警类型"), constants.LEN_SHORT),
        alarm_status=_clip(record.get("状态"), constants.LEN_SHORT),
        alarm_level=_clip(record.get("级别"), constants.LEN_SHORT),
        region=_clip(record.get("地域"), constants.LEN_NORMAL),
        policy_name=_clip(record.get("策略"), constants.LEN_LONG),
        instance_id=_clip(record.get("实例ID"), constants.LEN_MIDDLE),
        instance_name=_clip(record.get("实例名称"), constants.LEN_LONG),
        address=_clip(record.get("实例地址"), constants.LEN_MIDDLE),
        content=record.get("内容") or "",
        alarm_object=record.get("对象") or "",
        tags=tags,
        bk_biz_id=cluster.bk_biz_id if cluster is not None else 0,
        app=_clip(getattr(cluster, "db_app_abbr", "") if cluster is not None else "", constants.LEN_MIDDLE),
        cluster_id=cluster.id if cluster is not None else 0,
        cluster_domain=_clip(cluster.immute_domain if cluster is not None else "", constants.LEN_LONG),
        cluster_type=_clip(cluster.cluster_type if cluster is not None else "", constants.LEN_NORMAL),
        event_sent=False,
    )


def persist_rows(rows):
    if rows:
        TencentCloudAlarmRecord.objects.bulk_create(rows, ignore_conflicts=True)


def load_unsent_rows(exclude):
    queryset = TencentCloudAlarmRecord.objects.filter(event_sent=False, product=PRODUCT_CLB).exclude(cluster_id=0)
    if exclude:
        queryset = queryset.exclude(alarm_id__in=list(exclude))
    return list(queryset)


def mark_event_sent(alarm_ids):
    if not alarm_ids:
        return
    TencentCloudAlarmRecord.objects.filter(alarm_id__in=list(alarm_ids)).update(event_sent=True, updater="system")


def event_from_row(row):
    record = {
        "内容": row.content,
        "实例名称": row.instance_name,
        "实例地址": row.address,
        "地域": row.region,
        "策略": row.policy_name,
        "状态": row.alarm_status,
        "标签": row.tags or [],
        "告警ID": row.alarm_id,
        "告警类型": row.alarm_type,
        "级别": row.alarm_level or "",
        "app": row.app or "",
        "timestamp_ms": int(row.occurred_at.timestamp() * 1000),
    }
    cluster = SimpleNamespace(bk_biz_id=row.bk_biz_id, immute_domain=row.cluster_domain, cluster_type=row.cluster_type)
    return build_event(record, cluster)


def _publish_events(rows):
    for offset in range(0, len(rows), EVENT_BATCH):
        batch = rows[offset : offset + EVENT_BATCH]
        BKMonitorV3EventApi.send_event([event_from_row(row) for row in batch])
        mark_event_sent([row.alarm_id for row in batch])


def attach_redis_tags(credential, records):
    """Redis 告警没有内联标签时补查实例标签。查询失败只记日志，不中断同步。"""
    grouped = {}
    for record in records:
        if record.get("产品") != PRODUCT_REDIS or record.get("标签"):
            record.setdefault("标签", [])
            continue
        instance_id = record.get("实例ID") or ""
        region = record.get("地域") or ""
        if not instance_id or not region:
            record["标签"] = []
            continue
        grouped.setdefault(region, {}).setdefault(instance_id, []).append(record)
    for region, resources in grouped.items():
        try:
            tags = fetch_redis_tags(credential, region, list(resources))
        except (OSError, RuntimeError, ValueError) as exc:
            logger.warning("腾讯云 Redis 标签查询失败 %s: %s", region, exc)
            continue
        for instance_id, owners in resources.items():
            for record in owners:
                record["标签"] = tags.get(instance_id, [])


def collect_histories(credential, start, end):
    """按产品拉取告警。任一命名空间失败时保留已成功的记录，并标记本轮不能推进水位。"""
    histories = []
    failed = False
    for namespace, product in SYNC_PRODUCTS:
        batch, error = fetch_alarm_histories(credential, namespace, start, end)
        if error:
            failed = True
            logger.error(
                "腾讯云告警同步失败 product=%s %s..%s: %s %s",
                product,
                start,
                end,
                error.get("Code"),
                error.get("Message"),
            )
            continue
        for item in batch:
            item["_product"] = product
        histories.extend(batch)
    return histories, failed


def sync_tencent_cloud_alarms(now=None):
    """同步腾讯云负载均衡和 Redis 告警。全部入库；只有对上平台 CLB VIP 的才上报事件。"""
    global _missing_credential_logged
    credential = load_credentials()
    if credential is None:
        if not _missing_credential_logged:
            logger.warning("腾讯云告警同步跳过: 未配置 DBM_TENCENTCLOUD_MONITOR_SECRET_ID / DBM_TENCENTCLOUD_MONITOR_SECRET_KEY")
            _missing_credential_logged = True
        return 0
    current = int(now if now is not None else datetime.now(tz=timezone.utc).timestamp())
    state = load_state()
    start = resolve_start(state["watermark"], current)
    histories, failed = collect_histories(credential, start, current)
    if failed and not histories:
        return 0
    fetched_ids = [clean(item.get("AlarmId")) for item in histories]
    records = _new_records(histories, existing_alarm_ids([alarm_id for alarm_id in fetched_ids if alarm_id]))
    attach_redis_tags(credential, records)
    clb_vips = {
        vip_of(record["实例地址"]) for record in records if record.get("产品") == PRODUCT_CLB and vip_of(record["实例地址"])
    }
    clusters = cluster_by_vip(clb_vips)
    rows = []
    for record in records:
        cluster = None
        if record.get("产品") == PRODUCT_CLB:
            cluster = clusters.get(vip_of(record["实例地址"]))
        rows.append(build_row(record, cluster))
    persist_rows(rows)
    pending = [row for row in rows if row.product == PRODUCT_CLB and row.cluster_id]
    pending.extend(load_unsent_rows({row.alarm_id for row in rows}))
    if pending:
        _publish_events(pending)
    if not failed:
        state["watermark"] = current
        save_state(state)
    logger.info(
        "腾讯云告警同步完成: fetched=%s stored=%s events=%s failed=%s",
        len(histories),
        len(rows),
        len(pending),
        failed,
    )
    return len(rows)


def sync_tencent_cloud_alarms_guarded():
    """上一次同步还没结束时，本次直接返回，不叠着再跑一轮。"""
    if not cache.add(LOCK_KEY, 1, timeout=LOCK_TIMEOUT):
        logger.info("sync_tencent_cloud_alarm skipped, previous run still active")
        return
    try:
        sync_tencent_cloud_alarms()
    finally:
        cache.delete(LOCK_KEY)
