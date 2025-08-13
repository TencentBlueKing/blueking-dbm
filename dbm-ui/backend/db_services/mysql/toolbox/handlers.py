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

from django.utils.translation import ugettext as _

from backend.configuration.constants import MYSQL8_VER_PARSE_NUM, DBType
from backend.db_meta.enums import InstanceRole
from backend.db_meta.models import Cluster, ProxyInstance, Spec, StorageInstance
from backend.db_package.models import Package
from backend.flow.consts import MediumEnum
from backend.flow.utils.mysql.mysql_version_parse import (
    get_online_mysql_version,
    major_version_parse,
    spider_major_version_parse,
    tmysql_version_parse,
)


class ToolboxHandler:
    """mysql工具箱查询接口封装"""

    def __init__(self):
        self.available_pkg_list = []

    def query_higher_spider_ver_pkgs(self, cluster_id: int, higher_major_version: bool, higher_sub_version: bool):
        cluster = Cluster.objects.filter(id=cluster_id).get()
        spiders = ProxyInstance.objects.filter(cluster=cluster)
        uniq_spider_version_list = list(set(spider.version for spider in spiders))
        all_pkg_list = Package.objects.filter(pkg_type=MediumEnum.Spider, db_type=DBType.MySQL, enable=True).all()
        # 如果版本统一,这是最好的情况
        for pkg in all_pkg_list:
            pkg_major_version_num, pkg_sub_version_num = spider_major_version_parse(pkg.name, True)
            if len(uniq_spider_version_list) == 1:
                refer_version = uniq_spider_version_list[0]
                major_version_num, sub_version_num = spider_major_version_parse(refer_version, False)
            else:
                version_map = {}
                version_num_list = []
                for version in uniq_spider_version_list:
                    version_num = tmysql_version_parse(version)
                    version_map[version_num] = version
                    version_num_list.append(version_num)
                version_num_list.sort()
                min_version_num = min(version_num_list)
                max_version_num = max(version_num_list)
                # 如果集中存在跨主版本的情况,则只能以最大的版本为参考版本
                if spider_cross_major_version(max_version_num, min_version_num):
                    refer_version = version_map[max_version_num]
                    major_version_num, sub_version_num = spider_major_version_parse(refer_version, False)
                else:
                    refer_version = version_map[min_version_num]
                    major_version_num, sub_version_num = spider_major_version_parse(refer_version, False)
            # 参考的版本号和包的版本号进行比较
            self.filter_spider_available_packages(
                pkg,
                higher_major_version,
                higher_sub_version,
                major_version_num,
                pkg_major_version_num,
                sub_version_num,
                pkg_sub_version_num,
            )
        # return the available package list
        return [
            {
                "version": item.version,
                "pkg_name": item.name,
                "pkg_id": item.id,
            }
            for item in self.available_pkg_list
        ]

    def query_higher_version_pkg_list(self, cluster_id: int, higher_major_version: bool, higher_all_version: bool):
        #  select version()
        #  tmysql:  select version();==> 5.7.20-tmysql-3.4.2-log
        #  社区版本 mysql:> select version(); 8.0.32
        #  txsql: select version(); 8.0.30-txsql

        # tmysql pkg name: mysql-5.7.20-linux-x86_64-tmysql-3.3-gcs.tar.gz
        # txsql pkg name: mysql-txsql-8.0.30-20230701-linux-x86_64.tar.gz
        # 社区版本 pkg name: mysql-8.0.32-linux-glibc2.12-x86_64.tar.xz
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
            pkg_major_version_num, pkg_sub_version_num = major_version_parse(pkg.name)
            pkg_major_version_num = convert_mysql8_version_num(pkg_major_version_num)
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
                            pkg_major_version_num,
                            sub_version_num,
                            pkg_sub_version_num,
                        )
                        # 判断tmysql的子版本
                        if (
                            higher_all_version
                            and pkg_major_version_num == major_version_num
                            and pkg_sub_version_num == sub_version_num
                        ):
                            tmysql_pkg_sub_version_num = tmysql_version_parse(pkg.name)
                            if tmysql_pkg_sub_version_num > tmysql_sub_version_num:
                                self.available_pkg_list.append(pkg)
                        continue
                    else:
                        if pkg_major_version_num == major_version_num:
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
                        pkg_major_version_num,
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
                        pkg_major_version_num,
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

    def filter_spider_available_packages(
        self,
        pkg: Package,
        higher_major_version: bool,
        higher_sub_version: bool,
        refer_major_version_num: int,
        current_major_version_num: int,
        refer_sub_version_num: int,
        current_sub_version_num: int,
    ):
        """
        根据包类型、版本号和是否要求更高主版本来过滤包列表
        """
        if higher_major_version:
            if spider_cross_major_version(current_major_version_num, refer_major_version_num):
                self.available_pkg_list.append(pkg)
                return
        if higher_sub_version:
            if (current_major_version_num == refer_major_version_num) and (
                current_sub_version_num > refer_sub_version_num
            ):
                self.available_pkg_list.append(pkg)
                return

    def change_cluster_spec(self, cluster_id: int, cluster_type: str, spec_id: int, machine_type: str):
        """
        更改集群规格

        Args:
            cluster_id: 集群ID
            cluster_type: 集群类型 (tendbha/tendbcluster)
            spec_id: 规格ID
            machine_type: 机器类型

        Returns:
            dict: 包含操作结果的信息
        """
        # 验证集群存在
        try:
            Cluster.objects.get(id=cluster_id, cluster_type=cluster_type)
        except Cluster.DoesNotExist:
            return {"result": False, "message": _("集群不存在或集群类型不匹配")}

        # 验证规格存在且机器类型匹配
        try:
            spec = Spec.objects.get(spec_id=spec_id, spec_machine_type=machine_type)
        except Spec.DoesNotExist:
            return {"result": False, "message": _("规格ID不存在或规格机器类型不匹配")}

        # 获取集群关联的机器
        machines = Cluster.get_cluster_related_machines([cluster_id])

        # 过滤指定机器类型的机器
        target_machines = machines.filter(machine_type=machine_type)

        if not target_machines.exists():
            return {"result": False, "message": _("集群中没有找到指定类型的机器: {}").format(machine_type)}

        # 准备规格配置信息
        spec_config = {
            "spec_id": spec.spec_id,
            "spec_name": spec.spec_name,
            "cpu": spec.cpu,
            "mem": spec.mem,
            "device_class": spec.device_class,
            "storage_spec": spec.storage_spec,
            "qps": spec.qps,
        }

        # 更新机器规格
        updated_count = target_machines.update(spec_id=spec_id, spec_config=spec_config)

        return {
            "result": True,
            "message": _("成功更新了 {} 台机器的规格配置").format(updated_count),
            "cluster_id": cluster_id,
            "cluster_type": cluster_type,
            "spec_id": spec_id,
            "machine_type": machine_type,
            "updated_machines": updated_count,
        }


def convert_mysql8_version_num(major_version: int) -> int:
    # MySQL的发行版本号并不连续 MySQL 5.5 5.6 5.7 8.0
    # 为了方便比较将8.0 装换成 parse 之后的5.8的版本号来做比较
    if major_version >= MYSQL8_VER_PARSE_NUM:
        return 5008 * 1000 + major_version % 1000
    return major_version


def just_cross_one_major_version(current_version_num, refer_version_num) -> bool:
    return (current_version_num // 1000 - refer_version_num // 1000) == 1


def spider_cross_major_version(current_version_num, refer_version_num) -> bool:
    """判断spider是否跨主版本

    Args:
        current_version_num (_type_): _description_
        refer_version_num (_type_): _description_

    Returns:
        bool: _description_
    """
    return (current_version_num // 1000000 - refer_version_num // 1000000) >= 1
