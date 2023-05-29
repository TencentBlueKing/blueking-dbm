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
from typing import Any, Dict, List

from django.db.models import Q
from django.utils.translation import ugettext as _

from backend.components.bklog.handler import BKLogHandler
from backend.db_meta.enums import ClusterType
from backend.db_meta.enums.comm import SystemTagEnum
from backend.db_meta.models import Cluster
from backend.db_services.mongodb.restore.constants import BACKUP_LOG_RANGE_DAYS, PitrFillType
from backend.exceptions import AppBaseException
from backend.ticket.constants import TicketType
from backend.ticket.models import ClusterOperateRecord, Ticket
from backend.utils.time import find_nearby_time, timezone2timestamp


class MongoDBRestoreHandler(object):
    """mongodb定点构造函数封装"""

    def __init__(self, cluster_id: int):
        self.cluster = Cluster.objects.get(id=cluster_id)

    @staticmethod
    def _get_log_from_bklog(collector: str, start_time: datetime, end_time: datetime, query_string="*") -> List[Dict]:
        return BKLogHandler.query_logs(collector, start_time, end_time, query_string)

    def _query_latest_log_and_index(self, rollback_time: datetime, query_string: str, time_key: str, flag: int):
        """查询距离rollback_time最近的备份记录"""
        end_time = rollback_time
        start_time = end_time - timedelta(days=BACKUP_LOG_RANGE_DAYS)

        backup_logs = self._get_log_from_bklog(
            collector="mongo_backup_result",
            start_time=start_time,
            end_time=end_time,
            query_string=query_string,
        )
        if not backup_logs:
            raise AppBaseException(_("距离回档时间点7天内没有备份日志").format(rollback_time))

        # 获取距离回档时间最近的全备日志
        backup_logs.sort(key=lambda x: x[time_key])
        time_keys = [log[time_key] for log in backup_logs]
        try:
            latest_backup_log_index = find_nearby_time(time_keys, timezone2timestamp(rollback_time), flag)
        except IndexError:
            raise AppBaseException(_("无法找到时间点{}附近的全备日志记录").format(rollback_time))

        return backup_logs, latest_backup_log_index

    def query_latest_backup_log(self, rollback_time: datetime) -> Dict[str, Any]:
        """
        查询距离rollback_time最近的全备-增量备份文件
        @param rollback_time: 回档时间
        """
        # 获取距离回档时间最近的全备日志
        query_string = f"cluster: {self.cluster.id} AND pitr_file_type: {PitrFillType.FULL}"
        full_backup_logs, full_latest_index = self._query_latest_log_and_index(
            rollback_time, query_string, time_key="pitr_last_pos", flag=1
        )
        latest_full_backup_log = full_backup_logs[full_latest_index]

        # 找到与全备日志pitr_fullname相同的增量备份日志
        pitr_fullname = latest_full_backup_log["pitr_fullname"]
        query_string = (
            f"cluster: {self.cluster.id} AND pitr_file_type: {PitrFillType.INCR} AND pitr_fullname: {pitr_fullname}"
        )
        incr_backup_logs, incr_latest_index = self._query_latest_log_and_index(
            rollback_time, query_string, time_key="pitr_last_pos", flag=0
        )
        # 找到第一个大于等于rollback_time的增量备份ai, 此时a1, a2, ..., ai为合法的增量备份
        incr_backup_logs = incr_backup_logs[: incr_latest_index + 1]

        return {"full_backup_log": latest_full_backup_log, "incr_backup_logs": incr_backup_logs}

    @classmethod
    def _aggregate_ticket_backup_logs(cls, backup_logs):
        """根据单据ID聚合备份记录"""
        ticket_id__logs = defaultdict(list)
        for log in backup_logs:
            ticket_id__logs[int(log["releate_bill_id"])].append(log)

        id__ticket = {ticket.id: ticket for ticket in Ticket.objects.filter(id__in=ticket_id__logs.keys())}
        ticket_backup_logs: List[Dict[str, Any]] = []
        # 获取每个单据的单据信息和备份记录
        for ticket_id, logs in ticket_id__logs.items():
            if ticket_id not in id__ticket:
                continue
            ticket = id__ticket[ticket_id]
            info = {
                "ticket_id": ticket.id,
                "create_at": ticket.create_at,
                "ticket_type": ticket.ticket_type,
                "backup_logs": logs,
            }
            ticket_backup_logs.append(info)

        return ticket_backup_logs

    @classmethod
    def _query_shard_ticket_backup_log(cls, cluster_id, start_time, end_time):
        """查询通过单据备份的分片集群备份记录"""
        backup_logs = cls._get_log_from_bklog(
            collector="mongo_backup_result",
            start_time=start_time,
            end_time=end_time,
            query_string=f"cluster_id: {cluster_id} AND releate_bill_id: /[0-9]*/",
        )
        if not backup_logs:
            raise AppBaseException(_("{}-{}内没有通过单据备份的日志").format(start_time, end_time))

        # 分片集群查询的是每个分片的备份记录
        ticket_backup_logs = cls._aggregate_ticket_backup_logs(backup_logs)
        return ticket_backup_logs

    @classmethod
    def _query_replicaset_ticket_backup_log(cls, cluster_ids, start_time, end_time):
        """查询通过单据备份的副本集集群备份记录"""
        backup_logs = cls._get_log_from_bklog(
            collector="mongo_backup_result",
            start_time=start_time,
            end_time=end_time,
            query_string=f"cluster_type: {ClusterType.MongoReplicaSet} AND releate_bill_id: /[0-9]*/",
        )
        if not backup_logs:
            raise AppBaseException(_("{}-{}内没有通过单据备份的日志").format(start_time, end_time))

        # 副本集群查询的是单个集群的记录
        ticket_backup_logs = cls._aggregate_ticket_backup_logs(backup_logs)

        # 过滤必须包含查询集群的备份记录
        valid_ticket_backup_logs: List[Dict[str, Any]] = []
        for info in ticket_backup_logs:
            log_cluster_ids = [int(log["cluster_id"]) for log in info["backup_logs"]]
            if not set(cluster_ids).issubset(set(log_cluster_ids)):
                continue

            valid_backup_logs = [log for log in info["backup_logs"] if int(log["cluster_id"]) in cluster_ids]
            info["backup_logs"] = valid_backup_logs
            valid_ticket_backup_logs.append(info)

        return valid_ticket_backup_logs

    @classmethod
    def query_ticket_backup_log(
        cls, cluster_ids: List[int], cluster_type: str, start_time: datetime, end_time: datetime
    ):
        """
        查询通过单据备份的集群备份记录
        @param cluster_ids: 集群ID列表
        @param cluster_type: 集群类型
        @param start_time: 查询开始时间
        @param end_time: 查询结束时间
        """
        if cluster_type == ClusterType.MongoShardedCluster:
            # 分片集只有一个集群
            return cls._query_shard_ticket_backup_log(cluster_ids[0], start_time, end_time)
        else:
            return cls._query_replicaset_ticket_backup_log(cluster_ids, start_time, end_time)

    @classmethod
    def query_clusters_backup_log(
        cls, cluster_ids: List[int], cluster_type: str, start_time: datetime, end_time: datetime
    ):
        """
        通过集群ID查询集群的备份记录
        @param cluster_ids: 集群ID列表
        @param cluster_type: 集群类型
        @param start_time: 查询开始时间
        @param end_time: 查询结束时间
        """
        # 根据集群类型和集群ID过滤备份记录
        cluster_id_query = " OR ".join(map(str, cluster_ids))
        backup_logs = cls._get_log_from_bklog(
            collector="mongo_backup_result",
            start_time=start_time,
            end_time=end_time,
            query_string=f"cluster_type: {cluster_type} AND cluster_id: {cluster_id_query}",
        )

        # 根据集群ID聚合备份记录
        cluster_id__backup_logs: Dict[int, List[Dict]] = defaultdict(list)
        for log in backup_logs:
            cluster_id__backup_logs[int(log["cluster_id"])].append(log)
        return cluster_id__backup_logs

    @classmethod
    def query_restore_record(cls, bk_biz_id: int, limit: int, offset: int, filters: Q = None):
        """
        查询MongoDB回档临时集群的记录
        @param bk_biz_id: 业务ID
        @param limit: 单页限制
        @param offset: 单页起始
        @param filters: 过滤参数
        """
        filters = filters or Q()
        # 查询临时集群信息
        temp_clusters = (
            Cluster.objects.prefetch_related("storageinstance_set", "proxyinstance_set")
            .filter(
                bk_biz_id=bk_biz_id,
                cluster_type__in=[ClusterType.MongoShardedCluster, ClusterType.MongoReplicaSet],
                tag__name=SystemTagEnum.TEMPORARY,
            )
            .filter(filters)
        )
        temp_clusters_count = temp_clusters.count()
        temp_clusters = temp_clusters[offset : limit + offset]
        id__temp_cluster = {cluster.id: cluster for cluster in temp_clusters}

        # 查询定点回档记录
        records = ClusterOperateRecord.objects.select_related("ticket").filter(
            cluster_id__in=id__temp_cluster.keys(), ticket__ticket_type=TicketType.MONGODB_RESTORE
        )
        # 查询源集群的信息
        source_cluster_names = [cluster.name.rsplit("-", 2)[0] for cluster in temp_clusters]
        source_clusters = Cluster.objects.filter(
            bk_biz_id=bk_biz_id,
            cluster_type__in=[ClusterType.MongoShardedCluster, ClusterType.MongoReplicaSet],
            name__in=source_cluster_names,
        )
        name__source_cluster = {cluster.name: cluster for cluster in source_clusters}
        # 获取源集群和构造集群的操作记录
        cluster_records_map = ClusterOperateRecord.get_cluster_records_map(
            cluster_ids=[*id__temp_cluster.keys(), *list(source_clusters.values_list("id", flat=True))]
        )

        # 填充定点回档实例记录
        restore_records: List[Dict[str, Any]] = []
        for record in records:
            ticket_data = record.ticket.details
            target_cluster = id__temp_cluster.get(record.cluster_id)
            storage_machines = list(target_cluster.storageinstance_set.all().values_list("machine__ip", flat=True))
            proxy_machines = list(target_cluster.proxyinstance_set.all().values_list("machine__ip", flat=True))
            source_cluster_name = target_cluster.name.rsplit("-", 2)[0]
            restore_records.append(
                {
                    "source_cluster": {
                        **name__source_cluster[source_cluster_name].simple_desc,
                        "access_port": name__source_cluster[source_cluster_name].access_port,
                        "operations": cluster_records_map[name__source_cluster[source_cluster_name].id],
                    },
                    "target_cluster": {
                        **target_cluster.simple_desc,
                        "access_port": target_cluster.access_port,
                        "operations": cluster_records_map[target_cluster.id],
                    },
                    "target_cluster_id": target_cluster.id,
                    "target_nodes": list({*storage_machines, *proxy_machines}),
                    "ticket_id": record.ticket.id,
                    "instance_per_host": record.ticket.details.get("instance_per_host"),
                    "ns_filter": record.ticket.details.get("ns_filter"),
                    "rollback_time": ticket_data.get("rollback_time", ""),
                    "backupinfo": ticket_data.get("backupinfo", {}),
                }
            )

        return {"count": temp_clusters_count, "results": restore_records}
