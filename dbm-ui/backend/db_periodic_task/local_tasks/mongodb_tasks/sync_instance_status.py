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
import time
import traceback
import uuid
from collections import defaultdict
from datetime import timedelta

from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist
from django.db.models import Q
from django.utils import timezone

from backend import env
from backend.components import BKMonitorV3Api
from backend.db_meta.enums import ClusterType
from backend.db_meta.enums.instance_status import MongoDBStorageInstanceStatus
from backend.db_meta.models import Cluster, MongoDBStorageInstanceExt, StorageInstance
from backend.db_periodic_task.local_tasks.db_meta.constants import UNIFY_QUERY_PARAMS
from backend.db_periodic_task.local_tasks.mongodb_tasks.report_op import RecordBatchOps, dev_debug
from backend.db_report.enums.mongodb_check_sub_type import StorageInstanceStatusCheckSubType
from backend.db_report.repo.task_record_repo import get_report_day_from_time
from backend.utils.redis import RedisConn

logger = logging.getLogger("root")

# Redis 锁：防止定时任务重复执行
SYNC_INSTANCE_STATUS_LOCK_KEY = "SyncStorageInstanceStatusTask:lock"
SYNC_INSTANCE_STATUS_LOCK_TIMEOUT = 300  # 5 分钟

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

    def start(self, report_day: int = None, batch_size: int = 20) -> None:
        """
        replicaset, sharded cluster 2种架构：
        1, list all cluster
        2, filter failed, write to db
        """
        # step0: 获取锁，防止重复执行（value 唯一，便于续期与安全释放）
        lock_value = str(uuid.uuid4())
        lock_acquired = RedisConn.set(
            SYNC_INSTANCE_STATUS_LOCK_KEY, lock_value, nx=True, ex=SYNC_INSTANCE_STATUS_LOCK_TIMEOUT
        )
        if not lock_acquired:
            logger.warning("SyncStorageInstanceStatusTask: failed to acquire lock, skip this round")
            return
        try:
            # step1: 填充Ext表
            self.fill_ext_table()

            if report_day is None:
                report_day = get_report_day_from_time(timezone.now())
            record_batch_ops = RecordBatchOps(self.check_type, report_day)
            deleted_count = record_batch_ops.delete_old_record(360)
            logger.info(
                f"SyncStorageInstanceStatusTask report_day: {report_day} "
                f"sub_type: {self.check_type} "
                f"deleted_count: {deleted_count}"
            )
            if not _renew_lock(SYNC_INSTANCE_STATUS_LOCK_KEY, lock_value):
                logger.warning(
                    "SyncStorageInstanceStatusTask: renew lock failed after step1, "
                    f"lock_key={SYNC_INSTANCE_STATUS_LOCK_KEY}, lock_value={lock_value[:8]}"
                )

            # step2: 从changes中查询最近2分钟有变化的instance，检查并更新.
            try:
                # 每2分钟执行一次，这里查询4分钟内的变化.避免漏掉.
                instance_list = self.fetch_latest_changes(minutes=4)
                logger.info(f"SyncStorageInstanceStatusTask fetch_latest_changes: {len(instance_list)} instances")
                # 状态变化 会在同一个shard的多个instance上同时变化，需要合并.
                # 所以这里以shard为单位，查询并合并状态变化.
                # 获得所有的cluster_domain和shard的组合
                shard_list = list(
                    set([instance["cluster_domain"] + ":" + instance["shard"] for instance in instance_list])
                )
                self.check_and_update_shards(shard_list)
            except Exception as e:
                logger.error(f"fetch_latest_changes error: {e}")

            if not _renew_lock(SYNC_INSTANCE_STATUS_LOCK_KEY, lock_value):
                logger.warning(
                    "SyncStorageInstanceStatusTask: renew lock failed after step2, "
                    f"lock_key={SYNC_INSTANCE_STATUS_LOCK_KEY}, lock_value={lock_value[:8]}"
                )

            # step3: 最近更新时间大于5分钟的PRIMARY，检查并更新.
            try:
                changed_instance_list = self.fetch_changed_instance_list()
                logger.info(
                    f"SyncStorageInstanceStatusTask fetch_changed_instance_list: {len(changed_instance_list)} instances"
                )
                self.check_and_update_instance(changed_instance_list)
            except Exception as e:
                traceback.print_exc()
                logger.error(f"fetch_changed_instance_list error: {e}")
        finally:
            _release_lock(SYNC_INSTANCE_STATUS_LOCK_KEY, lock_value)

    def check_and_update_shards(self, cluster_domain_shard_list: list):
        """
        以shard为单位，检查并更新 instance的ext表
        """
        for cluster_domain_shard in cluster_domain_shard_list:
            cluster_domain = cluster_domain_shard.split(":")[0]
            shard = cluster_domain_shard.split(":")[1]
            metric_val = _instant_fetch_metric(
                {
                    "shard": shard,
                    "cluster_domain": cluster_domain,
                }
            )
            if metric_val is None:
                logger.error(
                    f"_instant_fetch_metric error: metric_val is None for cluster_domain {cluster_domain} and shard {shard}"
                )
                continue
            # update ext table
            for item in metric_val:
                instance_ip = item["bk_target_ip"]
                instance_port = int(item["instance_port"])
                value = int(item["value"])
                try:
                    ext = MongoDBStorageInstanceExt.objects.get(
                        instance__machine__ip=instance_ip, instance__port=instance_port
                    )
                except ObjectDoesNotExist:
                    logger.warning(
                        f"missing MongoDBStorageInstanceExt for instance {instance_ip}:{instance_port}, skip"
                    )
                    continue
                except MultipleObjectsReturned:
                    logger.error(
                        f"multiple MongoDBStorageInstanceExt rows for instance {instance_ip}:{instance_port}, skip"
                    )
                    continue
                ext.update_at = timezone.now()
                status = MongoDBStorageInstanceStatus.get_status_by_value(value)
                ext.state_code = status.value
                ext.state = status.name
                ext.shard_name = item.get("shard", "")
                ext.save()
                logger.info(
                    f"update ext table: {ext.id} {ext.instance.id} "
                    f"{ext.priority} {ext.hidden} {ext.update_at} {ext.state} {ext.state_code}"
                )

    def check_and_update_instance(self, instance_list: list):
        """
        检查并更新cluster的状态
        """
        for one_instance in instance_list:
            addr = one_instance["instance"]
            if not is_valid_instance_addr(addr):
                logger.debug(f"addr must be ip:port, skip: {addr}")
                continue
            old_state_code = one_instance["old_state_code"]  # -1 or other status code
            new_state_code = one_instance["new_state_code"]  # -1 or other status code
            new_state = one_instance["new_state"]  # UNKNOWN or other status name
            new_shard_name = one_instance.get("new_shard_name", "")  # shard name
            if old_state_code == new_state_code:
                logger.debug(f"old_state_code == new_state_code, skip update for instance {addr}")
                continue
            # update ext table
            try:
                ext = MongoDBStorageInstanceExt.objects.get(
                    instance__machine__ip=addr.split(":")[0], instance__port=int(addr.split(":")[1])
                )
            except ObjectDoesNotExist:
                logger.warning(f"missing MongoDBStorageInstanceExt for instance {addr}, skip")
                continue
            except MultipleObjectsReturned:
                logger.error(f"multiple MongoDBStorageInstanceExt rows for instance {addr}, skip")
                continue
            ext.update_at = timezone.now()
            ext.state_code = new_state_code
            ext.state = new_state
            if new_shard_name is not None and new_shard_name != "":
                ext.shard_name = new_shard_name
            ext.save()
            logger.info(
                f"update ext table: {ext.id} {ext.instance.id} "
                f"{ext.priority} {ext.hidden} {ext.update_at} {ext.state} {ext.state_code}"
            )

    def fetch_changed_instance_list(self) -> list:
        """
        检查所有的PRIMARY的instance的状态，如果状态不为PRIMARY，则更新整个cluster_domain和shard的状态
        """
        query = Q(cluster_type__in=[ClusterType.MongoShardedCluster, ClusterType.MongoReplicaSet])
        mongo_storage_instance_ext_qs = MongoDBStorageInstanceExt.objects.filter(
            instance__cluster__in=Cluster.objects.filter(query), update_at__lt=timezone.now() - timedelta(seconds=200)
        ).exclude(state_code=MongoDBStorageInstanceStatus.SECONDARY.value)
        mongo_storage_instance_ext_count = mongo_storage_instance_ext_qs.count()
        logger.info(
            f"SyncStorageInstanceStatusTask mongo_storage_instance_ext_list: {mongo_storage_instance_ext_count} instances"
        )
        changed_instance_list = []
        addr_list = []
        fetch_metric_batch_size = 20
        current_state_code_dict = defaultdict(int)

        def flush_batch():
            nonlocal addr_list, current_state_code_dict
            metric_val = _instant_fetch_metric(
                {
                    "instance": addr_list,
                }
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
                            "new_shard_name": one_metric.get("shard", ""),
                        }
                    )
                metric_val_dict[one_metric["instance"]] = one_metric["value"]

            # 如果某个instance返回的内容为空，则认为该instance已经宕机，需要更新状态为UNAVAILABLE
            for one_addr in current_state_code_dict.keys():
                if one_addr not in metric_val_dict:
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
        logger.info(f"SyncStorageInstanceStatusTask changed_instance_list: {changed_instance_list}")
        return changed_instance_list

    def fill_ext_table(self):
        """
        填充Ext表
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

    def fetch_latest_changes(self, minutes: int = 4) -> list[dict]:
        """
        获取最近minutes分钟有变化的instance
        changes(bkmonitor:exporter_dbm_mongodb_exporter:mongodb_mongod_replset_my_state[4m]) > 0
        backup instance 的changes 不计算在内
        return list of instance
        """
        end_time = datetime.datetime.now(timezone.utc)
        start_time = end_time - datetime.timedelta(minutes=minutes)
        query_template = {
            "changes": (
                "changes("
                "bkmonitor:exporter_dbm_mongodb_exporter:mongodb_mongod_replset_my_state"
                f"{{instance_role!='backup'}}[{minutes}m]"
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
            instance = item["dimensions"]["instance"]
            ip_port = item["dimensions"]["bk_target_ip"] + ":" + str(item["dimensions"]["instance_port"])
            new_row = {
                "instance": instance,
                "ip_port": ip_port,
                "instance_role": item["dimensions"]["instance_role"],
                "instance_port": item["dimensions"]["instance_port"],
                "bk_target_ip": item["dimensions"]["bk_target_ip"],
                "cluster_domain": item["dimensions"]["cluster_domain"],
                "shard": item["dimensions"]["shard"],
                "value": value,
            }
            instance_list.append(new_row)
        return instance_list


def _instant_fetch_metric(condition: dict, retry_times: int = 3, sleep_time: int = 10):
    """
    查询mongodb_replset_my_state metric, condition 支持 cluster_domain, shard, instance, instance_host
    return [] or None(error)
    """
    logger.info("_instant_fetch_metric condition : {} ".format(condition))
    query_template = {
        "replset_my_state": """avg by (cluster_domain,instance_port,instance_role,instance,bk_target_ip) (
            bkmonitor:exporter_dbm_mongodb_exporter:mongodb_mongod_replset_my_state{condition_str_all}
            )""",
    }
    condition_strs = []
    for cond_key in condition.keys():
        if cond_key not in ["cluster_domain", "shard", "instance", "instance_host", "bk_target_ip", "instance_role"]:
            raise ValueError(f"condition {cond_key} is invalid")
        condition_str = ""
        v = condition[cond_key]
        if isinstance(v, list):
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
            logger.error("query metric error: {}".format(e))
            if i < retry_times - 1:
                time.sleep(sleep_time)
                continue
            else:
                logger.error("query metric error: retry_times is reached")
                return None
    for item in series:
        value = _extract_datapoint_value(item)
        if value is None:
            logger.warning(f"_instant_fetch_metric: empty datapoints, skip item: {item.get('dimensions', {})}")
            continue
        logger.info("item: {}".format(item))
        ip_port = item["dimensions"]["bk_target_ip"] + ":" + str(item["dimensions"]["instance_port"])
        logger.info("ip_port: {}".format(ip_port))
        metric_result.append(
            {
                "instance": ip_port,
                "instance_role": item["dimensions"]["instance_role"],
                "instance_port": item["dimensions"]["instance_port"],
                "bk_target_ip": item["dimensions"]["bk_target_ip"],
                "cluster_domain": item["dimensions"]["cluster_domain"],
                "shard": item["dimensions"]["shard"],
                "value": value,
            }
        )
    return metric_result
