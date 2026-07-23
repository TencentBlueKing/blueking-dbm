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
import copy
import datetime
import logging
import re
import time
import traceback
import uuid
from collections import defaultdict
from datetime import timedelta

from django.db.models import Q
from django.utils import timezone

from backend import env
from backend.components import BKMonitorV3Api
from backend.db_meta.enums import ClusterType
from backend.db_meta.enums.instance_status import MongoDBStorageInstanceStatus
from backend.db_meta.models import Cluster, MongoDBStorageInstanceExt, StorageInstance
from backend.db_periodic_task.local_tasks.db_meta.constants import UNIFY_QUERY_PARAMS
from backend.db_periodic_task.local_tasks.mongodb_tasks.report_op import RecordBatchOps, dev_debug
from backend.db_report.enums import ReportStateType
from backend.db_report.enums.mongodb_check_sub_type import StorageInstanceStatusCheckSubType
from backend.db_report.models.monogdb_check_report import MongodbBackupCheckReport
from backend.db_report.repo.task_record_repo import get_report_day_from_time
from backend.utils.redis import RedisConn

logger = logging.getLogger("celery")

# Redis 锁：防止定时任务重复执行
SYNC_INSTANCE_STATUS_LOCK_KEY = "SyncStorageInstanceStatusTask:lock"
SYNC_INSTANCE_STATUS_LOCK_TIMEOUT = 300  # 5 分钟
SYNC_INSTANCE_STATUS_INIT_EXT_TABLE_FLAG_KEY = "SyncStorageInstanceStatusTask:init_ext_table:done"
SYNC_INSTANCE_STATUS_DELETE_OLD_RECORD_FLAG_KEY = "SyncStorageInstanceStatusTask:delete_old_record:last_day"
DEFAULT_FETCH_METRIC_BATCH_SIZE = 50
SHARD_METRIC_BATCH_SIZE = 30
EXT_IP_PORT_QUERY_BATCH_SIZE = 200
EXT_BULK_UPDATE_FIELDS = ["update_at", "state_code", "state", "shard_name"]
ABNORMAL_STATE_CODES = frozenset(
    {
        MongoDBStorageInstanceStatus.DOWN.value,
        MongoDBStorageInstanceStatus.FATAL.value,
        MongoDBStorageInstanceStatus.UNKNOWN.value,
        MongoDBStorageInstanceStatus.REMOVED.value,
    }
)

# Lua: 仅当 value 匹配时续期，避免误续其他实例的锁
REDIS_LOCK_RENEW_LUA = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("expire", KEYS[1], ARGV[2])
else
    return 0
end
"""
# Lua: 仅当 value 匹配时删除，避免先结束的任务误删后启动任务的锁
REDIS_LOCK_RELEASE_LUA = """
if redis.call("get", KEYS[1]) == ARGV[1] then
    return redis.call("del", KEYS[1])
else
    return 0
