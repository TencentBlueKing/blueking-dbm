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
import math
import random
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from blueapps.core.celery.celery import app
from celery.schedules import crontab
from django.utils import timezone

from backend.components.mysql_partition.client import DBPartitionApi
from backend.db_meta.enums.cluster_type import ClusterType
from backend.db_periodic_task.local_tasks import register_periodic_task
from backend.db_periodic_task.local_tasks.mysql_partition.execute_partition_task import (
    execute_tendbcluster_partition_task,
    execute_tendbha_partition_task,
)
from backend.db_periodic_task.local_tasks.mysql_partition.get_partition_conf import (
    get_exec_domain_info,
    get_partition_by_config_id,
)
from backend.db_periodic_task.local_tasks.mysql_partition.mysql_check_partition_v2 import (
    BIZ_PAGE_SIZE,
    CONFIG_ID_PAGE_SIZE,
    _chunked,
    _classify_config_ids,
    _fetch_execution_sets_for_config_ids,
    _iter_biz_config_ids,
    _iter_check_biz,
)

logger = logging.getLogger("flow")

GROUP_SIZE = 100
WAVE_SIZE = 10
HA_GROUP_INTERVAL_SECONDS = 50
SCHEDULE_WINDOW_SECONDS = 3500
MIN_WAVE_INTERVAL_SECONDS = 30
CONF_QUERY_SIZE = 100

MODE_HA_SERIAL = "ha_serial"
MODE_WAVE = "wave"


