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
from backend import env
from backend.components.constants import SSLEnum
from backend.configuration.constants import DBType
from backend.db_meta.enums.cluster_type import ClusterType
from backend.db_package.models import Package
from backend.db_services.version.constants import PredixyVersion, TwemproxyVersion
from backend.flow.consts import CLOUD_SSL_PATH, MediumEnum


class GetFileList(object):
    """
    定义获取文件列表的对象，调用时通过任务类型、节点属性、来判断应该下发什么文件
    定义新场景时，可以根据
    """

    def __init__(self, db_type: str = DBType.MySQL):
        """
        @param db_type: db类型，默认是MySQL，如果是Redis这actuator包不一样
        """
        self.actuator_pkg = Package.get_latest_package(
            version=MediumEnum.Latest, pkg_type=MediumEnum.DBActuator, db_type=db_type
        )

    def get_db_actuator_package(self):
        """
        最新的db_actuator介质包路径
        """
        return [f"{env.BKREPO_PROJECT}/{env.BKREPO_BUCKET}/{self.actuator_pkg.path}"]

    def get_db_dba_toolkit_package(self):
        """
        最新的dba_toolkit包
        """
        dba_toolkit = Package.get_latest_package(version=MediumEnum.Latest, pkg_type=MediumEnum.MySQLToolKit)
        return [f"{env.BKREPO_PROJECT}/{env.BKREPO_BUCKET}/{dba_toolkit.path}"]

    @staticmethod
    def get_mysql_surrounding_apps_package():
        """
        mysql的备份介质包和数据校验介质包，提供切换后重建用的
        """
        db_backup_pkg = Package.get_latest_package(version=MediumEnum.Latest, pkg_type=MediumEnum.DbBackup)
        checksum_pkg = Package.get_latest_package(version=MediumEnum.Latest, pkg_type=MediumEnum.MySQLChecksum)
        rotate_binlog = Package.get_latest_package(version=MediumEnum.Latest, pkg_type=MediumEnum.MySQLRotateBinlog)
        mysql_monitor_pkg = Package.get_latest_package(version=MediumEnum.Latest, pkg_type=MediumEnum.MySQLMonitor)
        return [
            f"{env.BKREPO_PROJECT}/{env.BKREPO_BUCKET}/{db_backup_pkg.path}",
            f"{env.BKREPO_PROJECT}/{env.BKREPO_BUCKET}/{checksum_pkg.path}",
            f"{env.BKREPO_PROJECT}/{env.BKREPO_BUCKET}/{rotate_binlog.path}",
            f"{env.BKREPO_PROJECT}/{env.BKREPO_BUCKET}/{mysql_monitor_pkg.path}",
        ]

    def mysql_install_package(self, db_version: str) -> list:
        """
        mysql安装需要的安装包
        """
        mysql_pkg = Package.get_latest_package(version=db_version, pkg_type=MediumEnum.MySQL)
        db_backup_pkg = Package.get_latest_package(version=MediumEnum.Latest, pkg_type=MediumEnum.DbBackup)
        checksum_pkg = Package.get_latest_package(version=MediumEnum.Latest, pkg_type=MediumEnum.MySQLChecksum)
        dba_toolkit = Package.get_latest_package(version=MediumEnum.Latest, pkg_type=MediumEnum.MySQLToolKit)
        rotate_binlog = Package.get_latest_package(version=MediumEnum.Latest, pkg_type=MediumEnum.MySQLRotateBinlog)
        mysql_crond_pkg = Package.get_latest_package(version=MediumEnum.Latest, pkg_type=MediumEnum.MySQLCrond)
        mysql_monitor_pkg = Package.get_latest_package(version=MediumEnum.Latest, pkg_type=MediumEnum.MySQLMonitor)
        return [
            f"{env.BKREPO_PROJECT}/{env.BKREPO_BUCKET}/{mysql_pkg.path}",
            f"{env.BKREPO_PROJECT}/{env.BKREPO_BUCKET}/{db_backup_pkg.path}",
            f"{env.BKREPO_PROJECT}/{env.BKREPO_BUCKET}/{checksum_pkg.path}",
            f"{env.BKREPO_PROJECT}/{env.BKREPO_BUCKET}/{dba_toolkit.path}",
            f"{env.BKREPO_PROJECT}/{env.BKREPO_BUCKET}/{rotate_binlog.path}",
            f"{env.BKREPO_PROJECT}/{env.BKREPO_BUCKET}/{self.actuator_pkg.path}",
            f"{env.BKREPO_PROJECT}/{env.BKREPO_BUCKET}/{mysql_crond_pkg.path}",
            f"{env.BKREPO_PROJECT}/{env.BKREPO_BUCKET}/{mysql_monitor_pkg.path}",
        ]

    # MYSQL_RESTORE_SLAVE
    def mysql_restore_slave(self, db_version: str) -> list:
        """
        重建mysql slave 需要的pkg列表
        """
        mysql_pkg = Package.get_latest_package(version=db_version, pkg_type=MediumEnum.MySQL)
        db_backup_pkg = Package.get_latest_package(version=MediumEnum.Latest, pkg_type=MediumEnum.DbBackup)
        mysql_crond_pkg = Package.get_latest_package(version=MediumEnum.Latest, pkg_type=MediumEnum.MySQLCrond)
        return [
            f"{env.BKREPO_PROJECT}/{env.BKREPO_BUCKET}/{mysql_pkg.path}",
            f"{env.BKREPO_PROJECT}/{env.BKREPO_BUCKET}/{db_backup_pkg.path}",
            f"{env.BKREPO_PROJECT}/{env.BKREPO_BUCKET}/{self.actuator_pkg.path}",
            f"{env.BKREPO_PROJECT}/{env.BKREPO_BUCKET}/{mysql_crond_pkg.path}",
        ]

    def mysql_proxy_install_package(self) -> list:
        """
        mysql_proxy安装需要的安装包列表
        """
        proxy_pkg = Package.get_latest_package(version=MediumEnum.Latest, pkg_type=MediumEnum.Proxy)
        mysql_crond_pkg = Package.get_latest_package(version=MediumEnum.Latest, pkg_type=MediumEnum.MySQLCrond)
        mysql_monitor_pkg = Package.get_latest_package(version=MediumEnum.Latest, pkg_type=MediumEnum.MySQLMonitor)
        return [
            f"{env.BKREPO_PROJECT}/{env.BKREPO_BUCKET}/{self.actuator_pkg.path}",
            f"{env.BKREPO_PROJECT}/{env.BKREPO_BUCKET}/{proxy_pkg.path}",
            f"{env.BKREPO_PROJECT}/{env.BKREPO_BUCKET}/{mysql_crond_pkg.path}",
            f"{env.BKREPO_PROJECT}/{env.BKREPO_BUCKET}/{mysql_monitor_pkg.path}",
        ]

    def riak_install_package(self, db_version: str) -> list:
        """
        riak安装需要的安装包列表
        """
        riak_pkg = Package.get_latest_package(version=db_version, pkg_type=MediumEnum.Riak, db_type=DBType.Riak)
        # riak_crond_pkg = Package.get_latest_package(version=MediumEnum.Latest,
        #                                             pkg_type=MediumEnum.RiakCrond, db_type=DBType.Riak)
        # riak_monitor_pkg = Package.get_latest_package(version=MediumEnum.Latest,
        #                                               pkg_type=MediumEnum.RiakMonitor, db_type=DBType.Riak)
        return [
            f"{env.BKREPO_PROJECT}/{env.BKREPO_BUCKET}/{self.actuator_pkg.path}",
            f"{env.BKREPO_PROJECT}/{env.BKREPO_BUCKET}/{riak_pkg.path}",
            # f"{env.BKREPO_PROJECT}/{env.BKREPO_BUCKET}/{riak_crond_pkg.path}",
            # f"{env.BKREPO_PROJECT}/{env.BKREPO_BUCKET}/{riak_monitor_pkg.path}",
        ]

    def redis_cluster_apply_proxy(self, cluster_type) -> list:
        """
        部署redis,所有节点需要的proxy pkg包
        """
        version = TwemproxyVersion.TwemproxyLatest
        pkg_type = MediumEnum.Twemproxy
        if cluster_type == ClusterType.TendisPredixyTendisplusCluster.value:
            version = PredixyVersion.PredixyLatest
            pkg_type = MediumEnum.Predixy

        proxy_pkg = Package.get_latest_package(version=version, pkg_type=pkg_type, db_type=DBType.Redis)
        bkdbmon_pkg = Package.get_latest_package(
            version=MediumEnum.Latest, pkg_type=MediumEnum.DbMon, db_type=DBType.Redis
        )
        redis_tool_pkg = Package.get_latest_package(
            version=MediumEnum.Latest, pkg_type=MediumEnum.RedisTools, db_type=DBType.Redis
        )
        return [
            f"{env.BKREPO_PROJECT}/{env.BKREPO_BUCKET}/{self.actuator_pkg.path}",
            f"{env.BKREPO_PROJECT}/{env.BKREPO_BUCKET}/{proxy_pkg.path}",
            f"{env.BKREPO_PROJECT}/{env.BKREPO_BUCKET}/{redis_tool_pkg.path}",
            f"{env.BKREPO_PROJECT}/{env.BKREPO_BUCKET}/{bkdbmon_pkg.path}",
        ]

    def redis_cluster_apply_backend(self, db_version: str) -> list:
        """
        部署redis,所有节点需要的redis pkg包
        """
        pkg_type = MediumEnum.Redis
        if db_version.startswith("TendisSSD"):
            pkg_type = MediumEnum.TendisSsd
        if db_version.startswith("Tendisplus"):
            pkg_type = MediumEnum.TendisPlus
        redis_pkg = Package.get_latest_package(version=db_version, pkg_type=pkg_type, db_type=DBType.Redis)
        redis_tool_pkg = Package.get_latest_package(
            version=MediumEnum.Latest, pkg_type=MediumEnum.RedisTools, db_type=DBType.Redis
        )
        bkdbmon_pkg = Package.get_latest_package(
            version=MediumEnum.Latest, pkg_type=MediumEnum.DbMon, db_type=DBType.Redis
        )
        return [
            f"{env.BKREPO_PROJECT}/{env.BKREPO_BUCKET}/{self.actuator_pkg.path}",
            f"{env.BKREPO_PROJECT}/{env.BKREPO_BUCKET}/{redis_pkg.path}",
            f"{env.BKREPO_PROJECT}/{env.BKREPO_BUCKET}/{redis_tool_pkg.path}",
            f"{env.BKREPO_PROJECT}/{env.BKREPO_BUCKET}/{bkdbmon_pkg.path}",
        ]

    def redis_dbmon(self) -> list:
        """
        安装 或者重装 dbmon
        """
        bkdbmon_pkg = Package.get_latest_package(
            version=MediumEnum.Latest, pkg_type=MediumEnum.DbMon, db_type=DBType.Redis
        )
        redis_tool_pkg = Package.get_latest_package(
            version=MediumEnum.Latest, pkg_type=MediumEnum.RedisTools, db_type=DBType.Redis
        )
        return [
            f"{env.BKREPO_PROJECT}/{env.BKREPO_BUCKET}/{self.actuator_pkg.path}",
            f"{env.BKREPO_PROJECT}/{env.BKREPO_BUCKET}/{redis_tool_pkg.path}",
            f"{env.BKREPO_PROJECT}/{env.BKREPO_BUCKET}/{bkdbmon_pkg.path}",
        ]

    def redis_actuator(
        self,
    ) -> list:
        """
        Redis actuator 包
        """
        redis_tool_pkg = Package.get_latest_package(
            version=MediumEnum.Latest, pkg_type=MediumEnum.RedisTools, db_type=DBType.Redis
        )
        return [
            f"{env.BKREPO_PROJECT}/{env.BKREPO_BUCKET}/{self.actuator_pkg.path}",
            f"{env.BKREPO_PROJECT}/{env.BKREPO_BUCKET}/{redis_tool_pkg.path}",
        ]

    def tendisplus_apply_proxy(self) -> list:
        proxy_pkg = Package.get_latest_package(
            version=PredixyVersion.PredixyLatest, pkg_type=MediumEnum.Predixy, db_type=DBType.Redis
        )
        bkdbmon_pkg = Package.get_latest_package(
            version=MediumEnum.Latest, pkg_type=MediumEnum.DbMon, db_type=DBType.Redis
        )
        redis_tool_pkg = Package.get_latest_package(
            version=MediumEnum.Latest, pkg_type=MediumEnum.RedisTools, db_type=DBType.Redis
        )
        return [
            f"{env.BKREPO_PROJECT}/{env.BKREPO_BUCKET}/{self.actuator_pkg.path}",
            f"{env.BKREPO_PROJECT}/{env.BKREPO_BUCKET}/{proxy_pkg.path}",
            f"{env.BKREPO_PROJECT}/{env.BKREPO_BUCKET}/{redis_tool_pkg.path}",
            f"{env.BKREPO_PROJECT}/{env.BKREPO_BUCKET}/{bkdbmon_pkg.path}",
        ]

    def tendisplus_apply_backend(self, db_version: str) -> list:
        redis_pkg = Package.get_latest_package(
            version=db_version, pkg_type=MediumEnum.TendisPlus, db_type=DBType.Redis
        )
        redis_tool_pkg = Package.get_latest_package(
            version=MediumEnum.Latest, pkg_type=MediumEnum.RedisTools, db_type=DBType.Redis
        )
        bkdbmon_pkg = Package.get_latest_package(
            version=MediumEnum.Latest, pkg_type=MediumEnum.DbMon, db_type=DBType.Redis
        )
        return [
            f"{env.BKREPO_PROJECT}/{env.BKREPO_BUCKET}/{self.actuator_pkg.path}",
            f"{env.BKREPO_PROJECT}/{env.BKREPO_BUCKET}/{redis_pkg.path}",
            f"{env.BKREPO_PROJECT}/{env.BKREPO_BUCKET}/{redis_tool_pkg.path}",
            f"{env.BKREPO_PROJECT}/{env.BKREPO_BUCKET}/{bkdbmon_pkg.path}",
        ]

    def mysql_import_sqlfile(self, path: str, filelist: list) -> list:
        """
        返回执行导入SQL需要下发分的文件
        """
        fileaddrs = []
        for filename in filelist:
            fileaddrs.append(f"{env.BKREPO_PROJECT}/{env.BKREPO_BUCKET}/{path}/{filename}")
        # fileaddrs.append(f"{env.BKREPO_PROJECT}/{env.BKREPO_BUCKET}/{self.actuator_pkg.path}")
        return fileaddrs

    def es_apply(self, db_version: str) -> list:
        # 部署es所有节点需要的pkg列表
        es_pkg = Package.get_latest_package(version=db_version, pkg_type=MediumEnum.Es, db_type=DBType.Es)
        return [
            f"{env.BKREPO_PROJECT}/{env.BKREPO_BUCKET}/{es_pkg.path}",
            f"{env.BKREPO_PROJECT}/{env.BKREPO_BUCKET}/{self.actuator_pkg.path}",
        ]

    def es_scale_up(self, db_version: str) -> list:
        # 扩容es所有节点需要的pkg列表
        es_pkg = Package.get_latest_package(version=db_version, pkg_type=MediumEnum.Es, db_type=DBType.Es)
        return [
            f"{env.BKREPO_PROJECT}/{env.BKREPO_BUCKET}/{es_pkg.path}",
            f"{env.BKREPO_PROJECT}/{env.BKREPO_BUCKET}/{self.actuator_pkg.path}",
        ]

    def es_disable(self) -> list:
        # 禁用集群只需要actuator
        return self.get_db_actuator_package()

    def es_enable(self) -> list:
        # 启用集群只需要actuator
        return self.get_db_actuator_package()

    def es_reboot(self) -> list:
        # 重启实例只需要actuator
        return self.get_db_actuator_package()

    def es_destroy(self) -> list:
        # 销毁集群只需要actuator
        return self.get_db_actuator_package()

    def es_shrink(self) -> list:
        # 缩容集群只需要actuator
        return self.get_db_actuator_package()

    def kafka_apply(self, db_version: str) -> list:
        # 部署kafka集群，所有节点需要的pkg列表
        kafka_pkg = Package.get_latest_package(version=db_version, pkg_type=MediumEnum.Kafka, db_type=DBType.Kafka)
        return [
            f"{env.BKREPO_PROJECT}/{env.BKREPO_BUCKET}/{self.actuator_pkg.path}",
            f"{env.BKREPO_PROJECT}/{env.BKREPO_BUCKET}/{kafka_pkg.path}",
        ]

    def reboot(self) -> list:
        # 重启实例只需要actuator
        return self.get_db_actuator_package()

    def influxdb_apply(self, db_version: str) -> list:
        # 部署kafka集群，所有节点需要的pkg列表
        influxdb_pkg = Package.get_latest_package(
            version=db_version, pkg_type=MediumEnum.Influxdb, db_type=DBType.InfluxDB
        )
        return [
            f"{env.BKREPO_PROJECT}/{env.BKREPO_BUCKET}/{self.actuator_pkg.path}",
            f"{env.BKREPO_PROJECT}/{env.BKREPO_BUCKET}/{influxdb_pkg.path}",
        ]

    def fetch_kafka_actuator_path(self) -> list:
        """
        只拉取kafka actuator
        """
        return [
            f"{env.BKREPO_PROJECT}/{env.BKREPO_BUCKET}/{self.actuator_pkg.path}",
        ]

    def redis_base(self) -> list:
        """
        redis单据基础包：act + tool工具包 + dbmon
        """
        redis_tool_pkg = Package.get_latest_package(
            version=MediumEnum.Latest, pkg_type=MediumEnum.RedisTools, db_type=DBType.Redis
        )
        bkdbmon_pkg = Package.get_latest_package(
            version=MediumEnum.Latest, pkg_type=MediumEnum.DbMon, db_type=DBType.Redis
        )
        return [
            f"{env.BKREPO_PROJECT}/{env.BKREPO_BUCKET}/{self.actuator_pkg.path}",
            f"{env.BKREPO_PROJECT}/{env.BKREPO_BUCKET}/{redis_tool_pkg.path}",
            f"{env.BKREPO_PROJECT}/{env.BKREPO_BUCKET}/{bkdbmon_pkg.path}",
        ]

    def redis_add_dts_server(self) -> list:
        """
        redis add dts_server
        """
        redis_dts_pkg = Package.get_latest_package(
            version=MediumEnum.Latest, pkg_type=MediumEnum.RedisDts, db_type=DBType.Redis
        )
        return [
            f"{env.BKREPO_PROJECT}/{env.BKREPO_BUCKET}/{self.actuator_pkg.path}",
            f"{env.BKREPO_PROJECT}/{env.BKREPO_BUCKET}/{redis_dts_pkg.path}",
        ]

    def redis_remove_dts_server(self) -> list:
        """
        redis remove dts_server
        """
        return [
            f"{env.BKREPO_PROJECT}/{env.BKREPO_BUCKET}/{self.actuator_pkg.path}",
        ]

    def hdfs_apply(self, db_version: str) -> list:
        # 部署hdfs集群需要的pkg列表
        hdfs_pkg = Package.get_latest_package(version=db_version, pkg_type=MediumEnum.Hdfs, db_type=DBType.Hdfs)
        return [
            f"{env.BKREPO_PROJECT}/{env.BKREPO_BUCKET}/{hdfs_pkg.path}",
            f"{env.BKREPO_PROJECT}/{env.BKREPO_BUCKET}/{self.actuator_pkg.path}",
        ]

    def hdfs_actuator(self) -> list:
        # 执行hdfs actor需要的文件列表
        return [
            f"{env.BKREPO_PROJECT}/{env.BKREPO_BUCKET}/{self.actuator_pkg.path}",
        ]

    @classmethod
    def nginx_apply(cls) -> list:
        # 部署云区域nginx服务的文件列表
        nginx_pkg = Package.get_latest_package(
            version=MediumEnum.Latest, pkg_type=MediumEnum.CloudNginx, db_type=DBType.Cloud
        )
        return [
            f"{env.BKREPO_PROJECT}/{env.BKREPO_BUCKET}/{nginx_pkg.path}",
            f"{env.BKREPO_PROJECT}/{env.BKREPO_BUCKET}/{CLOUD_SSL_PATH}/{SSLEnum.SERVER_CRT}",
            f"{env.BKREPO_PROJECT}/{env.BKREPO_BUCKET}/{CLOUD_SSL_PATH}/{SSLEnum.SERVER_KEY}",
            f"{env.BKREPO_PROJECT}/{env.BKREPO_BUCKET}/{CLOUD_SSL_PATH}/{SSLEnum.CLIENT_CRT}",
            f"{env.BKREPO_PROJECT}/{env.BKREPO_BUCKET}/{CLOUD_SSL_PATH}/{SSLEnum.CLIENT_KEY}",
        ]

    @classmethod
    def dns_apply(cls) -> list:
        # 部署云区域nginx服务的文件列表
        dns_bind_pkg = Package.get_latest_package(
            version=MediumEnum.Latest, pkg_type=MediumEnum.CloudDNSBind, db_type=DBType.Cloud
        )
        dns_pull_crond_pkg = Package.get_latest_package(
            version=MediumEnum.Latest, pkg_type=MediumEnum.CloudDNSPullCrond, db_type=DBType.Cloud
        )
        return [
            f"{env.BKREPO_PROJECT}/{env.BKREPO_BUCKET}/{dns_bind_pkg.path}",
            f"{env.BKREPO_PROJECT}/{env.BKREPO_BUCKET}/{dns_pull_crond_pkg.path}",
        ]

    @classmethod
    def dbha_apply(cls) -> list:
        # 部署云区域dbha服务的文件列表
        dbha_pkg = Package.get_latest_package(
            version=MediumEnum.Latest, pkg_type=MediumEnum.CloudDBHA, db_type=DBType.Cloud
        )
        return [
            f"{env.BKREPO_PROJECT}/{env.BKREPO_BUCKET}/{dbha_pkg.path}",
        ]

    @classmethod
    def drs_apply(cls) -> list:
        # 部署云区域drs服务的文件列表
        drs_pkg = Package.get_latest_package(
            version=MediumEnum.Latest, pkg_type=MediumEnum.CloudDRS, db_type=DBType.Cloud
        )
        tmysqlparse_pkg = Package.get_latest_package(
            version=MediumEnum.Latest, pkg_type=MediumEnum.CloudDRSTymsqlParse, db_type=DBType.Cloud
        )
        return [
            f"{env.BKREPO_PROJECT}/{env.BKREPO_BUCKET}/{drs_pkg.path}",
            f"{env.BKREPO_PROJECT}/{env.BKREPO_BUCKET}/{tmysqlparse_pkg.path}",
            f"{env.BKREPO_PROJECT}/{env.BKREPO_BUCKET}/{CLOUD_SSL_PATH}/{SSLEnum.SERVER_CRT}",
            f"{env.BKREPO_PROJECT}/{env.BKREPO_BUCKET}/{CLOUD_SSL_PATH}/{SSLEnum.SERVER_KEY}",
        ]

    def pulsar_apply(self, db_version: str) -> list:
        # 部署es所有节点需要的pkg列表
        pulsar_pkg = Package.get_latest_package(version=db_version, pkg_type=MediumEnum.Pulsar, db_type=DBType.Pulsar)
        return [
            f"{env.BKREPO_PROJECT}/{env.BKREPO_BUCKET}/{pulsar_pkg.path}",
            f"{env.BKREPO_PROJECT}/{env.BKREPO_BUCKET}/{self.actuator_pkg.path}",
        ]

    def pulsar_actuator(self) -> list:
        # 执行pulsar actor需要的文件列表
        return [
            f"{env.BKREPO_PROJECT}/{env.BKREPO_BUCKET}/{self.actuator_pkg.path}",
        ]

    def spider_master_install_package(self, spider_version: str) -> list:
        """
        部署spider master节点时需要的介质包
        spider master 和 spider ctl 混合部署一起，所以下发两个介质包
        """
        spider_master_pkg = Package.get_latest_package(
            version=spider_version, pkg_type=MediumEnum.Spider, db_type=DBType.MySQL
        )
        tdbctl_pkg = Package.get_latest_package(
            version=MediumEnum.Latest, pkg_type=MediumEnum.tdbCtl, db_type=DBType.MySQL
        )
        mysql_crond_pkg = Package.get_latest_package(
            version=MediumEnum.Latest, pkg_type=MediumEnum.MySQLCrond, db_type=DBType.MySQL
        )
        return [
            f"{env.BKREPO_PROJECT}/{env.BKREPO_BUCKET}/{self.actuator_pkg.path}",
            f"{env.BKREPO_PROJECT}/{env.BKREPO_BUCKET}/{spider_master_pkg.path}",
            f"{env.BKREPO_PROJECT}/{env.BKREPO_BUCKET}/{tdbctl_pkg.path}",
            f"{env.BKREPO_PROJECT}/{env.BKREPO_BUCKET}/{mysql_crond_pkg.path}",
        ]

    def spider_slave_install_package(self, spider_version: str) -> list:
        """
        部署spider slave节点需要的介质包
        """
        spider_slave_pkg = Package.get_latest_package(
            version=spider_version, pkg_type=MediumEnum.Spider, db_type=DBType.MySQL
        )
        mysql_crond_pkg = Package.get_latest_package(
            version=MediumEnum.Latest, pkg_type=MediumEnum.MySQLCrond, db_type=DBType.MySQL
        )
        mysql_monitor_pkg = Package.get_latest_package(
            version=MediumEnum.Latest, pkg_type=MediumEnum.MySQLMonitor, db_type=DBType.MySQL
        )
        return [
            f"{env.BKREPO_PROJECT}/{env.BKREPO_BUCKET}/{self.actuator_pkg.path}",
            f"{env.BKREPO_PROJECT}/{env.BKREPO_BUCKET}/{spider_slave_pkg.path}",
            f"{env.BKREPO_PROJECT}/{env.BKREPO_BUCKET}/{mysql_crond_pkg.path}",
            f"{env.BKREPO_PROJECT}/{env.BKREPO_BUCKET}/{mysql_monitor_pkg.path}",
        ]

    @staticmethod
    def get_spider_apps_package():
        """
        spider 安装周边程序所需要下载介质包列表
        """
        db_backup_pkg = Package.get_latest_package(version=MediumEnum.Latest, pkg_type=MediumEnum.DbBackup)
        mysql_monitor_pkg = Package.get_latest_package(version=MediumEnum.Latest, pkg_type=MediumEnum.MySQLMonitor)
        dba_toolkit = Package.get_latest_package(version=MediumEnum.Latest, pkg_type=MediumEnum.MySQLToolKit)
        return [
            f"{env.BKREPO_PROJECT}/{env.BKREPO_BUCKET}/{dba_toolkit.path}",
            f"{env.BKREPO_PROJECT}/{env.BKREPO_BUCKET}/{db_backup_pkg.path}",
            f"{env.BKREPO_PROJECT}/{env.BKREPO_BUCKET}/{mysql_monitor_pkg.path}",
        ]
