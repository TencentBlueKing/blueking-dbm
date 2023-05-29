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
import copy

MYSQL_CONF_VERSION1 = "MYSQL-5.7"
MYSQL_CONF_VERSION2 = "MYSQL-5.8"
MYSQL_CONF_VERSION3 = "MYSQL-5.9"
OPERATOR = "admin"
CREATED_AT = UPDATED_AT = "1990-01-01"
CHARSET = "utf-8"

LIST_CONF_NAME_DATA = {
    "conf_names": {
        "5.7配置test": {
            "name": "5.7配置test",
            "updated_at": "2022-07-08 16:57:59",
            "updated_by": OPERATOR,
            "version": MYSQL_CONF_VERSION1,
            "info": "",
        }
    }
}

LIST_PLATFORM_CONFIGS = [
    {"conf_file_lc": "5.7配置test", "conf_file": MYSQL_CONF_VERSION1, "updated_at": UPDATED_AT, "updated_by": OPERATOR},
    {"conf_file_lc": "5.8配置test", "conf_file": MYSQL_CONF_VERSION2, "updated_at": UPDATED_AT, "updated_by": OPERATOR},
    {"conf_file_lc": "5.9配置test", "conf_file": MYSQL_CONF_VERSION3, "updated_at": UPDATED_AT, "updated_by": OPERATOR},
]

CONF_FILE_DATA = {
    "conf_file": MYSQL_CONF_VERSION1,
    "conf_names": {
        "mysqld.back_log": {
            "conf_name": "mysqld.back_log",
            "conf_name_lc": "",
            "value_type": "INT",
            "value_type_sub": "RANGE",
            "value_allowed": "[1,65535]",
            "value_default": "3000",
            "need_restart": 1,
            "flag_disable": 0,
            "flag_status": 0,
            "flag_locked": 0,
            "description": "The number of outstanding connection requests MySQL can have.",
        },
        "mysqld.socket": {
            "conf_name": "mysqld.socket",
            "conf_name_lc": "",
            "value_type": "STRING",
            "value_type_sub": "",
            "value_allowed": "",
            "value_default": "mysqldata/mysql.sock",
            "need_restart": 0,
            "flag_disable": 0,
            "flag_status": 0,
            "flag_locked": 0,
            "description": "",
        },
        "os_mysql_user": {"name": OPERATOR, "flag_status": 2},
        "os_mysql_pwd": {"password": "123", "flag_status": 2},
    },
}

CONF_ITEM_DATA = {
    "bk_biz_id": "",
    "level_name": "",
    "level_value": "",
    "flag_status": 0,
    "conf_file_info": {
        "description": "test",
        "updated_by": OPERATOR,
        "created_by": OPERATOR,
        "updated_at": UPDATED_AT,
        "created_at": CREATED_AT,
        "conf_file_lc": "",
    },
    "content": {
        **CONF_FILE_DATA["conf_names"],
        "db_version": {"version": MYSQL_CONF_VERSION1},
        "charset": {"charset": CHARSET},
    },
}

HISTORY_VERSION_DATA = {
    "bk_biz_id": "",
    "namespace": "",
    "conf_file": "",
    "versions": [],
    "published": OPERATOR,
    "level_name": "",
    "level_value": "",
}

VERSION_DETAIL_DATA = {
    "id": 2319,
    "revision": OPERATOR,
    "content": "",
    "is_published": 0,
    "pre_revision": OPERATOR,
    "rows_affected": 2,
    "description": "test",
    "created_by": OPERATOR,
    "created_at": CREATED_AT,
    "configs": {**CONF_FILE_DATA["conf_names"]},
    "configs_diff": {},
}


class DBConfigApiMock(object):
    """
    dbconfig 相关接口的mock
    TODO: 这个测试类的mock数据造的不好，后面需要重造一下
    """

    @classmethod
    def list_conf_name(cls, *args, **kwargs):
        db_args = args[0]
        conf_type = db_args.get("conf_type", "dbconf")
        namespace = db_args.get("namespace", "tendbsingle")
        conf_file = db_args.get("conf_file", "1.0")

        data = copy.deepcopy(LIST_CONF_NAME_DATA)
        for config in data["conf_names"].values():
            config["info"] = f"{conf_type}-{namespace}-{conf_file}"
        return data

    @classmethod
    def query_conf_item(cls, *args, **kwargs):
        db_args = args[0]
        conf_item_data = copy.deepcopy(CONF_ITEM_DATA)
        conf_item_data["bk_biz_id"] = db_args.get("bk_biz_id", 0)
        conf_item_data["level_name"] = db_args.get("level_name", "plat")
        conf_item_data["level_value"] = db_args.get("level_value", 0)
        conf_item_data["conf_file_info"]["conf_file"] = db_args.get("conf_file", "MySQL-5.7")
        conf_item_data["conf_file_info"]["conf_type"] = db_args.get("conf_type", "dbconf")
        conf_item_data["conf_file_info"]["namespace"] = db_args.get("namespace", "tendbsingle")

        return conf_item_data

    @classmethod
    def list_conf_file(cls, *args, **kwargs):
        data = copy.deepcopy(LIST_PLATFORM_CONFIGS)
        return data

    @classmethod
    def query_conf_file(cls, *args, **kwargs):
        conf_file = copy.deepcopy(CONF_FILE_DATA)
        return conf_file

    @classmethod
    def list_version(cls, *args, **kwargs):
        db_args = args[0]
        history_data = copy.deepcopy(HISTORY_VERSION_DATA)
        history_data["bk_biz_id"] = db_args["bk_biz_id"]
        history_data["level_name"] = db_args["level_name"]
        history_data["level_value"] = db_args["level_value"]
        history_data["conf_file"] = db_args["conf_file"]

        return history_data

    @classmethod
    def version_detail(cls, *args, **kwargs):
        db_args = args[0]
        version_detail_data = copy.deepcopy(VERSION_DETAIL_DATA)
        version_detail_data["revision"] = db_args["revision"]
        return version_detail_data

    @classmethod
    def get_instance_config(cls, *args, **kwargs):
        instance_config_data = cls.query_conf_item(*args, **kwargs)
        return instance_config_data
