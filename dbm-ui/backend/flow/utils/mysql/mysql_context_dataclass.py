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
from dataclasses import dataclass, field
from typing import Dict, List


@dataclass()
class SingleApplyAutoContext:
    """
    定义单节点申请的上下文dataclass类(资源池模式)
    """

    new_ip: str = None  # 代表在资源池分配到的每个单节点集群的新的ip
    time_zone_info: dict = field(default_factory=dict)  # 新机器的时区设置信息

    @staticmethod
    def get_new_ip_var_name() -> str:
        return "new_ip"

    @staticmethod
    def get_time_zone_var_name() -> str:
        return "time_zone_info"


@dataclass()
class SingleApplyManualContext:
    """
    定义单节点申请的上下文dataclass类(手输ip模式)
    """

    time_zone_info: dict = field(default_factory=dict)  # 新机器的时区设置信息

    @staticmethod
    def get_time_zone_var_name() -> str:
        return "time_zone_info"


@dataclass()
class ClusterInfoContext:
    """
    定义集群信息
    """

    master_ip_sync_info: dict = field(default_factory=dict)
    change_master_info: dict = field(default_factory=dict)
    latest_backup_file: str = None
    backupinfo: dict = None
    backup_time: str = None
    backup_role: str = None
    binlog_files: str = None
    binlog_files_list: list = None
    master_backup_file: dict = None
    slave_backup_file: dict = None
    show_master_status_info: dict = field(default_factory=dict)
    max_open_file: dict = field(default_factory=dict)

    @staticmethod
    def get_sync_info_var_name() -> str:
        return "master_ip_sync_info"


@dataclass()
class HaApplyAutoContext:
    """
    定义主从版申请的上下文dataclass类(资源池模式)
    """

    new_master_ip: str = None  # 代表在资源池分配到的每套HA集群的新的master
    new_slave_ip: str = None  # 代表在资源池分配的每套HA集群的新的slave
    new_proxy_1_ip: str = None  # 代表在资源池分配的每套HA集群的新的proxy_1
    new_proxy_2_ip: str = None  # 代表在资源池分配的每套HA集群的新的proxy_2
    new_all_ips: list = field(default_factory=list)  # 代表在资源池这套集群分配到所有的ip
    new_proxy_ips: list = field(default_factory=list)  # 代表在资源池这套集群分配到所有的proxy_ip
    new_mysql_ips: list = field(default_factory=list)  # 代表在资源池这套集群分配到所有的mysql_ip
    master_ip_sync_info: dict = field(default_factory=dict)  # 代表获取到master的主从复制位点信息
    set_backend_ip: str = None  # proxy设置的后端ip
    time_zone_info: dict = field(default_factory=dict)  # 新机器的时区设置信息

    def get_all_ips(self):
        self.new_all_ips = [self.new_master_ip, self.new_slave_ip, self.new_proxy_1_ip, self.new_proxy_2_ip]

    def set_proxy_backend_ip(self):
        self.set_backend_ip = self.new_master_ip

    @staticmethod
    def get_new_master_ip_var_name() -> str:
        return "new_master_ip"

    @staticmethod
    def get_new_slave_ip_var_name() -> str:
        return "new_slave_ip"

    @staticmethod
    def get_new_proxy_ips_var_list() -> list:
        return ["new_proxy_1_ip", "new_proxy_2_ip"]

    @staticmethod
    def get_new_mysql_ips_var_list() -> list:
        return ["new_master_ip", "new_slave_ip"]

    @staticmethod
    def get_new_all_ips_var_name() -> str:
        return "new_all_ips"

    @staticmethod
    def get_new_proxy_ips_var_name() -> str:
        return "new_proxy_ips"

    @staticmethod
    def get_new_mysql_ips_var_name() -> str:
        return "new_mysql_ips"

    @staticmethod
    def get_time_zone_var_name() -> str:
        return "time_zone_info"

    @staticmethod
    def get_sync_info_var_name() -> str:
        return "master_ip_sync_info"


@dataclass()
class HaApplyManualContext:
    """
    定义主从版申请的上下文dataclass类(手输ip模式)
    """

    master_ip_sync_info: dict = field(default_factory=dict)  # 代表获取到master的主从复制位点信息
    time_zone_info: dict = field(default_factory=dict)  # 新机器的时区设置信息

    @staticmethod
    def get_time_zone_var_name() -> str:
        return "time_zone_info"

    @staticmethod
    def get_sync_info_var_name() -> str:
        return "master_ip_sync_info"