end
"""


def _renew_lock(key: str, lock_value: str, timeout: int = SYNC_INSTANCE_STATUS_LOCK_TIMEOUT) -> bool:
    """续期锁，仅当当前实例仍持有锁时有效。返回是否续期成功。"""
    script = RedisConn.register_script(REDIS_LOCK_RENEW_LUA)
    return script(keys=[key], args=[lock_value, timeout])


def _release_lock(key: str, lock_value: str) -> bool:
    """释放锁，仅当 value 匹配时删除，避免误删其他实例的锁。返回是否释放成功。"""
    script = RedisConn.register_script(REDIS_LOCK_RELEASE_LUA)
    return script(keys=[key], args=[lock_value])


def is_valid_instance_addr(addr: str) -> bool:
    """
    检查 addr 是否为 ip:port 格式
    """
    if not addr or ":" not in addr:
        return False
    parts = addr.split(":", 1)
    if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
        return False
    try:
        int(parts[1])
        return True
    except (ValueError, TypeError):
        return False


def _extract_datapoint_value(item: dict):
    """从监控返回中提取 datapoints[0][0]，若缺失返回 None。"""
    datapoints = item.get("datapoints") or []
    if not datapoints or not isinstance(datapoints[0], (list, tuple)) or len(datapoints[0]) == 0:
        return None
    return datapoints[0][0]


def _parse_instance_addr(addr: str) -> tuple[str, int] | None:
    if not is_valid_instance_addr(addr):
        return None
    ip, port_str = addr.split(":", 1)
    return ip, int(port_str)


def _instance_addr_key(ip: str, port: int) -> str:
    return f"{ip}:{port}"


def _group_shards_by_cluster(cluster_domain_shard_list: list) -> dict[str, list[str]]:
    grouped = defaultdict(list)
    for cluster_domain_shard in cluster_domain_shard_list:
        cluster_domain, shard = cluster_domain_shard.split(":", 1)
        if shard not in grouped[cluster_domain]:
            grouped[cluster_domain].append(shard)
    return grouped


def _chunk_list(items: list, chunk_size: int) -> list[list]:
    if chunk_size <= 0:
        return [items]
    return [items[i : i + chunk_size] for i in range(0, len(items), chunk_size)]


def _load_ext_map_by_ip_ports(ip_ports: list[tuple[str, int]]) -> dict[str, MongoDBStorageInstanceExt]:
    """
    按 (ip, port) 批量加载 Ext。

    返回的 ext 已 `select_related(instance__machine)` + `prefetch_related(instance__cluster)`。
    调用方后续应复用该 map，避免再走未 prefetch 的查询路径（例如 `_make_change_report` 里的
    `ext.instance.cluster.first()` 依赖本函数的 prefetch cache）。
    """
    if not ip_ports:
        return {}

    # OR(Q) 过长可能触达 DB 限制；分批查询后合并。
    ext_map = {}
    for chunk in _chunk_list(ip_ports, EXT_IP_PORT_QUERY_BATCH_SIZE):
        query = Q()
        for ip, port in chunk:
            query |= Q(instance__machine__ip=ip, instance__port=port)

        # cluster is M2M on StorageInstance — use prefetch_related, not select_related
        for ext in (
            MongoDBStorageInstanceExt.objects.filter(query)
            .select_related("instance__machine")
            .prefetch_related("instance__cluster")
        ):
            key = _instance_addr_key(ext.instance.machine.ip, ext.instance.port)
            if key in ext_map:
                logger.error(f"multiple MongoDBStorageInstanceExt rows for instance {key}, skip duplicates")
                continue
            ext_map[key] = ext
    return ext_map


def _bulk_update_ext_records(ext_records: list[MongoDBStorageInstanceExt]) -> int:
    if not ext_records:
        return 0
    MongoDBStorageInstanceExt.objects.bulk_update(ext_records, EXT_BULK_UPDATE_FIELDS, batch_size=500)
    return len(ext_records)


def _resolve_report_state(new_state_code: int) -> tuple[str, bool]:
    if new_state_code in ABNORMAL_STATE_CODES:
        return ReportStateType.ABNORMAL.value, False
    if new_state_code == MongoDBStorageInstanceStatus.PRIMARY.value:
        return ReportStateType.WARNING.value, False
    return ReportStateType.NORMAL.value, True


def _make_change_report(
    ext: MongoDBStorageInstanceExt,
    *,
    report_day: int,
    sub_type: str,
    shard: str,
    old_state: str,
    old_state_code: int,
    new_state: str,
    new_state_code: int,
) -> MongodbBackupCheckReport | None:
    # StorageInstance.cluster is M2M; Mongo instances normally belong to one cluster.
    # 依赖 `_load_ext_map_by_ip_ports` 的 prefetch_related("instance__cluster")，避免循环内 N+1。
    cluster = ext.instance.cluster.first()
    if cluster is None:
        logger.warning(
            "missing cluster for instance %s, skip change report",
            _instance_addr_key(ext.instance.machine.ip, ext.instance.port),
        )
        return None
    report_state, status = _resolve_report_state(new_state_code)
    return MongodbBackupCheckReport(
        creator="",
        subtype=sub_type,
        report_day=report_day,
        bk_biz_id=cluster.bk_biz_id,
        bk_cloud_id=cluster.bk_cloud_id,
        cluster=cluster.immute_domain,
        cluster_id=cluster.id,
        cluster_type=cluster.cluster_type,
        shard=shard or ext.shard_name or "",
        instance=_instance_addr_key(ext.instance.machine.ip, ext.instance.port),
        status=status,
        state=report_state,
        msg=f"{old_state}({old_state_code}) -> {new_state}({new_state_code})",
    )


class SyncStorageInstanceStatusTask:
    """同步storage实例的status到db_meta表中"""

    """和巡检任务类似，但执行的频率更高，每2分钟执行一次，要注意不要重复执行"""
    """ # step0: 获得锁，防止重复执行
        # step1: 填充Ext表, 优先级为100.
        # step2: 根据changes(mongodb_mystate)，查到最近2分钟有变化的instance，优先更新
        # step2: 最近更新时间大于5分钟的PRIMARY，检查并更新.
        # step3: 更新的记录写到mongodb巡检表. """

    check_type: str

    def __init__(self):
        self.check_type = StorageInstanceStatusCheckSubType.SyncStatus.value

    def start(
        self,
        report_day: int = None,
        batch_size: int = DEFAULT_FETCH_METRIC_BATCH_SIZE,
        cluster_domain: str | None = None,
        bk_biz_id: int | None = None,
        acquire_lock: bool = True,
    ) -> None:
        """
        replicaset, sharded cluster 2种架构：
        1, list all cluster
        2, filter failed, write to db

        作用域（互斥，由调用方保证）：
        - 全量：cluster_domain / bk_biz_id 均为空
        - 单集群：cluster_domain
        - 单业务：bk_biz_id
        acquire_lock: 是否抢全局 Redis 锁
        """
        if cluster_domain and bk_biz_id is not None:
            raise ValueError("cluster_domain and bk_biz_id are mutually exclusive")

        scoped = bool(cluster_domain) or bk_biz_id is not None
        # step0: 获取锁，防止重复执行（value 唯一，便于续期与安全释放）
        lock_value = None
        if acquire_lock:
            lock_value = str(uuid.uuid4())
            lock_acquired = RedisConn.set(
                SYNC_INSTANCE_STATUS_LOCK_KEY, lock_value, nx=True, ex=SYNC_INSTANCE_STATUS_LOCK_TIMEOUT
            )
            if not lock_acquired:
                logger.warning("SyncStorageInstanceStatusTask: failed to acquire lock, skip this round")
                return
        try:
            # 全量任务才做 Ext 初始化 / 旧巡检清理；按集群/业务入口避免副作用
            if not scoped:
                if RedisConn.exists(SYNC_INSTANCE_STATUS_INIT_EXT_TABLE_FLAG_KEY):
                    dev_debug("SyncStorageInstanceStatusTask init_ext_table already done, skip")
                else:
                    logger.info("SyncStorageInstanceStatusTask init_ext_table")
                    self.init_ext_table()
                    # 设置标志位，防止重复初始化. 初始化操作只需要执行一次. 不需要设置过期时间.
                    # 如果有特殊情况需要重新初始化，可以手动删除标志位
                    RedisConn.set(SYNC_INSTANCE_STATUS_INIT_EXT_TABLE_FLAG_KEY, "1")

            if report_day is None:
                report_day = get_report_day_from_time(timezone.now())
            record_batch_ops = RecordBatchOps(self.check_type, report_day)
            deleted_count = 0
            if not scoped:
                last_delete_day = RedisConn.get(SYNC_INSTANCE_STATUS_DELETE_OLD_RECORD_FLAG_KEY)
                if last_delete_day != str(report_day):
                    deleted_count = record_batch_ops.delete_old_record(360)
                    RedisConn.set(SYNC_INSTANCE_STATUS_DELETE_OLD_RECORD_FLAG_KEY, str(report_day))
            dev_debug(
                "SyncStorageInstanceStatusTask report_day: {} sub_type: {} "
                "cluster_domain: {} bk_biz_id: {} deleted_count: {}".format(
                    report_day,
                    self.check_type,
                    cluster_domain or "-",
                    bk_biz_id if bk_biz_id is not None else "-",
                    deleted_count,
                )
            )
            if lock_value and not _renew_lock(SYNC_INSTANCE_STATUS_LOCK_KEY, lock_value):
                logger.warning(
                    "SyncStorageInstanceStatusTask: renew lock failed after step1, "
                    f"lock_key={SYNC_INSTANCE_STATUS_LOCK_KEY}, lock_value={lock_value[:8]}"
                )

            # step2: 从changes中查询最近有变化的instance，检查并更新.
            try:
                # 每2分钟执行一次，这里查询4分钟内的变化.避免漏掉.
                instance_list = self.fetch_latest_changes(
                    minutes=4, cluster_domain=cluster_domain, bk_biz_id=bk_biz_id
                )
                dev_debug(f"SyncStorageInstanceStatusTask fetch_latest_changes: {len(instance_list)} instances")
                # 状态变化 会在同一个shard的多个instance上同时变化，需要合并.
                # 所以这里以shard为单位，查询并合并状态变化.
                # 获得所有的cluster_domain和shard的组合
                shard_list = list(
                    set([instance["cluster_domain"] + ":" + instance["shard"] for instance in instance_list])
                )
                # 限定范围手工执行：即使近期无 changes，也按作用域拉全量指标刷新
                if scoped and not shard_list:
                    shard_list = self._list_shard_keys_for_scope(cluster_domain=cluster_domain, bk_biz_id=bk_biz_id)
                self.check_and_update_shards(shard_list, record_batch_ops, report_day)
            except Exception as e:
                logger.error(f"fetch_latest_changes error: {e}")

            if lock_value and not _renew_lock(SYNC_INSTANCE_STATUS_LOCK_KEY, lock_value):
                logger.warning(
                    "SyncStorageInstanceStatusTask: renew lock failed after step2, "
                    f"lock_key={SYNC_INSTANCE_STATUS_LOCK_KEY}, lock_value={lock_value[:8]}"
                )

            # step3: 最近更新时间大于5分钟的PRIMARY，检查并更新.
            # 限定范围时忽略 update_at 门槛，强制核对该范围内非 SECONDARY 实例.
            try:
                changed_instance_list = self.fetch_changed_instance_list(
                    batch_size=batch_size,
                    cluster_domain=cluster_domain,
                    bk_biz_id=bk_biz_id,
                    ignore_update_at=scoped,
                )
                dev_debug(
                    f"SyncStorageInstanceStatusTask fetch_changed_instance_list: {len(changed_instance_list)} instances"
                )
                self.check_and_update_instance(changed_instance_list, record_batch_ops, report_day)
            except Exception as e:
                traceback.print_exc()
                logger.error(f"fetch_changed_instance_list error: {e}")

            record_batch_ops.bulk_create()
        finally:
            if lock_value:
                _release_lock(SYNC_INSTANCE_STATUS_LOCK_KEY, lock_value)

    def _mongo_cluster_domains(self, bk_biz_id: int | None = None) -> list[str]:
        qs = Cluster.objects.filter(
            cluster_type__in=[ClusterType.MongoShardedCluster, ClusterType.MongoReplicaSet],
        )
        if bk_biz_id is not None:
            qs = qs.filter(bk_biz_id=bk_biz_id)
        return list(qs.values_list("immute_domain", flat=True))

    def _list_shard_keys_for_scope(self, cluster_domain: str | None = None, bk_biz_id: int | None = None) -> list[str]:
        """按作用域列出 cluster_domain:shard。"""
        if cluster_domain:
            domains = [cluster_domain]
        elif bk_biz_id is not None:
            domains = self._mongo_cluster_domains(bk_biz_id=bk_biz_id)
        else:
            return []

        shard_keys: list[str] = []
        for domain in domains:
            shard_keys.extend(self._list_shard_keys_for_cluster(domain))
        return shard_keys

    def _list_shard_keys_for_cluster(self, cluster_domain: str) -> list[str]:
        """从监控拉该集群现有 shard，返回 cluster_domain:shard 列表。"""
        metric_val = _instant_fetch_metric({"cluster_domain": cluster_domain})
        if not metric_val:
            logger.warning(
                "SyncStorageInstanceStatusTask: no metric series for cluster_domain=%s",
                cluster_domain,
            )
            return []
        shard_keys = set()
        for item in metric_val:
            shard = (item.get("shard") or "").strip()
            domain = (item.get("cluster_domain") or "").strip()
            if shard and domain:
                shard_keys.add(f"{domain}:{shard}")
        return list(shard_keys)

    def check_and_update_shards(
        self, cluster_domain_shard_list: list, record_batch_ops: RecordBatchOps, report_day: int
    ):
        """
        以shard为单位，检查并更新 instance的ext表
        """
        shards_by_cluster = _group_shards_by_cluster(cluster_domain_shard_list)
        for cluster_domain, shard_list in shards_by_cluster.items():
            for shard_batch in _chunk_list(shard_list, SHARD_METRIC_BATCH_SIZE):
                metric_val = _instant_fetch_metric(
                    {
                        "shard": shard_batch,
                        "cluster_domain": cluster_domain,
                    }
                )
                if metric_val is None:
                    logger.error(
                        "_instant_fetch_metric error: metric_val is None for cluster_domain %s shards %s",
                        cluster_domain,
                        shard_batch,
                    )
                    continue

                ip_ports = [(item["bk_target_ip"], int(item["instance_port"])) for item in metric_val]
                ext_map = _load_ext_map_by_ip_ports(ip_ports)
                now = timezone.now()
                ext_updates = []
                for item in metric_val:
                    instance_ip = item["bk_target_ip"]
                    instance_port = int(item["instance_port"])
                    addr_key = _instance_addr_key(instance_ip, instance_port)
                    ext = ext_map.get(addr_key)
                    if ext is None:
                        logger.warning(
                            "missing MongoDBStorageInstanceExt for instance %s, skip",
                            addr_key,
                        )
                        continue
                    value = int(item["value"])
                    if ext.state_code == value:
                        continue
                    old_state = ext.state
                    old_state_code = ext.state_code
                    status = MongoDBStorageInstanceStatus.get_status_by_value(value)
                    report = _make_change_report(
                        ext,
                        report_day=report_day,
                        sub_type=self.check_type,
                        shard=item.get("shard", ""),
                        old_state=old_state,
                        old_state_code=old_state_code,
                        new_state=status.name,
                        new_state_code=status.value,
                    )
                    if report is not None:
                        record_batch_ops.append(report)
                    ext.update_at = now
                    ext.state_code = status.value
                    ext.state = status.name
                    ext.shard_name = item.get("shard", "")
                    ext_updates.append(ext)

                updated_count = _bulk_update_ext_records(ext_updates)
                dev_debug(
                    "check_and_update_shards updated {} ext rows for cluster_domain={} shards={}".format(
                        updated_count,
                        cluster_domain,
                        shard_batch,
                    )
                )

    def check_and_update_instance(self, instance_list: list, record_batch_ops: RecordBatchOps, report_day: int):
        """
        检查并更新cluster的状态
        """
        pending_updates = []
        for one_instance in instance_list:
            addr = one_instance["instance"]
            parsed = _parse_instance_addr(addr)
            if parsed is None:
                dev_debug(f"addr must be ip:port, skip: {addr}")
                continue
            old_state_code = one_instance["old_state_code"]
            new_state_code = one_instance["new_state_code"]
            new_state = one_instance["new_state"]
            new_shard_name = one_instance.get("new_shard_name", "")
            if old_state_code == new_state_code:
                dev_debug(f"old_state_code == new_state_code, skip update for instance {addr}")
                continue
            pending_updates.append((parsed, new_state_code, new_state, new_shard_name))

        if not pending_updates:
            return

        ext_map = _load_ext_map_by_ip_ports([parsed for parsed, _, _, _ in pending_updates])
        now = timezone.now()
        ext_updates = []
        for (ip, port), new_state_code, new_state, new_shard_name in pending_updates:
            addr_key = _instance_addr_key(ip, port)
            ext = ext_map.get(addr_key)
            if ext is None:
                logger.warning(f"missing MongoDBStorageInstanceExt for instance {addr_key}, skip")
                continue
            if ext.state_code == new_state_code:
                continue
            old_state = ext.state
            old_state_code = ext.state_code
            report = _make_change_report(
                ext,
                report_day=report_day,
                sub_type=self.check_type,
                shard=new_shard_name or ext.shard_name or "",
                old_state=old_state,
                old_state_code=old_state_code,
                new_state=new_state,
                new_state_code=new_state_code,
            )
            if report is not None:
                record_batch_ops.append(report)
            ext.update_at = now
            ext.state_code = new_state_code
            ext.state = new_state
            if new_shard_name is not None and new_shard_name != "":
                ext.shard_name = new_shard_name
            ext_updates.append(ext)

        updated_count = _bulk_update_ext_records(ext_updates)
        dev_debug(f"check_and_update_instance updated {updated_count} ext rows")

    def fetch_changed_instance_list(
        self,
        batch_size: int = DEFAULT_FETCH_METRIC_BATCH_SIZE,
        cluster_domain: str | None = None,
        bk_biz_id: int | None = None,
        ignore_update_at: bool = False,
    ) -> list:
        """
        检查所有的PRIMARY的instance的状态，如果状态不为PRIMARY，则更新整个cluster_domain和shard的状态
        """
        filters = {
            "instance__cluster__cluster_type__in": [
                ClusterType.MongoShardedCluster,
                ClusterType.MongoReplicaSet,
            ],
        }
        if cluster_domain:
            filters["instance__cluster__immute_domain"] = cluster_domain
        if bk_biz_id is not None:
            filters["instance__cluster__bk_biz_id"] = bk_biz_id
        if not ignore_update_at:
            filters["update_at__lt"] = timezone.now() - timedelta(seconds=200)

        # Filter via M2M instance__cluster may duplicate rows — distinct() is required.
        mongo_storage_instance_ext_qs = (
            MongoDBStorageInstanceExt.objects.filter(**filters)
            .exclude(state_code=MongoDBStorageInstanceStatus.SECONDARY.value)
            .select_related("instance__machine")
            .distinct()
        )
        mongo_storage_instance_ext_count = mongo_storage_instance_ext_qs.count()
        dev_debug(
            f"SyncStorageInstanceStatusTask mongo_storage_instance_ext_list: {mongo_storage_instance_ext_count} instances"
        )
        changed_instance_list = []
        addr_list = []
        fetch_metric_batch_size = batch_size
        current_state_code_dict = defaultdict(int)

        def flush_batch():
            nonlocal addr_list, current_state_code_dict
            skipped_empty_shard = set()
            metric_condition = {"instance": addr_list}
            if cluster_domain:
                metric_condition["cluster_domain"] = cluster_domain
            metric_val = _instant_fetch_metric(
                metric_condition,
                collect_skipped_empty_shard=skipped_empty_shard,
            )
            if metric_val is None:
                logger.error(f"fetch_metric error: metric_val is None for instance {addr_list}")
                return

            # 检查状态是否变化
            metric_val_dict = defaultdict(int)
            for one_metric in metric_val:
                if one_metric["value"] != current_state_code_dict[one_metric["instance"]]:
                    changed_instance_list.append(
                        {
                            "instance": one_metric["instance"],
                            "old_state_code": current_state_code_dict[one_metric["instance"]],
                            "new_state_code": one_metric["value"],
                            "new_state": MongoDBStorageInstanceStatus.get_status_by_value(one_metric["value"]).name,
                            "new_shard_name": one_metric["shard"],
                        }
                    )
                metric_val_dict[one_metric["instance"]] = one_metric["value"]

            # 如果某个instance返回的内容为空，则认为该instance已经宕机，需要更新状态为UNAVAILABLE
            for one_addr in current_state_code_dict.keys():
                if one_addr not in metric_val_dict:
                    if one_addr in skipped_empty_shard:
                        logger.warning(
                            f"fetch_metric: instance {one_addr} has empty shard in monitor series, "
                            "skip UNKNOWN state update for this round"
                        )
                        continue
                    changed_instance_list.append(
                        {
                            "instance": one_addr,
                            "old_state_code": current_state_code_dict[one_addr],
                            "new_state_code": MongoDBStorageInstanceStatus.UNKNOWN.value,
                            "new_state": MongoDBStorageInstanceStatus.UNKNOWN.name,
                            "new_shard_name": None,
                        }
                    )

            # 清空缓存列表和状态字典
            addr_list = []
            current_state_code_dict = defaultdict(int)

        for ext in mongo_storage_instance_ext_qs.iterator(chunk_size=500):
            addr = ext.instance.machine.ip + ":" + str(ext.instance.port)
            addr_list.append(addr)
            current_state_code_dict[addr] = ext.state_code
            # 批处理
            if len(addr_list) >= fetch_metric_batch_size:
                flush_batch()
        if addr_list:
            flush_batch()
        dev_debug(f"SyncStorageInstanceStatusTask changed_instance_list count: {len(changed_instance_list)}")
        return changed_instance_list

    def init_ext_table(self):
        """
        初始化Ext表
        """
        # fetch all instance from db_meta.StorageInstance and without ext
        instance_qs = StorageInstance.objects.filter(
            cluster_type__in=[ClusterType.MongoShardedCluster, ClusterType.MongoReplicaSet]
        ).filter(mongodbstorageinstanceext__isnull=True)
        # 关联 db_meta_nosqlstoragesetdtl 表，获取 shard name

        # 关联 db_meta_mongodbstoragesetdtl 表，获取 shard name

        instance_count = instance_qs.count()
        logger.info(f"fill_ext_table: {instance_count} instances")
        if instance_count == 0:
            return
        for instance in instance_qs.iterator(chunk_size=500):
            try:
                # fetch instance status from bkmonitor
                ext = MongoDBStorageInstanceExt.objects.create(
                    instance=instance,
                    priority=-1,  # 优先级最低
                    hidden=0,
                    update_at=timezone.now(),
                    state=MongoDBStorageInstanceStatus.UNKNOWN.name,
                    state_code=MongoDBStorageInstanceStatus.UNKNOWN.value,
                    shard_name="",  # shard name is empty
                )
                logger.info(
                    f"fill_ext_table: {ext.id} {ext.instance.id} "
                    f"{ext.priority} {ext.hidden} {ext.update_at} {ext.state} {ext.state_code}"
                )
            except Exception as e:
                logger.error(f"fill_ext_table error: {e} for instance {instance.machine.ip}:{instance.port}")

    def fetch_latest_changes(
        self, minutes: int = 4, cluster_domain: str | None = None, bk_biz_id: int | None = None
    ) -> list[dict]:
        """
        获取最近minutes分钟有变化的instance
        changes(bkmonitor:exporter_dbm_mongodb_exporter:mongodb_mongod_replset_my_state[4m]) > 0
        backup instance 的changes 不计算在内
        return list of instance
        """
        allowed_domains = None
        if bk_biz_id is not None:
            allowed_domains = set(self._mongo_cluster_domains(bk_biz_id=bk_biz_id))
            if not allowed_domains:
                return []

        end_time = datetime.datetime.now(timezone.utc)
        start_time = end_time - datetime.timedelta(minutes=minutes)
        label_filters = ["instance_role!='backup'"]
        if cluster_domain:
            # PromQL label matcher; cluster_domain 来自命令行/元数据，不含引号
            safe_domain = cluster_domain.replace("\\", "\\\\").replace('"', '\\"')
            label_filters.append(f'cluster_domain="{safe_domain}"')
        label_selector = "{" + ",".join(label_filters) + "}"
        query_template = {
            "changes": (
                "changes("
                "bkmonitor:exporter_dbm_mongodb_exporter:mongodb_mongod_replset_my_state"
                f"{label_selector}[{minutes}m]"
                ") > 0"
            ),
        }
        params = copy.deepcopy(UNIFY_QUERY_PARAMS)
        params["bk_biz_id"] = env.DBA_APP_BK_BIZ_ID
        params["start_time"] = int(start_time.timestamp())
        params["end_time"] = int(end_time.timestamp())
        params["query_configs"][0]["promql"] = query_template["changes"]
        dev_debug("params: {}".format(params["query_configs"][0]["promql"]))
        out = BKMonitorV3Api.unify_query(params, use_admin=True)
        series = out["series"]
        instance_list: list[dict] = []
        for item in series:
            value = _extract_datapoint_value(item)
            if value is None:
                logger.warning(f"fetch_latest_changes: empty datapoints, skip item: {item.get('dimensions', {})}")
                continue
            dims = item["dimensions"]
            shard = (dims.get("shard") or "").strip()
            if not shard:
                logger.warning(f"fetch_latest_changes: missing or empty shard in dimensions, skip item: {dims}")
                continue
            domain = dims["cluster_domain"]
            if cluster_domain and domain != cluster_domain:
                continue
            if allowed_domains is not None and domain not in allowed_domains:
                continue
            instance = dims["instance"]
            ip_port = dims["bk_target_ip"] + ":" + str(dims["instance_port"])
            new_row = {
                "instance": instance,
                "ip_port": ip_port,
                "instance_role": dims["instance_role"],
                "instance_port": dims["instance_port"],
                "bk_target_ip": dims["bk_target_ip"],
                "cluster_domain": domain,
                "shard": shard,
                "value": value,
            }
            instance_list.append(new_row)
        return instance_list


