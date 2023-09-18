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
from typing import Any, Union
from urllib.parse import urljoin

from jinja2 import Environment

from backend import env
from backend.db_meta.models import AppMonitorTopo


class JsonConfigFormat:
    """
    用于格式化json的配置文件
    格式函数的命名规则: format_{file_name}
    """

    @classmethod
    def format(cls, content: str, format_func_name: str) -> Union[str, Any]:
        jinja_env = Environment()
        template = jinja_env.from_string(content)
        return template.render(getattr(cls, format_func_name)())

    @classmethod
    def format_dbm_dbactuator(cls):
        return {"bk_biz_id": env.DBA_APP_BK_BIZ_ID, "bk_inst_id": env.DBA_APP_BK_BIZ_ID}

    @classmethod
    def format_mysql(cls):
        return {
            "bk_biz_id": env.DBA_APP_BK_BIZ_ID,
            "bk_set_ids": list({bk_set["bk_set_id"] for bk_set in AppMonitorTopo.get_set_by_dbtype("mysql")}),
        }

    @classmethod
    def format_mysql_slowlog(cls):
        return {
            "bk_biz_id": env.DBA_APP_BK_BIZ_ID,
            "bk_set_ids": list({bk_set["bk_set_id"] for bk_set in AppMonitorTopo.get_set_by_dbtype("mysql")}),
            "slow_query_parse_url": urljoin(env.SLOW_QUERY_PARSER_DOMAIN, "mysql/"),
        }

    @classmethod
    def format_redis(cls):
        return {
            "bk_biz_id": env.DBA_APP_BK_BIZ_ID,
            "bk_set_ids": list({bk_set["bk_set_id"] for bk_set in AppMonitorTopo.get_set_by_dbtype("redis")}),
        }
