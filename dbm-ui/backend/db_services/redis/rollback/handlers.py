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
import logging.config
from datetime import datetime, timedelta
from typing import Any, Dict, List, Union

from django.utils.translation import gettext as _

from backend import env
from backend.components.bklog.client import BKLogApi
from backend.db_meta.enums import ClusterType, InstanceInnerRole
from backend.db_meta.models.cluster import Cluster
from backend.db_services.redis.rollback.constants import (
    BACKUP_LOG_ROLLBACK_TIME_RANGE_DAYS,
    BACKUP_LOG_ROLLBACK_TIME_RANGE_HOURS,
)
from backend.exceptions import AppBaseException
from backend.utils.string import pascal_to_snake
from backend.utils.time import datetime2str, find_nearby_time, str2datetime

logger = logging.getLogger("flow")


class DataStructureHandler:
    """
    封装数据构造相关接口
    """

    def __init__(self, cluster_id: int):
        self.cluster = Cluster.objects.get(id=cluster_id)

    def query_latest_backup_log(self, rollback_time: datetime, host_ip: str, port: int) -> Dict[str, Any]:
        # 日志平台查询
        end_time = rollback_time
        start_time = end_time - timedelta(days=BACKUP_LOG_ROLLBACK_TIME_RANGE_DAYS)
        backup_logs = self.redis_query_backup_log_from_bklog(
            start_time=start_time, end_time=end_time, host_ip=host_ip, port=port
        )

        if not backup_logs:
            raise AppBaseException(_("无法查找到在时间范围内{}-{}，主机{}的全备份日志").format(start_time, end_time, host_ip))

        backup_logs.sort(key=lambda x: x["start_time"])
        time_keys = [log["start_time"] for log in backup_logs]
        try:
            latest_log = backup_logs[find_nearby_time(time_keys, datetime2str(rollback_time), 1)]
        except IndexError:
            raise AppBaseException(_("没有找到小于时间点{}附近的备份日志记录，请检查时间点的合法性或稍后重试").format(rollback_time))
        # 转化为直接查询备份系统返回的格式
        return self.convert_to_backup_system_format(latest_log)

    def redis_query_backup_log_from_bklog(
        self, start_time: datetime, end_time: datetime, host_ip: str, port: int
    ) -> List[Dict]:
        """
        通过日志平台查询集群的时间范围内的备份记录
        :param start_time: 开始时间
        :param end_time: 结束时间
        :param host_ip: 源机器
        :param port: 实例端口
        """

        cluster_domain = self.cluster.immute_domain
        status = "to_backup_system_success"
        backup_logs = self._get_log_from_bklog(
            collector="redis_fullbackup_result",
            start_time1=start_time,
            end_time1=end_time,
            # 得到的是上传成功的： to_backup_system_success
            query_string=f"domain: {cluster_domain} AND status: {status} server_ip: {host_ip} AND server_port: {port}",
            # 得到的是上传系统中的：to_backup_system_start ，这种状态有必要存在吗？
            # query_string=f'log: "domain: \\"{cluster_domain}\\""',
        )
        return backup_logs

    def _get_log_from_bklog(self, collector, start_time1, end_time1, query_string="*") -> List[Dict]:
        """
        从日志平台获取对应采集项的日志
        @param collector: 采集项名称
        @param start_time: 开始时间
        @param end_time: 结束时间
        @param query_string: 过滤条件
        """
        resp = BKLogApi.esquery_search(
            {
                "indices": f"{env.DBA_APP_BK_BIZ_ID}_bklog.{collector}",
                "start_time": datetime2str(start_time1),
                "end_time": datetime2str(end_time1),
                # 这里需要精确查询集群域名，所以可以通过log: "key: \"value\""的格式查询
                "query_string": query_string,
                "start": 0,
                "size": 6000,
                "sort_list": [["dtEventTimeStamp", "asc"], ["gseIndex", "asc"], ["iterationIndex", "asc"]],
            },
            use_admin=True,
        )
        backup_logs = []
        for hit in resp["hits"]["hits"]:
            raw_log = json.loads(hit["_source"]["log"])
            backup_logs.append({pascal_to_snake(key): value for key, value in raw_log.items()})

        return backup_logs

    def get_bklog_by_domain(self, start_time: datetime, end_time: datetime) -> List[Dict]:
        """
        通过日志平台查询集群的时间范围内的备份记录
        :param start_time: 开始时间
        :param end_time: 结束时间
        """

        cluster_domain = self.cluster.immute_domain
        status = "to_backup_system_success"
        backup_logs = self._get_log_from_bklog(
            collector="redis_fullbackup_result",
            start_time1=start_time,
            end_time1=end_time,
            # 得到的是该集群上传成功的： to_backup_system_success
            query_string=f"domain: {cluster_domain} AND status: {status} ",
        )
        return backup_logs

    def get_bklog_by_identify(
        self, backup_identify: str, start_time: datetime = None, end_time: datetime = None
    ) -> List[Dict]:
        """
        通过日志平台按 (cluster_domain, backup_identify) 精确查询"一次备份"产生的全部分片记录.
        数据量上限	6000 条硬顶
        重要: backup_identify **不是全局唯一** 的:
        - Flow 场景 (BILL/FLUSH/FOREVER/DTS-{uid}-{ts}): 一个单据涉及多个集群时,
          所有集群共用同一个 identify;
        - 例行备份 (SCHEDULED-{YYYYMMDDHH}): 全业务所有 Redis 集群在同一小时的
          identify 完全相同;
        - Reupload (REUPLOAD-{ts}): 同一秒重上报多集群时 identify 相同.

        因此本方法**始终**使用当前实例的 self.cluster.immute_domain 作为过滤条件, identify
        只在集群维度内定位"一次备份". 调用方无法通过 identify 跨集群查询.

        :param backup_identify: 备份批次标识 (集群内唯一)
        :param start_time:      查询起始时间; 不传时默认往前推
                                BACKUP_LOG_ROLLBACK_TIME_RANGE_DAYS 天
        :param end_time:        查询结束时间; 不传时默认取当前时间
        :return: 该集群该批次的原始 bklog 记录 (未做格式转换)
        """
        if not backup_identify:
            raise AppBaseException(_("backup_identify 不能为空"))

        if end_time is None:
            end_time = datetime.now()
        if start_time is None:
            start_time = end_time - timedelta(days=BACKUP_LOG_ROLLBACK_TIME_RANGE_DAYS)

        cluster_domain = self.cluster.immute_domain
        status = "to_backup_system_success"
        # 语义: 集群维度 (domain) + 批次维度 (backup_identify) + 状态维度 (status) 三元锁定
        # backup_identify 单独不能定位到"一次备份", 必须与 domain 组合
        backup_logs = self._get_log_from_bklog(
            collector="redis_fullbackup_result",
            start_time1=start_time,
            end_time1=end_time,
            query_string=(
                f"domain: {cluster_domain} AND status: {status} " f'AND backup_identify: "{backup_identify}"'
            ),
        )
        return backup_logs

    def query_backup_logs_by_identify(
        self, backup_identify: str, start_time: datetime = None, end_time: datetime = None
    ) -> List[Dict[str, Union[int, Any]]]:
        """
        按 (当前集群, backup_identify) 精确聚齐一次备份的所有分片, 并转换为备份系统标准格式.

        与 query_donmain_backup_log 的差异:
        - query_donmain_backup_log 用 "最近 N 天 + 3 小时时间窗口" 聚批, 精度较低;
        - 本方法在当前集群下用 backup_identify 精确聚批, 直接对应"一次备份行为",
          不需要时间窗口.

        注意: backup_identify 不是全局唯一, 必须绑定当前 self.cluster; 若调用方需要跨
        集群查询同一单据触发的所有备份, 请对每个 cluster 分别 new 一个 handler 后调用本方法.

        :param backup_identify: 备份批次标识
        :param start_time:      查询起始时间(可选)
        :param end_time:        查询结束时间(可选)
        :return: 与 query_donmain_backup_log 相同格式的备份文件列表
        """
        backup_logs = self.get_bklog_by_identify(
            backup_identify=backup_identify, start_time=start_time, end_time=end_time
        )
        if not backup_logs:
            raise AppBaseException(
                _("无法查找到集群{}下 backup_identify={} 的全备份日志").format(self.cluster.immute_domain, backup_identify)
            )

        logger.info(
            _("集群{} 按 backup_identify={} 命中 {} 条备份记录").format(
                self.cluster.immute_domain, backup_identify, len(backup_logs)
            )
        )
        backup_logs.sort(key=lambda x: x["start_time"])

        # 转换为备份系统标准格式
        return [self.convert_to_backup_system_format(log) for log in backup_logs]

    def list_backup_identifies(
        self, start_time: datetime, end_time: datetime, status: str = "to_backup_system_success"
    ) -> List[Dict[str, Any]]:
        """
        枚举当前集群在指定时间范围内出现过的所有 backup_identify, 附带每个批次的聚合元信息.
        后期可以改成： 查：tb_redis_backup_result 位于 bk_dbm_report 数据库
        使用场景:
        - 前端"备份批次列表"下拉框, 让用户按批次选择恢复
        - 单据结束页面回显"本次单据触发的备份批次"
        - 运维排查"某天该集群做过哪些备份"

        实现说明:
        - 复用 _get_log_from_bklog 拉当前集群时间窗内的原始记录, 应用层按 backup_identify
          分组去重, 与项目现有 set() 去重风格保持一致;
        - 数据量控制: _get_log_from_bklog size=6000, 单集群 backup_identify 一般是"1天 1~24 批 *
          N 分片" 量级, 不会触发上限. 若未来上限成为问题, 可再考虑走 ES aggregations.

        :param start_time: 查询起始时间
        :param end_time:   查询结束时间
        :param status:     备份状态过滤; 默认只列出"上传备份系统成功"的批次
        :return: 批次列表, 每个元素形如:
                 {
                     "backup_identify": "SCHEDULED-2026073003",
                     "backup_type":      "SCHEDULED",         # 从 identify 前缀提取
                     "shard_count":      12,                  # 该批次记录数
                     "earliest_start":   "2026-07-30T03:00:11+08:00",
                     "latest_end":       "2026-07-30T03:04:22+08:00",
                     "total_file_size":  123456789,           # 该批次总大小
                     "roles":            ["slave"],           # 涉及的实例角色
                 }
                 按 earliest_start 倒序 (最新的批次在前).
        """
        cluster_domain = self.cluster.immute_domain
        query_string = f"domain: {cluster_domain}"
        if status:
            query_string = f"{query_string} AND status: {status}"

        raw_logs = self._get_log_from_bklog(
            collector="redis_fullbackup_result",
            start_time1=start_time,
            end_time1=end_time,
            query_string=query_string,
        )
        if not raw_logs:
            logger.info(_("集群{} 在时间范围 {} ~ {} 未发现任何备份批次").format(cluster_domain, start_time, end_time))
            return []

        # 按 backup_identify 分组聚合
        buckets: Dict[str, Dict[str, Any]] = {}
        for log in raw_logs:
            identify = log.get("backup_identify") or ""
            if not identify:
                # 兜底: 未上报 identify 的老记录跳过 (它们无法用于批次维度定位)
                continue

            bucket = buckets.setdefault(
                identify,
                {
                    "backup_identify": identify,
                    "backup_type": self._extract_identify_prefix(identify),
                    "shard_count": 0,
                    "earliest_start": log["start_time"],
                    "latest_end": log["end_time"],
                    "total_file_size": 0,
                    "roles": set(),
                },
            )
            bucket["shard_count"] += 1
            bucket["total_file_size"] += int(log.get("backup_file_size") or 0)
            if log.get("role"):
                bucket["roles"].add(log["role"])
            if log["start_time"] < bucket["earliest_start"]:
                bucket["earliest_start"] = log["start_time"]
            if log["end_time"] > bucket["latest_end"]:
                bucket["latest_end"] = log["end_time"]

        # set 转 list 便于 json 序列化, 并按最新时间倒序返回
        result = []
        for bucket in buckets.values():
            bucket["roles"] = sorted(bucket["roles"])
            result.append(bucket)
        result.sort(key=lambda x: x["earliest_start"], reverse=True)

        logger.info(_("集群{} 在时间范围 {} ~ {} 发现 {} 个备份批次").format(cluster_domain, start_time, end_time, len(result)))
        return result

    @staticmethod
    def _extract_identify_prefix(backup_identify: str) -> str:
        """
        从 backup_identify 提取批次类型前缀:
        - BILL{uid}-{ts}     -> BILL 普通单据备份：
        - FLUSH{uid}-{ts}    -> FLUSH 清档前备份：
        - FOREVER{uid}-{ts}  -> FOREVER 集群下架永久备份：实例下架永久备份：
        - DTS{uid}-{ts}      -> DTS DTS 目标集群清档前备份：
        - SCHEDULED-{ts}     -> SCHEDULED 周期备份生成格式：
        - REUPLOAD-{ts}      -> REUPLOAD 迁移DBM备份
        - 其它未识别格式返回 UNKNOWN
        """
        known_prefixes = ("SCHEDULED", "REUPLOAD", "FOREVER", "FLUSH", "BILL", "DTS")
        for prefix in known_prefixes:
            if backup_identify.startswith(prefix):
                return prefix
        return "UNKNOWN"

    def query_donmain_backup_log(self, rollback_time: datetime) -> List[Dict[str, Union[int, Any]]]:
        # 1、通过集群名从日志平台查询集群信息,首先是扩大范围查询到离回档时间点最近的一个备份文件
        end_time = rollback_time
        start_time = end_time - timedelta(days=BACKUP_LOG_ROLLBACK_TIME_RANGE_DAYS)
        backup_logs = self.get_bklog_by_domain(start_time=start_time, end_time=end_time)
        if not backup_logs:
            raise AppBaseException(
                _("无法查找到在时间范围内{}-{}，集群{}的全备份日志").format(start_time, end_time, self.cluster.immute_domain)
            )
        logger.info(_("大范围内的查询结果 backup_logs: {}".format(backup_logs)))
        backup_logs.sort(key=lambda x: x["start_time"])
        time_keys = [log["start_time"] for log in backup_logs]
        try:
            # 获取最近的一个备份文件，然后获取到时间
            latest_log = backup_logs[find_nearby_time(time_keys, datetime2str(rollback_time), 1)]
            logger.info(_("latest_log:{},start_time:{}".format(latest_log, latest_log["start_time"])))
        except IndexError:
            raise AppBaseException(_("没有找到小于时间点{}附近的备份日志记录，请检查时间点的合法性或稍后重试").format(rollback_time))

        # 2、缩小范围过滤3小时内一般是同一批次备份的
        latest_log_start_time = str2datetime(latest_log["start_time"])
        start_time = latest_log_start_time - timedelta(hours=BACKUP_LOG_ROLLBACK_TIME_RANGE_HOURS)

        # 指定时间内备份文件
        backup_logs_cluster_same_batch = []
        for log in backup_logs:
            # 获取end_time到start_time时间范围内的备份文件
            if (
                str2datetime(log["start_time"]).replace(tzinfo=end_time.tzinfo) > end_time
                or str2datetime(log["start_time"]).replace(tzinfo=start_time.tzinfo) < start_time
            ):
                continue
            # 转化为直接查询备份系统返回的格式
            backup_binlog = self.convert_to_backup_system_format(log)
            backup_logs_cluster_same_batch.append(backup_binlog)
            logger.info(_("backup_logs_cluster_same_batch:{}".format(backup_logs_cluster_same_batch)))

        return backup_logs_cluster_same_batch

    def query_binlog_from_bklog(
        self,
        start_time: datetime,
        end_time: datetime,
        host_ip: str = None,
        port: int = None,
        kvstorecount: str = None,
        tendis_type: str = None,
        minute_range: int = 120,
    ) -> List[Dict]:
        """
        通过日志平台查询集群的时间范围内的binlog记录
        :param start_time: 开始时间
        :param end_time: 结束时间
        :param host_ip: 过滤的主机IP
        :param port: 端口
        :param kvstorecount: tendisplus kvstore 的值
        :param tendis_type: tendis 类型
        :param minute_range: 放大的前后时间范围
        """

        if not host_ip:
            master = self.cluster.storageinstance_set.get(instance_inner_role=InstanceInnerRole.MASTER)
            host_ip, port = master.machine.ip, master.port
        status = "to_backup_system_success"
        binlogs = self._get_log_from_bklog(
            collector="redis_binlog_backup_result",
            # 时间范围前后放大避免日志平台上传延迟
            # binlog每隔20分钟做备份上传，上传可能超时，上传超时时间 2小时; 这里的时间是大范围内的
            start_time1=start_time - timedelta(minutes=minute_range),
            end_time1=end_time + timedelta(minutes=minute_range),
            query_string=f"server_ip: {host_ip} AND server_port: {port} AND status:{status}",
        )

        if not binlogs:
            raise AppBaseException(_("无法查找到在时间范围内{}-{}，主机{}的binlog日志").format(start_time, end_time, host_ip))
        # 指定时间内单个节点的binlog备份文件
        binlog_file_list = []
        for log in binlogs:
            # 获取end_time到start_time时间范围内的binlog文件
            if (
                str2datetime(log["start_time"]).replace(tzinfo=end_time.tzinfo) > end_time
                or str2datetime(log["start_time"]).replace(tzinfo=start_time.tzinfo) < start_time
            ):
                continue
            # 转化为直接查询备份系统返回的格式
            backup_binlog = self.convert_to_backup_system_format(log)
            binlog_file_list.append(backup_binlog)

        # tendisplus才有 kvstorecount 的区别
        if kvstorecount is not None:
            # 每个节点又分不同kvstore
            for i in range(0, int(kvstorecount)):
                # tendisplus 过滤不同kvstore
                kvstore_filter = "-".join([str(host_ip), str(port), str(i)])
                # 添加instance不同kvstore的小于且最接近start_time和大于且最接近end_time的binlog备份文件
                binlog_file_list.extend(
                    self.get_specified_format_binlog(binlogs, kvstore_filter, start_time, end_time)
                )

            # 每个节点又分不同kvstore,校验binlog完整性
            for i in range(0, int(kvstorecount)):
                # 过滤不同kvstore
                kvstore_filter = "-".join([str(host_ip), str(port), str(i)])
                # 过滤后的包含指定kvstore的binlog列表
                kvstore_binlogs_list = [binlog for binlog in binlog_file_list if kvstore_filter in binlog["file_name"]]
                # 至少会包含两个binlog文件,第一个BackupStart小于 start_time, 第二个BackupStart 大于 end_time
                if len(kvstore_binlogs_list) < 2:
                    logger.error(_("binlog全部文件信息:{}".format(binlog_file_list)))
                    raise AppBaseException(
                        _("节点{}:{}的kvstore:{}的binlog 数少于2，不符合预期，请检查error日志").format(host_ip, port, i)
                    )

                # 检查是否获取到所有binlog
                bin_index_list = self.__is_get_all_binlog(kvstore_binlogs_list, tendis_type)
                if len(bin_index_list) != 0:
                    raise AppBaseException(
                        _("重复/缺失的binlog共{}个,重复/缺失的binlog index是:{},详细信息请查看error日志").format(
                            len(bin_index_list), bin_index_list
                        )
                    )

        elif kvstorecount is None:
            # ssd 过滤不同instance
            instance_filter = "-".join([str(host_ip), str(port)])
            # 添加instance小于且最接近start_time和大于且最接近end_time的binlog备份文件
            binlog_file_list.extend(self.get_specified_format_binlog(binlogs, instance_filter, start_time, end_time))

            binlogs_list = [binlog for binlog in binlog_file_list if instance_filter in binlog["file_name"]]
            # 至少会包含两个binlog文件,第一个BackupStart小于 start_time, 第二个BackupStart 大于 end_time
            if len(binlogs_list) < 2:
                logger.error(_("binlog全部文件信息:{}".format(binlog_file_list)))
                raise AppBaseException(_("节点{}:{}的binlog 数少于2，不符合预期，请检查error日志").format(host_ip, port))

            # 检查是否获取到所有binlog
            bin_index_list = self.__is_get_all_binlog(binlogs_list, tendis_type)
            if len(bin_index_list) != 0:
                raise AppBaseException(
                    _("重复/缺失的binlog共{}个,重复/缺失的binlog index是:{},详细信息请查看error日志").format(
                        len(bin_index_list), bin_index_list
                    )
                )

        return binlog_file_list

    @staticmethod
    def __is_get_all_binlog(binlogs_list: List, tendis_type: str):
        # 检查是否获取到所有binlog

        # 1. 获取binlog_file_list里每个字典的file_name值组成新的binlog_file_name_list
        binlog_file_name_list = [item["file_name"] for item in binlogs_list]

        # 2. 根据binlog_file_name_list如 0002437，0002438来排序
        if tendis_type == ClusterType.TendisplusInstance.value:
            # binlog-xxxx-30002-0-0002437-20230911164611.log.zst
            sorted_binlog_file_name_list = sorted(binlog_file_name_list, key=lambda x: int(x.split("-")[4]))
        elif tendis_type == ClusterType.TendisSSDInstance.value:
            # binlog-xxxx-30002-0002500-20230913101206.log.zst
            sorted_binlog_file_name_list = sorted(binlog_file_name_list, key=lambda x: int(x.split("-")[3]))
        else:
            raise NotImplementedError("Not supported tendis type: %s" % tendis_type)
        # 3. 判断是否连续重复
        missing_files = []
        duplicate_files = set()
        previous_number = None
        previous_file_name = None

        for file_name in sorted_binlog_file_name_list:
            if tendis_type == ClusterType.TendisplusInstance.value:
                current_index_number = int(file_name.split("-")[4])
            elif tendis_type == ClusterType.TendisSSDInstance.value:
                current_index_number = int(file_name.split("-")[3])
            else:
                raise NotImplementedError("Not supported tendis type: %s" % tendis_type)
            if current_index_number in duplicate_files:
                logger.error(_("文件序号重复: {}，文件重复: {}".format(current_index_number, file_name)))
                return [current_index_number]
            # 检查文件index序号是否连续
            if previous_number is not None and current_index_number - previous_number > 1:
                logger.error(_("缺失时打印当前文件:{}和上一个文件: {}".format(previous_file_name, file_name)))
                missing_files.extend(range(previous_number + 1, current_index_number))
            duplicate_files.add(current_index_number)
            previous_number = current_index_number
            previous_file_name = file_name
        # 4. 判断是否连续的结果
        if missing_files:
            logger.error(_("缺少的文件序号: {}").format(missing_files))
        return missing_files

    @staticmethod
    def convert_to_backup_system_format(bk_binlog):
        return {
            "file_tag": bk_binlog["backup_tag"],
            "status": bk_binlog["status"],
            "uptime": bk_binlog["end_time"],
            # latest_log["start_time"] 是全备份快照开始的时间-》文件最后写入时间作为binlog查询开始的时间
            "file_last_mtime": bk_binlog["start_time"],
            "size": int(bk_binlog["backup_file_size"]),
            "source_ip": bk_binlog["server_ip"],
            "server_port": bk_binlog["server_port"],
            "task_id": bk_binlog["backup_taskid"],
            "file_name": bk_binlog["backup_file"].split("/")[-1],
            # segment信息
            "shard_value": bk_binlog["shard_value"],
        }

    def get_specified_format_binlog(
        self, binlogs: List, filter: str, start_time: Union[datetime, str], end_time: Union[datetime, str]
    ) -> list:
        """
        从批量大范围的备份记录中过滤出特定的instance或者kvstore的小于且最接近start_time和大于且最接近end_time的binlog备份文件
        :param binlogs: 大范围的binlog备份记录
        :param filter: 过滤的的包含的内容
        :param start_time: 开始时间
        :param end_time: 结束时间
        """
        logger.info("+===get_specified_format_binlog filter:{} ===++++ ".format(filter))
        binlog_file_list = []
        # 过滤后的包含指定filter的binlog列表
        filtered_binlogs = [binlog for binlog in binlogs if filter in binlog["backup_file"].split("/")[-1]]
        filtered_binlogs.sort(key=lambda x: x["start_time"])
        # 时间键的列表，应按升序排序
        time_keys = [log["start_time"] for log in filtered_binlogs]
        try:
            # 获取小于且最接近start_time 的一个binlog文件 ；flag为1，则搜索小于或等于start_time的最近时间点
            latest_start_time_binlog = filtered_binlogs[find_nearby_time(time_keys, datetime2str(start_time), 1)]
        except IndexError:
            raise AppBaseException(_("无法找到filter:{}小于时间点{}附近的日志记录，请检查时间点的合法性或稍后重试").format(filter, start_time))
        # 转化为直接查询备份系统返回的格式
        backup_binlog = self.convert_to_backup_system_format(latest_start_time_binlog)
        binlog_file_list.append(backup_binlog)

        try:
            # 获取大于且最接近end_time 的一个binlog文件 ；flag为0，则搜索大于或等于end_time的最近时间点
            latest_end_time_binlog = filtered_binlogs[find_nearby_time(time_keys, datetime2str(end_time), 0)]
        except IndexError:
            raise AppBaseException(_("无法找到filter:{}大于时间点{}附近的日志记录，请检查时间点的合法性或稍后重试").format(filter, end_time))

        # 转化为直接查询备份系统返回的格式
        backup_binlog = self.convert_to_backup_system_format(latest_end_time_binlog)
        binlog_file_list.append(backup_binlog)
        return binlog_file_list