class ClusterRetryClock:
    """
    单个集群的重试执行时钟。

    随机秒数只加在当前组的 eta 上，不累进时钟，避免后面的组被越推越远。
    """

    def __init__(self, start: datetime, mode: str, interval_seconds: int):
        self.start = start
        self.mode = mode
        self.interval_seconds = interval_seconds
        self.scheduled = 0

    def next_eta(self) -> Tuple[datetime, int]:
        seq = self.scheduled
        if self.mode == MODE_HA_SERIAL:
            base_seconds = seq * HA_GROUP_INTERVAL_SECONDS
            jitter = random.randint(1, 10)
        else:
            base_seconds = (seq // WAVE_SIZE) * self.interval_seconds
            jitter = random.randint(5, 10)
        self.scheduled += 1
        return self.start + timedelta(seconds=base_seconds + jitter), seq


def build_cluster_clock(
    cluster_id: int, cluster_type: str, conf_cnt: Optional[int], start: datetime
) -> ClusterRetryClock:
    """按集群配置总量决定间隔。找不到 conf_cnt 时退到 30 秒一波。"""
    if not conf_cnt:
        logger.warning(
            "分区重试集群缺少 conf_cnt，按 %s 秒波次间隔排期 cluster_type=%s cluster_id=%s",
            MIN_WAVE_INTERVAL_SECONDS,
            cluster_type,
            cluster_id,
        )
        return ClusterRetryClock(start, MODE_WAVE, MIN_WAVE_INTERVAL_SECONDS)

    group_cnt = math.ceil(conf_cnt / GROUP_SIZE)
    if cluster_type == ClusterType.TenDBHA.value and group_cnt * HA_GROUP_INTERVAL_SECONDS <= SCHEDULE_WINDOW_SECONDS:
        clock = ClusterRetryClock(start, MODE_HA_SERIAL, HA_GROUP_INTERVAL_SECONDS)
    else:
        batch_cnt = math.ceil(group_cnt / WAVE_SIZE)
        interval_seconds = max(math.floor(SCHEDULE_WINDOW_SECONDS / batch_cnt), MIN_WAVE_INTERVAL_SECONDS)
        clock = ClusterRetryClock(start, MODE_WAVE, interval_seconds)
    logger.info(
        "分区重试集群时钟 cluster_type=%s cluster_id=%s mode=%s interval=%s conf_cnt=%s",
        cluster_type,
        cluster_id,
        clock.mode,
        clock.interval_seconds,
        conf_cnt,
    )
    return clock


def today_start() -> datetime:
    """当天 0 点。9:03 重试只看今天这一轮，不用巡检的近 24 小时窗口。"""
    local_now = timezone.localtime()
    return local_now.replace(hour=0, minute=0, second=0, microsecond=0)


def load_conf_cnt(cluster_type: str) -> Dict[int, int]:
    domain_infos = get_exec_domain_info(cluster_type)
    return {int(info["cluster_id"]): int(info["conf_cnt"]) for info in domain_infos}


def coerce_conf_cnt_map(conf_cnt_map: Optional[Dict]) -> Dict[int, int]:
    """Celery JSON 会把字典的 int key 变成字符串，这里转回 int。空 map 表示走 30 秒兜底。"""
    if not conf_cnt_map:
        return {}
    coerced: Dict[int, int] = {}
    for cluster_id, conf_cnt in conf_cnt_map.items():
        if cluster_id in (None, "") or conf_cnt in (None, ""):
            continue
        coerced[int(cluster_id)] = int(conf_cnt)
    return coerced


def query_conf_by_ids(bk_biz_id: int, cluster_type: str, config_ids: List[int]) -> List[Dict]:
    """只用来拿 config_id 对应的 cluster_id。这一行不下发。"""
    params = {
        "bk_biz_id": bk_biz_id,
        "cluster_type": cluster_type,
        "ids": config_ids,
        "limit": len(config_ids),
        "offset": 0,
    }
    resp = DBPartitionApi.query_conf_v2(params=params)
    return resp.get("items") or []


def _config_id_of(item: Dict) -> Optional[int]:
    raw_config_id = item.get("config_id")
    if raw_config_id in (None, ""):
        raw_config_id = item.get("id")
    if raw_config_id in (None, ""):
        return None
    return int(raw_config_id)


def load_retry_configs(bk_biz_id: int, cluster_type: str, config_ids: List[int]) -> Dict[int, List[Dict]]:
    """
    只拉待重试的配置。

    query_conf_v2 只提供 cluster_id。执行参数用 get_conf_by_id，和按配置执行的日常入口同一份返回。
    """
    grouped: Dict[int, List[Dict]] = defaultdict(list)
    seen = set()
    for config_id_chunk in _chunked(config_ids, CONF_QUERY_SIZE):
        try:
            items = query_conf_by_ids(bk_biz_id, cluster_type, config_id_chunk)
        except Exception as exc:  # pylint: disable=broad-except
            logger.exception(
                "分区重试查询配置所属集群失败 cluster_type=%s bk_biz_id=%s ids=%s err=%s",
                cluster_type,
                bk_biz_id,
                len(config_id_chunk),
                exc,
            )
            continue
        for item in items:
            config_id = _config_id_of(item or {})
            cluster_id = item.get("cluster_id") if item else None
            if config_id is None or cluster_id in (None, ""):
                logger.warning(
                    "分区重试配置缺少 cluster_id 或 config_id cluster_type=%s bk_biz_id=%s item=%s",
                    cluster_type,
                    bk_biz_id,
                    item,
                )
                continue
            if config_id in seen:
                continue
            seen.add(config_id)
            try:
                data = get_partition_by_config_id(int(cluster_id), config_id, cluster_type)
            except Exception as exc:  # pylint: disable=broad-except
                logger.exception(
                    "分区重试拉取单条配置失败 cluster_type=%s cluster_id=%s config_id=%s err=%s",
                    cluster_type,
                    cluster_id,
                    config_id,
                    exc,
                )
                continue
            configs = (data or {}).get("configs") or []
            if not configs:
                logger.warning(
                    "分区重试单条配置为空 cluster_type=%s cluster_id=%s config_id=%s",
                    cluster_type,
                    cluster_id,
                    config_id,
                )
                continue
            grouped[int(cluster_id)].extend(configs)
        if len(items) < len(config_id_chunk):
            logger.warning(
                "分区重试配置查询条数少于请求 cluster_type=%s bk_biz_id=%s request=%s response=%s",
                cluster_type,
                bk_biz_id,
                len(config_id_chunk),
                len(items),
            )
    return grouped


def dispatch_retry_group(cluster_type: str, cluster_id: int, configs: List[Dict], eta: datetime, seq: int):
    if not configs:
        logger.warning(
            "分区重试跳过空配置组 cluster_type=%s cluster_id=%s seq=%s",
            cluster_type,
            cluster_id,
            seq,
        )
        return
    payload = {"cluster_id": cluster_id, "configs": configs, "force": False}
    time_str = eta.strftime("%Y%m%d%H%M%S")
    first_id = configs[0].get("config_id")
    last_id = configs[-1].get("config_id")
    task_id = f"mysql_partition_retry_{cluster_id}_{seq}_{first_id}_{last_id}_{time_str}"
    if cluster_type == ClusterType.TenDBHA.value:
        execute_tendbha_partition_task.apply_async(args=[payload], eta=eta, task_id=task_id)
    elif cluster_type == ClusterType.TenDBCluster.value:
        execute_tendbcluster_partition_task.apply_async(args=[payload], eta=eta, task_id=task_id)
    else:
        raise Exception("cluster type not supported")


def dispatch_page_retries(
    bk_biz_id: int,
    cluster_type: str,
    config_ids: List[int],
    since: datetime,
    conf_cnt_map: Dict[int, int],
    clocks: Dict[int, ClusterRetryClock],
    start: datetime,
) -> Tuple[int, int, int]:
    """
    一页 config_id 先按巡检规则判定，再只拉失败和未执行的配置下发。

    返回本页的失败数、未执行数、下发组数。
    """
    success_ids, failed_ids = _fetch_execution_sets_for_config_ids(
        cluster_type=cluster_type,
        bk_biz_id=bk_biz_id,
        config_ids=config_ids,
        since=since,
    )
    not_run_ids, fail_ids = _classify_config_ids(
        config_ids=config_ids,
        success_ids=success_ids,
        failed_ids=failed_ids,
    )
    retry_ids = fail_ids + not_run_ids
    if not retry_ids:
        return len(fail_ids), len(not_run_ids), 0

    grouped = load_retry_configs(bk_biz_id, cluster_type, retry_ids)
    group_cnt = 0
    for cluster_id, configs in grouped.items():
        clock = clocks.get(cluster_id)
        if clock is None:
            clock = build_cluster_clock(cluster_id, cluster_type, conf_cnt_map.get(cluster_id), start)
            clocks[cluster_id] = clock
        for group in _chunked(configs, GROUP_SIZE):
            eta, seq = clock.next_eta()
            dispatch_retry_group(cluster_type, cluster_id, group, eta, seq)
            group_cnt += 1
    return len(fail_ids), len(not_run_ids), group_cnt


@app.task(max_retries=0, rate_limit="50/m")
def retry_one_biz_partition_task(bk_biz_id: int, cluster_type: str, conf_cnt_map: Optional[Dict] = None):
    """
    单个业务的分区重试。

    和巡检一样先分页收集 config_id，判定失败和当天未执行后，再按 id 拉配置下发。
    conf_cnt_map 由调度入口查一次后传入。缺失时按 30 秒一波排期，不中断下发。
    不自动重试：时钟在本任务进程内，中途失败后再跑会把已下发的组再排一次。
    """
    conf_cnt_map = coerce_conf_cnt_map(conf_cnt_map)
    since = today_start()
    start = timezone.now()
    clocks: Dict[int, ClusterRetryClock] = {}
    fail_cnt = 0
    not_run_cnt = 0
    group_cnt = 0

    try:
        for config_ids in _iter_biz_config_ids(cluster_type, bk_biz_id, CONFIG_ID_PAGE_SIZE):
            if not config_ids:
                continue
            try:
                page_fail, page_not_run, page_groups = dispatch_page_retries(
                    bk_biz_id=bk_biz_id,
                    cluster_type=cluster_type,
                    config_ids=config_ids,
                    since=since,
                    conf_cnt_map=conf_cnt_map,
                    clocks=clocks,
                    start=start,
                )
            except Exception as exc:  # pylint: disable=broad-except
                logger.exception(
                    "分区重试处理一页配置失败，继续下一页 cluster_type=%s bk_biz_id=%s page_size=%s err=%s",
                    cluster_type,
                    bk_biz_id,
                    len(config_ids),
                    exc,
                )
                continue
            fail_cnt += page_fail
            not_run_cnt += page_not_run
            group_cnt += page_groups
    except Exception as exc:  # pylint: disable=broad-except
        logger.exception(
            "分区重试拉取配置 id 失败 cluster_type=%s bk_biz_id=%s err=%s",
            cluster_type,
            bk_biz_id,
            exc,
        )
    finally:
        logger.info(
            "分区重试业务完成 cluster_type=%s bk_biz_id=%s 失败=%s 未执行=%s 集群数=%s 下发组数=%s",
            cluster_type,
            bk_biz_id,
            fail_cnt,
            not_run_cnt,
            len(clocks),
            group_cnt,
        )


def schedule_partition_retry(cluster_type: str):
    logger.info("start partition retry cluster_type=%s", cluster_type)
    try:
        conf_cnt_map = load_conf_cnt(cluster_type)
    except Exception as exc:  # pylint: disable=broad-except
        logger.exception(
            "分区重试获取集群配置数失败，按 30 秒波次继续下发 cluster_type=%s err=%s",
            cluster_type,
            exc,
        )
        conf_cnt_map = None
    try:
        for biz in _iter_check_biz(cluster_type, BIZ_PAGE_SIZE):
            if biz.config_count <= 0:
                continue
            retry_one_biz_partition_task.apply_async(args=[biz.bk_biz_id, cluster_type, conf_cnt_map])
    except Exception as exc:  # pylint: disable=broad-except
        logger.exception("分区重试列举业务失败 cluster_type=%s err=%s", cluster_type, exc)


@register_periodic_task(run_every=crontab(minute=3, hour="9"))
def tendbha_partition_retry_task():
    schedule_partition_retry(ClusterType.TenDBHA.value)


@register_periodic_task(run_every=crontab(minute=3, hour="9"))
def tendbcluster_partition_retry_task():
    schedule_partition_retry(ClusterType.TenDBCluster.value)