@dataclass()
class MySQLTruncateDataContext:
    ip: str = None
    port: int = None
    targets: Dict = None
    # show_open_fence: bool = None
    old_new_map: dict = None
    db_table_filter_regex: str = None
    db_filter_regex: str = None

    @staticmethod
    def get_master_ip_var_name() -> str:
        return "ip"


@dataclass()
class MysqlChecksumContext:
    """
    定义checksum的上下文dataclass
    """

    master_access_slave_user: str = None
    master_access_slave_password: str = None
    is_consistent: bool = True
    """
    {"pt_stderr":"",
    "summaries":
    [
    {"ts":"2022-11-07T18:51:59+08:00","errors":0,"diffs":1,"rows":2,
    "diff_rows":0,"chunks":1,"skipped":0,"time":0,"table":"db1.tb1"},
    {"ts":"2022-11-07T18:52:00+08:00","errors":0,"diffs":0,"rows":0,
    "diff_rows":0,"chunks":1,"skipped":0,"time":0,"table":"mysql.columns_priv"}
    ],
    "pt_exit_flags":[{"flag":"TABLE_DIFF","meaning":"At least one diff was found","bit_value":16}]}
    """
    checksum_report: dict = None


@dataclass()
class MysqlPartitionContext:
    """
    定义checksum的上下文dataclass
    """

    execute_objects: dict = None


@dataclass()
class SemanticCheckContext:
    """
    定义SQL语义检测的上下文dataclass
    """

    semantic_ip: str = None  # 代表测试的语义实例IP
    semantic_port: int = None  # 代表测试的语义实例端口

    @staticmethod
    def get_semantic_ip_var_name() -> str:
        return "semantic_ip"


# @dataclass()
# class MySQLTableBackupContext:
#     ip: str = None
#     port: int = None
#     # show_open_fence: bool = None
#     regex: str = None
#     backup_report_response: dict = None
#     db_table_filter_regex: str = None
#     db_filter_regex: str = None
#
#     @staticmethod
#     def get_backup_ip_var_name() -> str:
#         return "ip"


@dataclass()
class ClusterSwitchContext:
    """
    定义MySQL集群主从互切/主故障切换/成对切换场景的上下文dataclass类
    """

    master_ip_sync_info: dict = field(default_factory=dict)  # 代表新master的位点信息

    @staticmethod
    def get_new_master_bin_pos_var_name() -> str:
        return "master_ip_sync_info"


# @dataclass()
# class MySQLFullBackupContext:
#     ip: str = None
#     port: int = None
#     # show_open_fence: bool = None
#     # old_new_map: dict = None
#     # db_table_filter_regex: str = None
#     # db_filter_regex: str = None
#     # backup_report_response: dict = None
#
#     @staticmethod
#     def get_backup_ip_var_name() -> str:
#         return "ip"


@dataclass()
class SpiderApplyManualContext:
    """
    定义Spider集群部署的可交互上下文dataclass类(手输ip模式)
    """

    master_ip_sync_info: dict = field(default_factory=dict)  # 代表获取到master的主从复制位点信息
    time_zone_info: dict = field(default_factory=dict)  # 新机器的时区设置信息

    @staticmethod
    def get_time_zone_var_name() -> str:
        return "time_zone_info"

    @staticmethod
    def get_sync_info_var_name() -> str:
        return "master_ip_sync_info"


# @dataclass()
# class SpiderAddTmpNodeManualContext:
#     master_ip_sync_info: dict = field(default_factory=dict)  # 代表获取到master的主从复制位点信息
#     time_zone_info: dict = field(default_factory=dict)  # 新机器的时区设置信息
#
#     @staticmethod
#     def get_time_zone_var_name() -> str:
#         return "time_zone_info"
#
#     @staticmethod
#     def get_sync_info_var_name() -> str:
#         return "master_ip_sync_info"


@dataclass()
class SpiderSlaveApplyManualContext:
    """
    定义Spider slave部署的可交互上下文dataclass类
    """

    time_zone_info: dict = field(default_factory=dict)  # 新机器的时区设置信息

    @staticmethod
    def get_time_zone_var_name() -> str:
        return "time_zone_info"


@dataclass()
class MySQLBackupDemandContext:
    ip: str = None
    port: int = None
    regex: str = None
    backup_report_response: dict = None
    db_table_filter_regex: str = None
    db_filter_regex: str = None
    targets: Dict = None  # 用来检查是否匹配到库表

    @staticmethod
    def get_backup_ip_var_name() -> str:
        return "ip"


@dataclass()
class MySQLFlashBackContext:
    targets: Dict = None


@dataclass()
class MySQLHAImportMetadataContext:
    cluster_ids: List = None


@dataclass()
class TenDBClusterImportMetadataContext:
    cluster_ids: List = None
