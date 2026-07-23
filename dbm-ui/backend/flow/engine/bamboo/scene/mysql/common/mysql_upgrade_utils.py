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
import logging

from django.utils.translation import gettext as _

from backend.configuration.constants import MYSQL8_VER_PARSE_NUM
from backend.db_meta.exceptions import DBMetaException
from backend.flow.utils.mysql.mysql_version_parse import mysql_version_parse, tmysql_version_parse

logger = logging.getLogger("flow")


def convert_mysql8_version_num(ver_num: int) -> int:
    # MySQL的发行版本号并不连续 MySQL 5.5 5.6 5.7 8.0
    # 为了方便比较将8.0 装换成 parse 之后的5.8的版本号来做比较
    return 5008 * 1000 + ver_num % 1000


def upgrade_version_check(origin_ver: str, new_ver: str):
    new_version_num = mysql_version_parse(new_ver)
    original_version_num = mysql_version_parse(origin_ver)
    if new_version_num >= MYSQL8_VER_PARSE_NUM:
        new_version_num = convert_mysql8_version_num(new_version_num)
    if new_version_num // 1000 - original_version_num // 1000 > 1:
        logger.error("upgrades across multiple major versions are not allowed")
        raise DBMetaException(message=_("不允许跨多个大版本升级"))
    if original_version_num > new_version_num:
        logger.error(
            "the upgrade version {} needs to be larger than the current version {}".format(
                new_version_num, original_version_num
            )
        )
        raise DBMetaException(message=_("当前集群MySQL升级版本大于新版本,请确认"))
    elif original_version_num == new_version_num:
        new_tmysql_version = tmysql_version_parse(new_ver)
        origin_tmysql_version = tmysql_version_parse(origin_ver)
        if new_tmysql_version > origin_tmysql_version:
            logger.info("the tmysql version upgrade {} -> {}".format(origin_tmysql_version, new_tmysql_version))
        else:
            logger.error(
                "the tmysql version {} needs to be larger than the current tmysql version {}".format(
                    new_tmysql_version, origin_tmysql_version
                )
            )
            raise DBMetaException(message=_("当前集群MySQL升级版本大于新版本,请确认"))


def adapt_mycnf_for_upgrade(pkg_name, db_version: str, db_config: dict):
    if mysql_version_parse(db_version) >= mysql_version_parse("5.7.0"):
        will_del_keys = ["slave_parallel_type", "replica_parallel_type"]
        # 如果不是tmysql的话，需要删除一些配置
        if "tmysql" not in pkg_name:
            will_del_keys.append("log_bin_compress")
            will_del_keys.append("relay_log_uncompress")
        for port in db_config:
            for key in will_del_keys:
                if db_config[port].get(key):
                    del db_config[port][key]
    if mysql_version_parse(db_version) >= mysql_version_parse("8.0.0"):
        will_del_keys = ["innodb_large_prefix"]
        for port in db_config:
            for key in will_del_keys:
                if db_config[port].get(key):
                    del db_config[port][key]
    return db_config
