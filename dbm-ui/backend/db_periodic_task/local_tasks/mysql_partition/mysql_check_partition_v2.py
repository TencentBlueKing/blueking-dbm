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

import datetime
import logging
from dataclasses import dataclass
from datetime import timedelta
from typing import Dict, Iterable, List, Set, Tuple

from celery.schedules import crontab
from django.db.models import Max
from django.utils import timezone
from django.utils.translation import gettext as _

from backend import env
from backend.components.mysql_partition.client import DBPartitionApi
from backend.configuration.constants import DBType
from backend.configuration.models import DBAdministrator
from backend.core.notify.handlers import CmsiHandler
from backend.db_meta.enums.cluster_type import ClusterType
from backend.db_periodic_task.local_tasks import register_periodic_task
from backend.db_report.models.mysql_partiton_resuly import MysqlPartitionResult

logger = logging.getLogger("root")

# 每日巡检：只统计近 24 小时内的上报结果（滚动窗口，在 collect() 开始时固定 since）
CHECK_RESULT_WINDOW_HOURS = 24
BIZ_PAGE_SIZE = 100
CONFIG_ID_PAGE_SIZE = 2000
# 结果表 config_id__in 单批上限，避免 SQL 过长
RESULT_QUERY_CHUNK_SIZE = 500
# 企微展示的策略 ID 上限
DISPLAY_IDS_MAX_COUNT = 20
# 企微单段正文长度上限
WECOM_CONTENT_MAX_LEN = 1024

STATUS_SUCCESS = frozenset({"success", "succeeded"})
STATUS_FAILED = frozenset({"failed", "fail"})

MYSQL_CLUSTER_TYPE = ClusterType.TenDBHA.value
SPIDER_CLUSTER_TYPE = ClusterType.TenDBCluster.value


@dataclass
class BizCheckMeta:
    bk_biz_id: int
    db_app_abbr: str
    config_count: int


@dataclass(frozen=True)
class CheckSummary:
    bk_biz_id: int
    db_app_abbr: str
    cnt: int
    ids: str

    def as_dict(self) -> Dict:
        return {
            "bk_biz_id": self.bk_biz_id,
            "db_app_abbr": self.db_app_abbr,
            "cnt": self.cnt,
            "ids": self.ids,
        }


class PartitionCheckV2Collector:
    """按业务分批巡检，峰值内存 ≈ 单批 config_id + 异常汇总行。"""

    def __init__(self, result_window_hours: int = CHECK_RESULT_WINDOW_HOURS):
        self.since = timezone.now() - timedelta(hours=result_window_hours)

    def collect(self) -> Dict[str, List[Dict]]:
        mysql_not_run, mysql_fail = self._check_cluster_type(MYSQL_CLUSTER_TYPE)
        spider_not_run, spider_fail = self._check_cluster_type(SPIDER_CLUSTER_TYPE)
        return {
            "mysql_not_run": [s.as_dict() for s in mysql_not_run],
            "mysql_fail": [s.as_dict() for s in mysql_fail],
            "spider_not_run": [s.as_dict() for s in spider_not_run],
            "spider_fail": [s.as_dict() for s in spider_fail],
        }

    def _check_cluster_type(self, cluster_type: str) -> Tuple[List[CheckSummary], List[CheckSummary]]:
        not_run_summaries: List[CheckSummary] = []
        fail_summaries: List[CheckSummary] = []

        for biz_meta in _iter_check_biz(cluster_type, BIZ_PAGE_SIZE):
            if biz_meta.config_count <= 0:
                continue
            not_run_ids, fail_ids = self._check_one_biz(cluster_type, biz_meta)
            if not_run_ids:
                not_run_summaries.append(_make_summary(biz_meta, not_run_ids))
            if fail_ids:
                fail_summaries.append(_make_summary(biz_meta, fail_ids))

        return not_run_summaries, fail_summaries

    def _check_one_biz(self, cluster_type: str, biz_meta: BizCheckMeta) -> Tuple[List[int], List[int]]:
        not_run_ids: List[int] = []
        fail_ids: List[int] = []

        for config_ids in _iter_biz_config_ids(
            cluster_type=cluster_type,
            bk_biz_id=biz_meta.bk_biz_id,
            page_size=CONFIG_ID_PAGE_SIZE,
        ):
            if not config_ids:
                continue
            success_ids, failed_ids = _fetch_execution_sets_for_config_ids(
                cluster_type=cluster_type,
                bk_biz_id=biz_meta.bk_biz_id,
                config_ids=config_ids,
                since=self.since,
            )
            batch_not_run, batch_fail = _classify_config_ids(
                config_ids=config_ids,
                success_ids=success_ids,
                failed_ids=failed_ids,
            )
            not_run_ids.extend(batch_not_run)
            fail_ids.extend(batch_fail)

        return not_run_ids, fail_ids