def _instant_fetch_metric(
    condition: dict, retry_times: int = 3, sleep_time: int = 10, collect_skipped_empty_shard: set | None = None
):
    """
    查询mongodb_replset_my_state metric, condition 支持 cluster_domain, shard, instance, instance_host
    return [] or None(error)
    若某条 series 的 shard 缺失或为空则跳过该条；collect_skipped_empty_shard 若传入，会记录对应 instance（ip:port）。
    """
    query_template = {
        # Include `shard` in `avg by` so BK-Monitor series dimensions still expose it (otherwise it is dropped).
        "replset_my_state": """avg by (cluster_domain,shard,instance_port,instance_role,instance,bk_target_ip) (
            bkmonitor:exporter_dbm_mongodb_exporter:mongodb_mongod_replset_my_state{condition_str_all}
            )""",
    }
    condition_strs = []
    for cond_key in condition.keys():
        if cond_key not in ["cluster_domain", "shard", "instance", "instance_host", "bk_target_ip", "instance_role"]:
            raise ValueError(f"condition {cond_key} is invalid")
        condition_str = ""
        v = condition[cond_key]
        if cond_key == "instance":
            if isinstance(v, list):
                v = [instance.replace(":", "-") if isinstance(instance, str) else instance for instance in v]
            elif isinstance(v, str):
                v = v.replace(":", "-")

        if isinstance(v, list):
            if cond_key == "instance":
                # instance is queried with regex selector, escape all regex metacharacters to avoid over-matching.
                # NOTE: PromQL label value is a quoted string. Backslashes for regex must be double-escaped.
                v = [re.escape(item).replace("\\", "\\\\") if isinstance(item, str) else item for item in v]
            v = "^(" + "|".join(v) + ")$"
            condition_str = f'{cond_key}=~"{v}"'
        else:
            condition_str = f'{cond_key}="{v}"'

        condition_strs.append(condition_str)

    condition_str_all = "{" + ",".join(condition_strs) + "}"
    # last data of 5m ago to now
    end_time = datetime.datetime.now(timezone.utc)
    start_time = end_time - datetime.timedelta(minutes=5)
    params = copy.deepcopy(UNIFY_QUERY_PARAMS)
    params["bk_biz_id"] = env.DBA_APP_BK_BIZ_ID
    params["start_time"] = int(start_time.timestamp())
    params["end_time"] = int(end_time.timestamp())
    dev_debug("condition_str_all: {}".format(condition_str_all))
    params["query_configs"][0]["promql"] = query_template["replset_my_state"].format(
        condition_str_all=condition_str_all
    )
    dev_debug("params: {}".format(params["query_configs"][0]["promql"]))

    metric_result = list()
    series = []
    for i in range(retry_times):
        try:
            out = BKMonitorV3Api.unify_query(params, use_admin=True)
            series = out["series"]
            break
        except Exception as e:
            if i < retry_times - 1:
                dev_debug(f"query metric error (retry {i + 1}/{retry_times}): {e}")
                time.sleep(sleep_time)
                continue
            logger.error("query metric error: retry_times is reached, last_error=%s", e)
            return None

    skipped_empty_datapoints = 0
    skipped_empty_shard = 0
    for item in series:
        value = _extract_datapoint_value(item)
        if value is None:
            skipped_empty_datapoints += 1
            continue
        dims = item["dimensions"]
        ip_port = dims["bk_target_ip"] + ":" + str(dims["instance_port"])
        shard = (dims.get("shard") or "").strip()
        if not shard:
            skipped_empty_shard += 1
            if collect_skipped_empty_shard is not None:
                collect_skipped_empty_shard.add(ip_port)
            continue
        metric_result.append(
            {
                "instance": ip_port,
                "instance_role": dims["instance_role"],
                "instance_port": dims["instance_port"],
                "bk_target_ip": dims["bk_target_ip"],
                "cluster_domain": dims["cluster_domain"],
                "shard": shard,
                "value": value,
            }
        )

    if skipped_empty_datapoints or skipped_empty_shard:
        dev_debug(
            "_instant_fetch_metric skipped: empty_datapoints={} empty_shard={} parsed={} condition={}".format(
                skipped_empty_datapoints,
                skipped_empty_shard,
                len(metric_result),
                condition,
            )
        )
    return metric_result
