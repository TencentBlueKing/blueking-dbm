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
import re

from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component

from backend.components import DRSApi
from backend.constants import IP_PORT_DIVIDER
from backend.flow.plugins.components.collections.common.base_service import BaseService

logger = logging.getLogger("flow")

# 用于判断 SQL 是否包含复制相关关键字，匹配时使用 rpc_mysql_replica_compat
_REPLICATION_KEYWORD_PATTERN = re.compile(r"\b(slave|master)\b", re.IGNORECASE)


class MySQLExecuteRdsService(BaseService):
    """
    执行 rds sql 语句
    """

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        self.log_info(_("传入参数:{}").format(kwargs))

        # 如果 sqls 中包含 slave/master 关键字，使用 rpc_mysql_replica_compat 进行兼容翻译
        # 这里只做粗过滤，如果错误命中 slave/master，在实际转换翻译成时会进一步精确处理
        sqls = kwargs["sqls"]
        use_replica_rpc = any(_REPLICATION_KEYWORD_PATTERN.search(sql) for sql in sqls)
        rpc_func = DRSApi.rpc_mysql_replica_compat if use_replica_rpc else DRSApi.rpc

        res = rpc_func(
            {
                "addresses": ["{}{}{}".format(kwargs["instance_ip"], IP_PORT_DIVIDER, kwargs["instance_port"])],
                "cmds": sqls,
                "force": False,
                "bk_cloud_id": kwargs["bk_cloud_id"],
            }
        )
        if res[0]["error_msg"]:
            self.log_info("execute sql error {}".format(res[0]["error_msg"]))
            return False
        else:
            return True


class MySQLExecuteRdsComponent(Component):
    name = __name__
    code = "mysql_execute_rds"
    bound_service = MySQLExecuteRdsService