def _iter_check_biz(cluster_type: str, page_size: int) -> Iterable[BizCheckMeta]:
    offset = 0
    while True:
        resp = _call_list_check_biz(cluster_type, page_size, offset)
        items = resp.get("items") or []
        for row in items:
            # 每产出一个业务就返回一个 BizCheckMeta 对象，上层一个一个业务处理执行结果
            yield BizCheckMeta(
                bk_biz_id=int(row["bk_biz_id"]),
                db_app_abbr=row.get("db_app_abbr") or "",
                config_count=int(row.get("config_count") or 0),
            )
        total = int(resp.get("count") or 0)
        offset += len(items)
        if not items or offset >= total:
            break


def _iter_biz_config_ids(
    cluster_type: str,
    bk_biz_id: int,
    page_size: int,
) -> Iterable[List[int]]:
    offset = 0
    while True:
        resp = _call_list_check_conf_ids(cluster_type, bk_biz_id, page_size, offset)
        config_ids = [int(i) for i in (resp.get("config_ids") or [])]
        # 每CONFIG_ID_PAGE_SIZE个config_id返回一次
        yield config_ids
        total = int(resp.get("count") or 0)
        offset += len(config_ids)
        if not config_ids or offset >= total:
            break


def _call_list_check_biz(cluster_type: str, limit: int, offset: int) -> Dict:
    params = {
        "cluster_type": cluster_type,
        "limit": limit,
        "offset": offset,
    }
    try:
        return DBPartitionApi.list_check_biz_v2(params=params)
    except Exception as exc:  # pylint: disable=broad-except
        raise RuntimeError(
            _("分区服务 list_check_biz_v2 异常 cluster_type={} offset={}: {}").format(cluster_type, offset, exc)
        ) from exc


def _call_list_check_conf_ids(
    cluster_type: str,
    bk_biz_id: int,
    limit: int,
    offset: int,
) -> Dict:
    params = {
        "cluster_type": cluster_type,
        "bk_biz_id": bk_biz_id,
        "limit": limit,
        "offset": offset,
    }
    try:
        return DBPartitionApi.list_check_conf_ids_v2(params=params)
    except Exception as exc:  # pylint: disable=broad-except
        raise RuntimeError(
            _("分区服务 list_check_conf_ids_v2 异常 cluster_type={} bk_biz_id={} offset={}: {}").format(
                cluster_type, bk_biz_id, offset, exc
            )
        ) from exc


def _fetch_execution_sets_for_config_ids(
    cluster_type: str,
    bk_biz_id: int,
    config_ids: List[int],
    since: datetime.datetime,
) -> Tuple[Set[int], Set[int]]:
    """近 24 小时内，按 config_id 取 id 最大的一条（最近一次上报）判定 success / failed。"""
    success_ids: Set[int] = set()
    failed_ids: Set[int] = set()

    base_filter = {
        "cluster_type": cluster_type,
        "bk_biz_id": bk_biz_id,
        "create_time__gte": since,
    }

    for chunk in _chunked(config_ids, RESULT_QUERY_CHUNK_SIZE):
        latest_log_ids = (
            MysqlPartitionResult.objects.filter(config_id__in=chunk, **base_filter)
            .values("config_id")
            .annotate(latest_id=Max("id"))
            .values_list("latest_id", flat=True)
        )
        if not latest_log_ids:
            continue
        for config_id, status in MysqlPartitionResult.objects.filter(id__in=latest_log_ids).values_list(
            "config_id", "status"
        ):
            normalized = (status or "").lower()
            if normalized in STATUS_SUCCESS:
                success_ids.add(config_id)
            elif normalized in STATUS_FAILED:
                failed_ids.add(config_id)

    return success_ids, failed_ids


