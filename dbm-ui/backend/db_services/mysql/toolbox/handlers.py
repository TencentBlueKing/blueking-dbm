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
import re

from backend.configuration.constants import MYSQL8_VER_PARSE_NUM, DBType
from backend.db_meta.enums import InstanceRole
from backend.db_meta.models import Cluster, StorageInstance
from backend.db_package.models import Package
from backend.flow.consts import MediumEnum
from backend.flow.utils.mysql.mysql_version_parse import (
    get_online_mysql_version,
    major_version_parse,
    tmysql_version_parse,
)


class ToolboxHandler:
    """mysql工具箱查询接口封装"""

    def __init__(self):
        self.available_pkg_list = []

    #  select version()
    #  tmysql:  select version();==> 5.7.20-tmysql-3.4.2-log
    #  社区版本 mysql:> select version(); 8.0.32
    #  txsql: select version(); 8.0.30-txsql

    # tmysql pkg name: mysql-5.7.20-linux-x86_64-tmysql-3.3-gcs.tar.gz
    # txsql pkg name: mysql-txsql-8.0.30-20230701-linux-x86_64.tar.gz
    # 社区版本 pkg name: mysql-8.0.32-linux-glibc2.12-x86_64.tar.xz

    def query_higher_version_pkg_list(self, cluster_id: int, higher_major_version: bool, higher_all_version: bool):
        cluster = Cluster.objects.filter(id=cluster_id).get()
        instance = StorageInstance.objects.filter(
            cluster=cluster,
            instance_role__in=[InstanceRole.ORPHAN, InstanceRole.BACKEND_MASTER],
        ).first()

        all_pkg_list = Package.objects.filter(pkg_type=MediumEnum.MySQL, db_type=DBType.MySQL, enable=True).all()
        refer_version = get_online_mysql_version(
            ip=instance.machine.ip, port=instance.port, bk_cloud_id=cluster.bk_cloud_id
        )

        tmysql_re_pattern = r"tmysql-([\d]+).?([\d]+)?.?([\d]+)?"
        txsql_re_pattern = r"([\d]+).?([\d]+)?.?([\d]+)?-txsql"
        pkgname_txsql_re_pattern = r"txsql-([\d]+).?([\d]+)?.?([\d]+)?"
        # 参考的集群是tmysql的介质
        major_version_num, sub_version_num = major_version_parse(refer_version)
        tmysql_sub_version_num = 0
        refer_pkg_type = "mysql"

        if re.search(tmysql_re_pattern, refer_version):
            tmysql_sub_version_num = tmysql_version_parse(refer_version)
            refer_pkg_type = "tmysql"
        elif re.search(txsql_re_pattern, refer_version):
            refer_pkg_type = "txsql"

        for pkg in all_pkg_list:
            pkg_major_vesion_num, pkg_sub_version_num = major_version_parse(pkg.name)
            pkg_major_vesion_num = convert_mysql8_version_num(pkg_major_vesion_num)
            if refer_pkg_type == "tmysql":
                # tmysql 可用用mysql 官方社区版本的介质
                if re.search(tmysql_re_pattern, pkg.name) or (not re.search(pkgname_txsql_re_pattern, pkg.name)):
                    # higger_major_version：需要更高的主版本，无需比较子版本
                    if higher_major_version or higher_all_version:
                        self.filter_available_packages(
                            pkg,
                            higher_major_version,
                            higher_all_version,
                            major_version_num,
                            pkg_major_vesion_num,
                            sub_version_num,
                            pkg_sub_version_num,
                        )
                        # 判断tmysql的子版本
                        if (
                            higher_all_version
                            and pkg_major_vesion_num == major_version_num
                            and pkg_sub_version_num == sub_version_num
                        ):
                            tmysql_pkg_sub_version_num = tmysql_version_parse(pkg.name)
                            if tmysql_pkg_sub_version_num > tmysql_sub_version_num:
                                self.available_pkg_list.append(pkg)
                        continue
                    else:
                        if pkg_major_vesion_num == major_version_num:
                            tmysql_pkg_sub_version_num = tmysql_version_parse(pkg.name)
                            if tmysql_pkg_sub_version_num > tmysql_sub_version_num:
                                self.available_pkg_list.append(pkg)
                            if pkg_sub_version_num > sub_version_num:
                                self.available_pkg_list.append(pkg)

            elif refer_pkg_type == "txsql":
                if re.search(pkgname_txsql_re_pattern, pkg.name):
                    self.filter_available_packages(
                        pkg,
                        higher_major_version,
                        higher_all_version,
                        major_version_num,
                        pkg_major_vesion_num,
                        sub_version_num,
                        pkg_sub_version_num,
                    )

            # 统一当做社区版本来处理
            else:
                if (not re.search(pkgname_txsql_re_pattern, pkg.name)) and (
                    not re.search(tmysql_re_pattern, pkg.name)
                ):
                    self.filter_available_packages(
                        pkg,
                        higher_major_version,
                        higher_all_version,
                        major_version_num,
                        pkg_major_vesion_num,
                        sub_version_num,
                        pkg_sub_version_num,
                    )

        return [
            {
                "version": item.version,
                "pkg_name": item.name,
                "pkg_id": item.id,
            }
            for item in self.available_pkg_list
        ]

    def filter_available_packages(
        self,
        pkg: Package,
        higher_major_version: bool,
        higher_all_version: bool,
        refer_version_num: int,
        current_version_num: int,
        refer_sub_version_num: int,
        current_sub_version_num: int,
    ):
        """
        根据包类型、版本号和是否要求更高主版本来过滤包列表
        """
        if (higher_major_version or higher_all_version) and just_cross_one_major_version(
            current_version_num, refer_version_num
        ):
            self.available_pkg_list.append(pkg)
        else:
            if (
                (not higher_major_version)
                and (current_version_num == refer_version_num)
                and (current_sub_version_num > refer_sub_version_num)
            ):
                self.available_pkg_list.append(pkg)
        # higher_all_version 表示需要获取大小版本都可以使用的包
        if (
            higher_all_version
            and (current_version_num == refer_version_num)
            and (current_sub_version_num > refer_sub_version_num)
        ):
            self.available_pkg_list.append(pkg)


def convert_mysql8_version_num(major_version: int) -> int:
    # MySQL的发行版本号并不连续 MySQL 5.5 5.6 5.7 8.0
    # 为了方便比较将8.0 装换成 parse 之后的5.8的版本号来做比较
    if major_version >= MYSQL8_VER_PARSE_NUM:
        return 5008 * 1000 + major_version % 1000
    return major_version


def just_cross_one_major_version(current_version_num, refer_version_num) -> bool:
    print(current_version_num // 1000 - refer_version_num // 1000)
    return (current_version_num // 1000 - refer_version_num // 1000) == 1
