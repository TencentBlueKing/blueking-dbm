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
from typing import Any, Union
from urllib.parse import urljoin

from jinja2 import Environment

from backend import env
from backend.configuration.constants import DBType
from backend.db_meta.models import AppMonitorTopo


class JsonConfigFormat:
    """
    用于格式化json的配置文件
    格式函数的命名规则: format_{file_name}
    """

    @classmethod
    def get_db_set_ctx(cls, db_type: str):
        return {
            "bk_biz_id": env.DBA_APP_BK_BIZ_ID,
            "storage_cluster_id": env.STORAGE_CLUSTER_ID,
            "target_nodes": list(
                set(
                    [
                        json.dumps(
                            {
                                "bk_biz_id": bk_set["bk_biz_id"],
                                "bk_inst_id": bk_set["bk_set_id"],
                                "bk_obj_id": "set",
                            }
                        )
                        for bk_set in AppMonitorTopo.get_set_by_dbtype(db_type)
                    ]
                )
            ),
        }

    @classmethod
    def format(cls, content: str, format_func_name: str) -> Union[str, Any]:
        jinja_env = Environment()
        template = jinja_env.from_string(content)
        return template.render(getattr(cls, format_func_name)())

    @classmethod
    def format_for_all(cls):
        # 如 dbm_dbactuator、backup_stm_log 这类需要对 DBM 管理的所有机器进行日志采集
        target_nodes = [json.dumps({"bk_obj_id": "biz", "bk_inst_id": env.DBA_APP_BK_BIZ_ID})]
        target_nodes.extend(
            [
                json.dumps({"bk_obj_id": "set", "bk_inst_id": topo.bk_set_id, "bk_biz_id": topo.bk_biz_id})
                for topo in AppMonitorTopo.objects.exclude(bk_biz_id=env.DBA_APP_BK_BIZ_ID)
            ]
        )
        return {
            "bk_biz_id": env.DBA_APP_BK_BIZ_ID,
            "storage_cluster_id": env.STORAGE_CLUSTER_ID,
            "target_nodes": list(set(target_nodes)),
        }

    @classmethod
    def format_dbm_dbactuator(cls):
        return cls.format_for_all()

    @classmethod
    def format_backup_stm_log(cls):
        return cls.format_for_all()

    @classmethod
    def format_mysql(cls):
        return cls.get_db_set_ctx(DBType.MySQL.value)

    @classmethod
    def format_mysql_slowlog(cls):
        ctx = cls.get_db_set_ctx(DBType.MySQL.value)
        ctx["slow_query_parse_url"] = urljoin(env.SLOW_QUERY_PARSER_DOMAIN, "mysql/")
        return ctx

    @classmethod
    def format_redis(cls):
        return cls.get_db_set_ctx(DBType.Redis.value)