def _classify_config_ids(
    config_ids: List[int],
    success_ids: Set[int],
    failed_ids: Set[int],
) -> Tuple[List[int], List[int]]:
    """
    近 24 小时窗口内，以每个 config_id 最近一次上报（max id）为准：
      正常     = 最近一条为 success/succeeded（在 success_ids）
      fail     = 最近一条为 failed（在 failed_ids）
      not_run  = 24h 内无上报记录
    """
    not_run: List[int] = []
    fail: List[int] = []
    for config_id in config_ids:
        if config_id in success_ids:
            continue
        if config_id in failed_ids:
            fail.append(config_id)
        else:
            not_run.append(config_id)
    return not_run, fail


def _make_summary(biz_meta: BizCheckMeta, problem_ids: List[int]) -> CheckSummary:
    ids_sorted = sorted(set(problem_ids))
    return CheckSummary(
        bk_biz_id=biz_meta.bk_biz_id,
        db_app_abbr=biz_meta.db_app_abbr,
        cnt=len(ids_sorted),
        ids=",".join(str(i) for i in ids_sorted),
    )


def _chunked(items: List[int], size: int) -> Iterable[List[int]]:
    for i in range(0, len(items), size):
        yield items[i : i + size]


def _truncate_ids(ids_str: str, max_count: int = DISPLAY_IDS_MAX_COUNT) -> str:
    """策略 ID 过多时截断展示，避免企微消息过长。"""
    if not ids_str:
        return ids_str
    parts = [p for p in ids_str.split(",") if p]
    if len(parts) <= max_count:
        return ids_str
    return ",".join(parts[:max_count]) + _("...(共{}个)").format(len(parts))


def _format_msg_v2(logs: List[Dict], db_type: str, fail_type: str, content: str) -> str:
    """生成 v2 巡检企微正文行。"""
    if not logs:
        return content
    for biz_msg in logs:
        dbas = DBAdministrator().get_biz_db_type_admins(biz_msg["bk_biz_id"], DBType.MySQL)
        dba = dbas[0] if dbas else "None"
        content = _(
            "{}{}   {}   {}   {}   {}   <@{}>   {}\n".format(
                content,
                biz_msg["db_app_abbr"],
                biz_msg["bk_biz_id"],
                db_type,
                fail_type,
                biz_msg["cnt"],
                dba,
                _truncate_ids(biz_msg["ids"]),
            )
        )
    return content


def _cut_content_v2(content: str) -> List[str]:
    """将正文按长度分段，防止企微超限。"""
    split_contents = content.split("\n")
    contents: List[str] = []
    current_content = ""
    for index, msg in enumerate(split_contents):
        if msg:
            current_content += msg + "\n"
        if len(current_content) > WECOM_CONTENT_MAX_LEN or index == len(split_contents) - 1:
            contents.append(current_content)
            current_content = ""
    return contents


@register_periodic_task(run_every=crontab(day_of_week="*", hour="14", minute="35"))
def mysql_check_partition_v2():
    """分区 v2 巡检：按业务分批采集，仅对异常业务生成汇总并推送企微。"""
    try:
        logs = PartitionCheckV2Collector().collect()
    except Exception as exc:  # pylint: disable=broad-except
        logger.error(_("分区 v2 巡检采集异常: {}").format(exc))
        return

    content = ""
    content = _format_msg_v2(logs["mysql_not_run"], DBType.MySQL, _("未执行"), content)
    content = _format_msg_v2(logs["mysql_fail"], DBType.MySQL, _("失败"), content)
    content = _format_msg_v2(logs["spider_not_run"], DBType.TenDBCluster, _("未执行"), content)
    content = _format_msg_v2(logs["spider_fail"], DBType.TenDBCluster, _("失败"), content)
    content = content.rstrip("\n")

    if not content:
        logger.info("partition v2 check: no abnormal configs, skip notify")
        return

    if env.MYSQL_CHATID == "":
        logger.error(_("环境变量MYSQL_CHATID未设置"))
        return
    if env.WECOM_ROBOT == "":
        logger.error(_("环境变量WECOM_ROBOT未设置"))
        return

    chat_ids = env.MYSQL_CHATID.split(",")
    for msg in _cut_content_v2(content):
        title = _("【DBM】分区表异常(v2) ")
        partition_msg = _("【DBM】分区表异常情况(v2) {} \n业务名称 bk_biz_id DB类型 失败/未执行 数量 DBA 策略ID\n{}").format(
            datetime.date.today(),
            msg,
        )
        CmsiHandler(title, partition_msg, chat_ids).send_wecom_robot()
