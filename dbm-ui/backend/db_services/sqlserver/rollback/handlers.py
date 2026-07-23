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
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Set

from django.utils import timezone
from django.utils.translation import gettext as _

from backend.components.bklog.handler import BKLogHandler
from backend.db_meta.models import Cluster
from backend.db_report.models.sqlserver_full_backup_result import SQLServerBackupResult
from backend.db_report.models.sqlserver_log_backup_result import SQLServerBinlogResult
from backend.db_services.sqlserver.rollback.constants import BACKUP_LOG_RANGE_DAYS
from backend.db_services.sqlserver.rollback.log_backup_chain import LogBackupChainInspector, LogBackupChainResult
from backend.flow.utils.sqlserver.sqlserver_db_function import sqlserver_match_dbs
from backend.utils.time import datetime2str, find_nearby_time, str2datetime, timezone2timestamp


class SQLServerRollbackHandler(object):
    """sqlserver定点构造函数封装"""

    def __init__(self, cluster_id: int):
        self.cluster = Cluster.objects.get(id=cluster_id)

    @staticmethod
    def _serialize_backup_log(log: Dict) -> Dict:
        """
        将备份记录中的 datetime 字段转换为字符串，避免 JSON 序列化失败

        @param log: 备份记录字典
        @return: 序列化后的备份记录字典
        """
        serialized_log = log.copy()
        datetime_fields = [
            "created_at",
            "updated_at",
            "backup_task_start_time",
            "backup_task_end_time",
            "backup_begin_time",
            "backup_end_time",
        ]
        for field in datetime_fields:
            if field in serialized_log and serialized_log[field]:
                serialized_log[field] = datetime2str(serialized_log[field])
        return serialized_log

    @staticmethod
    def _get_log_from_bklog(
        collector: str, start_time: datetime, end_time: datetime, query_string="*", size=-1, sort_rule="asc"
    ) -> List[Dict]:
        return BKLogHandler.query_logs(collector, start_time, end_time, query_string, size, sort_rule)

    def query_binlogs(self, start_time: datetime, end_time: datetime, dbname: str):
        """
        根据时间范围查询集群的binlog记录
        @param start_time: 查询开始时间
        @param end_time: 查询结束时间
        @param dbname: 查询db
        """
        # 单独获取最后一个binlog, 加1秒为了保证获取比时间点大于的日志备份
        last_binlogs = self._get_log_from_bklog(
            collector="mssql_binlog_result",
            start_time=end_time + timedelta(seconds=1),
            end_time=end_time + timedelta(days=BACKUP_LOG_RANGE_DAYS),
            query_string=f"""cluster_id: {self.cluster.id} AND dbname: "{dbname}" """,
            size=1,
        )
        if not last_binlogs:
            raise ValueError(
                _(
                    "cluster [{}] 在时间范围 [{}~{}] 内找不到后续的日志备份记录".format(
                        self.cluster.name, end_time, end_time + timedelta(days=BACKUP_LOG_RANGE_DAYS)
                    )
                )
            )

        # 然后获取时间范围内的binlog
        binlogs = self._get_log_from_bklog(
            collector="mssql_binlog_result",
            start_time=start_time,
            end_time=end_time + timedelta(seconds=1),
            query_string=f"""cluster_id: {self.cluster.id} AND dbname: "{dbname}" """,
        )
        # TODO: binlog是否需要聚合 or 转义
        # list去重
        unique_list = []
        seen_values = set()
        for binlog in binlogs + last_binlogs:
            if binlog["backup_id"] not in seen_values:
                unique_list.append(binlog)
                seen_values.add(binlog["backup_id"])

        return unique_list

    @staticmethod
    def check_restore_time_range(restore_time_str: str) -> str:
        """校验 restore_time 的时间窗口合法性：不能晚于当前时间、不能早于 N 天前。

        设计要点 / 怎么做：
          - 业务约束一：定点构造要求 restore_time <= now（不能回档到未来）
          - 业务约束二：日志备份保留窗口 = BACKUP_LOG_RANGE_DAYS 天，超过该窗口的备份记录
            会被清理，即使 flow 执行也无法拿到日志文件；提交阶段 fail-fast 避免误提单
          - 双阶段调用：validator 提交时校验一次，flow 执行时再校验一次（时间跨度大，
            提交合法但执行时越界的情况必须兜住），共用同一份判定逻辑，错误消息一致
          - 时区：str2datetime 已强制要求解析结果为时区感知（aware），故与 timezone.now()
            比较无需再做 tz 归一，直接 `<` / `>` 运算即可
          - 静态方法：不依赖 handler 实例（cluster 无关），避免调用方为了一个纯校验去构造
            handler 实例，减少不必要的 DB 查询依赖

        :param restore_time_str: 目标构造时点字符串（ISO 格式，例如 "2024-01-01 12:00:00+08:00"）
        :return: 错误消息字符串；为空表示校验通过

        边界 / 异常：
          - restore_time_str 无法解析      -> str2datetime 抛 ValidationError（由上游兜住）
          - restore_time > now             -> 返回"不能晚于当前时间"错误
          - now - restore_time > 15 天     -> 返回"超出日志备份保留窗口"错误
          - 两个越界同时命中               -> 只返回首个（未来时间优先级更高，是明确输入错误）
        """
        restore_time: datetime = str2datetime(restore_time_str)
        # 使用 Django timezone.now() 拿到与 str2datetime 一致的时区感知当前时间
        now: datetime = timezone.now()

        # 约束一：restore_time 不能晚于当前时间（回档到未来无意义）
        if restore_time > now:
            return _("restore_time[{t}] 不能晚于当前时间[{now}]").format(t=restore_time_str, now=now)

        # 约束二：restore_time 距离当前时间不能超过 BACKUP_LOG_RANGE_DAYS 天
        # 超出该窗口的日志备份已被清理，即使提单/执行也无法完成回档
        if (now - restore_time).days > BACKUP_LOG_RANGE_DAYS:
            return _("restore_time[{t}] 距离当前时间[{now}]已超过 {days} 天，" "日志备份保留窗口内的记录已被清理，无法完成定点回档").format(
                t=restore_time_str, now=now, days=BACKUP_LOG_RANGE_DAYS
            )

        return ""

    def fetch_and_check_log_backup_chain(
        self,
        full_backup_info: Dict[str, Any],
        restore_time: datetime,
    ) -> LogBackupChainResult:
        """单 DB 日志备份链校验入口：一次调用产出 6 态之一的结构化结果。

        设计要点 / 怎么做：
          - 薄壳方法：仅做参数适配 + 委托给 `LogBackupChainInspector.inspect()`
          - 底层能力：见 `backend/db_services/sqlserver/rollback/log_backup_chain.py`
          - 输入契约：full_backup_info 由调用方装配，含 db_name / backup_full_end_time /
            cluster_address 三个必需字段与 full_last_lsn / full_file_name 两个可选字段

        :param full_backup_info: 全量备份信息 dict（见 LogBackupChainInspector.__init__ 详解）
        :param restore_time: 目标构造时点 datetime（可带 tzinfo）
        :return: LogBackupChainResult 实例；status 必为 6 态之一

        边界 / 异常：
          - full_backup_info 缺失必需字段 -> 由 Inspector 抛 ValueError
          - 非 OK 一律返回 backup_infos=[]（D5 决策）
        """
        inspector: LogBackupChainInspector = LogBackupChainInspector(
            cluster=self.cluster,
            full_backup_info=full_backup_info,
            restore_time=restore_time,
        )
        return inspector.inspect()

    def check_log_backup_chain_batch(
        self,
        full_restore_infos: List[Dict[str, Any]],
        restore_time: datetime,
    ) -> List[LogBackupChainResult]:
        """批量日志备份链校验入口：循环调用单条入口，供 validator 提交时 fail-fast 使用。

        设计要点 / 怎么做：
          - 内部循环调用 `fetch_and_check_log_backup_chain`；每个 DB 独立结果，
            互不影响（某个 DB 输入非法抛 ValueError 会中断整批，由上层决定是否兜住）
          - 返回结构化列表而非字符串错误列表（D6 决策），由 validator 侧自行聚合渲染

        :param full_restore_infos: 已完成全量匹配的构造信息列表，每个元素结构同单条入口；
            必须非空，空列表视为上游装配层异常（校验目标缺失即无意义可校验）
        :param restore_time: 目标构造时点（对整批共用）
        :return: `List[LogBackupChainResult]`，每个元素含 db_name 字段回填便于上下文回溯

        边界 / 异常：
          - full_restore_infos 为空 -> raise ValueError（fail-fast，避免静默通过掩盖上游 bug）
          - 单个 DB 的 full_backup_info 缺字段 -> Inspector 抛 ValueError，中断整批
        """
        if not full_restore_infos:
            raise ValueError("full_restore_infos is empty; batch check requires at least one full backup info entry")

        results: List[LogBackupChainResult] = []
        for full_info in full_restore_infos:
            result: LogBackupChainResult = self.fetch_and_check_log_backup_chain(
                full_backup_info=full_info,
                restore_time=restore_time,
            )
            results.append(result)

        return results

    def query_backup_logs(self, start_time: datetime, end_time: datetime):
        """
        根据时间范围查询集群的备份记录
        @param start_time: 查询开始时间
        @param end_time: 查询结束时间
        """
        backup_logs = self._get_log_from_bklog(
            collector="mssql_dbbackup_result",
            start_time=start_time,
            end_time=end_time,
            query_string=f"cluster_id: {self.cluster.id}",
        )

        # 根据backup id聚合备份记录
        backup_id__logs: Dict[str, List] = defaultdict(list)
        for log in backup_logs:
            if log["data_schema_grant"] == "all":
                backup_id__logs[log["backup_id"]].append(log)

        # 对每一份备份记录去重，相同的backup id不能出现重复的dbname
        backup_id__valid_logs: Dict[str, List] = defaultdict(list)
        for backup_id, logs in backup_id__logs.items():
            dbname_set: Set[str] = set()
            for log in logs:
                if log["dbname"] not in dbname_set:
                    backup_id__valid_logs[backup_id].append(log)
                dbname_set.add(log["dbname"])

        # 对每个聚合记录补充信息
        backup_logs: List[Dict[str, Any]] = []
        for backup_id, logs in backup_id__valid_logs.items():
            start_time = min(map(str2datetime, [log["backup_begin_time"] for log in logs]))
            end_time = max(map(str2datetime, [log["backup_end_time"] for log in logs]))
            backup_log_info = {
                "start_time": datetime2str(start_time),
                "end_time": datetime2str(end_time),
                "backup_id": backup_id,
                "logs": logs,
                "complete": len(logs) == logs[0]["file_cnt"],
                "expected_cnt": logs[0]["file_cnt"],
                "real_cnt": len(logs),
                # 是否只取第一个log的角色就好了？
                "role": logs[0]["role"],
            }
            backup_logs.append(backup_log_info)
        backup_logs = sorted(backup_logs, key=lambda x: x["start_time"], reverse=True)
        return backup_logs

    def query_backup_logs_from_model(self, start_time: datetime, end_time: datetime) -> List[Dict[str, Any]]:
        """
        基于 SQLServerBackupResult Model 查询集群的备份记录（替代 bklog 查询）
        @param start_time: 查询开始时间
        @param end_time: 查询结束时间
        """
        backup_qs = SQLServerBackupResult.objects.filter(
            cluster_id=self.cluster.id,
            backup_end_time__gte=start_time,
            backup_end_time__lte=end_time,
        )
        backup_logs_raw = list(backup_qs.values())

        # 根据 backup_id 聚合备份记录，仅保留 data_schema_grant == "all" 的记录
        backup_id__logs: Dict[str, List] = defaultdict(list)
        for log in backup_logs_raw:
            if log["data_schema_grant"] == "all":
                backup_id__logs[log["backup_id"]].append(log)

        # 对每一份备份记录去重，相同的 backup_id 不能出现重复的 dbname
        backup_id__valid_logs: Dict[str, List] = defaultdict(list)
        for backup_id, logs in backup_id__logs.items():
            dbname_set: Set[str] = set()
            for log in logs:
                if log["dbname"] not in dbname_set:
                    backup_id__valid_logs[backup_id].append(log)
                dbname_set.add(log["dbname"])

        # 对每个聚合记录补充信息
        result_logs: List[Dict[str, Any]] = []
        for backup_id, logs in backup_id__valid_logs.items():
            log_start_time = min(log["backup_begin_time"] for log in logs)
            log_end_time = max(log["backup_end_time"] for log in logs)
            # 计算已备份的 dbname 列表
            dbname_list = [log["dbname"] for log in logs]
            # 缺失的数据库 = db_list - 已备份的 dbname_list
            expected_db_list = logs[0]["db_list"]
            excluded_db_list = list(set(expected_db_list.split(",")) - set(dbname_list))

            # 将 logs 中的 datetime 字段转换为字符串，避免 JSON 序列化失败
            serialized_logs = [self._serialize_backup_log(log) for log in logs]

            backup_log_info = {
                "start_time": datetime2str(log_start_time),
                "end_time": datetime2str(log_end_time),
                "backup_id": backup_id,
                "logs": serialized_logs,
                "complete": len(logs) == logs[0]["file_cnt"],
                "expected_cnt": logs[0]["file_cnt"],
                "real_cnt": len(logs),
                "role": logs[0]["role"],  # 备份角色：logs 中其中的一个 role
                "backup_db_list": logs[0]["db_list"].split(","),  # 备份包含库：logs 中一个 db_list
                "backup_db_size_kb": sum(log["db_size_kb"] for log in logs),  # 数据库大小：同一个 backup_id 的 sum(db_size_kb)
                "backup_file_size_kb": sum(
                    log["file_size_kb"] for log in logs
                ),  # 备份文件大小：同一个 backup_id 的 sum(file_size_kb)
                "excluded_db_list": excluded_db_list,  # 排除库/缺失库：db_list - 已备份的 dbname_list
                "bill_id": logs[0]["bill_id"],  # 关联单据 id
            }
            result_logs.append(backup_log_info)

        result_logs = sorted(result_logs, key=lambda x: x["start_time"], reverse=True)
        return result_logs

    def query_latest_backup_log(self, rollback_time: datetime):
        """
        根据回档时间查询集群最近的备份记录
        @param rollback_time: 回档时间
        """
        end_time = rollback_time
        start_time = end_time - timedelta(days=BACKUP_LOG_RANGE_DAYS)
        backup_logs = self.query_backup_logs(start_time, end_time)

        # 查询最近的备份记录
        backup_logs.sort(key=lambda x: x["end_time"])
        time_keys = [log["end_time"] for log in backup_logs]
        try:
            latest_backup_log_index = find_nearby_time(time_keys, timezone2timestamp(rollback_time), flag=1)
        except IndexError:
            return {"logs": []}

        return backup_logs[latest_backup_log_index]

    def query_latest_backup_log_from_model(self, rollback_time: datetime):
        """
        基于 Model 查询，根据回档时间查询集群最近的备份记录
        @param rollback_time: 回档时间
        """
        end_time = rollback_time
        start_time = end_time - timedelta(days=BACKUP_LOG_RANGE_DAYS)
        backup_logs = self.query_backup_logs_from_model(start_time, end_time)

        # 查询最近的备份记录
        backup_logs.sort(key=lambda x: x["end_time"])
        time_keys = [log["end_time"] for log in backup_logs]
        try:
            latest_backup_log_index = find_nearby_time(time_keys, timezone2timestamp(rollback_time), flag=1)
        except IndexError:
            return {"logs": []}

        return backup_logs[latest_backup_log_index]

    def query_dbs_by_backup_log(
        self,
        db_pattern: List[str],
        ignore_db: List[str],
        backup_logs: List[Dict] = None,
        restore_time: datetime = None,
    ):
        """
        根据回档记录/回档时间，和库正则，过滤真正操作的DB库
        @param db_pattern: 库正则
        @param ignore_db: 忽略库正则
        @param backup_logs: 备份记录列表(这里只关注记录中的备份库字段)
        @param restore_time: 回档时间
        """
        if restore_time:
            backup_logs = self.query_latest_backup_log_from_model(restore_time)

        db_names = [log["dbname"] for log in backup_logs["logs"]]
        db_list = backup_logs["logs"][0]["db_list"].split(",")
        # 取 db_list 在 db_names 中没有的数据（缺失/排除库）
        excluded_db_names = set(db_list) - set(db_names)
        # 匹配实际备份库，并剔除落在排除库集合中的数据（保证 real_db_names 不含 excluded 库）
        real_db_names = [
            db for db in sqlserver_match_dbs(db_names, db_pattern, ignore_db) if db not in excluded_db_names
        ]
        return real_db_names

    def query_last_log_time(self, query_time: datetime):
        """
        查询集群的最近一次上报的备份时间
        拿最新的一条备份记录的备份开始时间的作为判断依据
        """
        last_binlogs = self._get_log_from_bklog(
            collector="mssql_binlog_result",
            start_time=query_time - timedelta(days=BACKUP_LOG_RANGE_DAYS),
            end_time=query_time,
            query_string=f"""cluster_id: {self.cluster.id} """,
            size=1,
            sort_rule="desc",
        )
        if not last_binlogs:
            raise Exception(_("集群【{}】最近的{}天里找不到日志备份").format(self.cluster.name, BACKUP_LOG_RANGE_DAYS))

        return last_binlogs[0]["backup_task_start_time"]

    def query_last_log_time_from_model(self, query_time: datetime):
        """
        基于 Model 查询集群的最近一次上报的备份时间
        拿最新的一条备份记录的备份开始时间的作为判断依据
        """
        last_binlog_qs = SQLServerBinlogResult.objects.filter(
            cluster_id=self.cluster.id,
            backup_task_start_time__gte=query_time - timedelta(days=BACKUP_LOG_RANGE_DAYS),
            backup_task_start_time__lte=query_time,
        ).order_by("-backup_task_start_time")[:1]

        last_binlogs = list(last_binlog_qs.values())
        if not last_binlogs:
            raise Exception(_("集群【{}】最近的{}天里找不到日志备份").format(self.cluster.immute_domain, BACKUP_LOG_RANGE_DAYS))

        return last_binlogs[0]["backup_task_start_time"]
