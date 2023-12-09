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
from typing import Any, Dict, Optional, Union
from urllib.parse import urljoin

from jinja2 import Environment

from backend import env
from backend.configuration.constants import DBType
from backend.db_meta.models import AppMonitorTopo
from backend.utils.basic import distinct_dict_list


class JsonConfigFormat:
    """
    用于格式化json的配置文件
    格式函数的命名规则: format_{file_name}
    """

    @classmethod
    def get_db_set_ctx(cls, db_type: str):
        return {
            "bk_biz_id": env.DBA_APP_BK_BIZ_ID,
            "target_nodes": distinct_dict_list(
                [
                    {
                        "bk_biz_id": bk_set["bk_biz_id"],
                        "bk_inst_id": bk_set["bk_set_id"],
                        "bk_obj_id": "set",
                    }
                    for bk_set in AppMonitorTopo.get_set_by_dbtype(db_type)
                ]
            ),
        }

    @classmethod
    def format(cls, params: Dict, get_context_method_name: str) -> Dict:
        """
        格式化json配置文件
        :param params: 配置文件的参数
        :param get_context_method_name: 获取上下文的方法名
        """
        context = getattr(cls, get_context_method_name)()
        params.update(context)
        if env.BKLOG_STORAGE_CLUSTER_ID:
            params["storage_cluster_id"] = env.BKLOG_STORAGE_CLUSTER_ID
        return params

    @classmethod
    def custom_modify(cls, params: Dict, custom_modify_method_name: str) -> Dict:

        # 针对一些复杂的数据结构，需自定义方法来修改请求参数
        modify_method = getattr(cls, custom_modify_method_name, None)
        if modify_method:
            params = modify_method(params)
        return params

    @classmethod
    def format_dbm_dbactuator(cls):
        # 如 dbm_dbactuator 这类需要对 DBM 管理的所有机器进行日志采集
        target_nodes = [{"bk_obj_id": "biz", "bk_inst_id": env.DBA_APP_BK_BIZ_ID}]
        target_nodes.extend(
            [
                {"bk_obj_id": "set", "bk_inst_id": topo.bk_set_id, "bk_biz_id": topo.bk_biz_id}
                for topo in AppMonitorTopo.objects.exclude(bk_biz_id=env.DBA_APP_BK_BIZ_ID)
            ]
        )
        return {
            "bk_biz_id": env.DBA_APP_BK_BIZ_ID,
            "target_nodes": distinct_dict_list(target_nodes),
        }

    @classmethod
    def format_backup_stm_log(cls):
        return {
            "bk_biz_id": env.DBA_APP_BK_BIZ_ID,
            "target_nodes": (
                cls.get_db_set_ctx(DBType.Redis.value)["target_nodes"]
                + cls.get_db_set_ctx(DBType.MySQL.value)["target_nodes"]
            ),
        }

    @classmethod
    def format_mysql(cls):
        return cls.get_db_set_ctx(DBType.MySQL.value)

    @classmethod
    def format_redis(cls):
        return cls.get_db_set_ctx(DBType.Redis.value)

    @classmethod
    def custom_modify_mysql_slowlog(cls, params):
        """
        mysql 慢查询日志，需要添加 option 进行清洗
        """
        params["fields"].append(
            {
                "value": "",
                "option": {
                    "dbm_enabled": True,
                    "dbm_url": urljoin(env.SLOW_QUERY_PARSER_DOMAIN, "mysql/"),
                    "dbm_field": "slow_query",
                },
                "is_time": False,
                "verdict": True,
                "is_delete": False,
                "alias_name": "",
                "field_name": "sql_text",
                "field_type": "string",
                "description": "",
                "field_index": 10,
                "is_analyzed": False,
                "is_built_in": False,
                "is_dimension": False,
                "previous_type": "string",
            }
        )
        return params
