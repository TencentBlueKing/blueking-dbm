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

from django.utils.translation import ugettext as _

from backend import env
from backend.components.bklog.client import BKLogApi
from backend.db_meta.enums import ClusterType, InstanceInnerRole
from backend.db_meta.models.cluster import Cluster
from backend.db_services.redis.rollback.constants import BACKUP_LOG_ROLLBACK_TIME_RANGE_DAYS
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
                "size": 1000,
                "sort_list": [["dtEventTimeStamp", "asc"], ["gseIndex", "asc"], ["iterationIndex", "asc"]],
            },
            use_admin=True,
        )
        backup_logs = []
        for hit in resp["hits"]["hits"]:
            raw_log = json.loads(hit["_source"]["log"])
            backup_logs.append({pascal_to_snake(key): value for key, value in raw_log.items()})

        return backup_logs

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
                str2datetime(log["start_time"]).replace(tzinfo=None) > end_time
                or str2datetime(log["start_time"]).replace(tzinfo=None) < start_time
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
            "size": bk_binlog["backup_file_size"],
            "source_ip": bk_binlog["server_ip"],
            "task_id": bk_binlog["backup_taskid"],
            "file_name": bk_binlog["backup_file"].split("/")[-1],
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
            raise AppBaseException(_("无法找到小于时间点{}附近的日志记录，请检查时间点的合法性或稍后重试").format(start_time))
        # 转化为直接查询备份系统返回的格式
        backup_binlog = self.convert_to_backup_system_format(latest_start_time_binlog)
        binlog_file_list.append(backup_binlog)

        try:
            # 获取大于且最接近end_time 的一个binlog文件 ；flag为0，则搜索大于或等于end_time的最近时间点
            latest_end_time_binlog = filtered_binlogs[find_nearby_time(time_keys, datetime2str(end_time), 0)]
        except IndexError:
            raise AppBaseException(_("无法找到大于时间点{}附近的日志记录，请检查时间点的合法性或稍后重试").format(end_time))

        # 转化为直接查询备份系统返回的格式
        backup_binlog = self.convert_to_backup_system_format(latest_end_time_binlog)
        binlog_file_list.append(backup_binlog)
        return binlog_file_list
