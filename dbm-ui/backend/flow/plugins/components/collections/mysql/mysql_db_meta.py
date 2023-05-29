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
import logging
from dataclasses import asdict

from django.utils.translation import ugettext as _
from pipeline.component_framework.component import Component

from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.mysql.mysql_db_meta import MySQLDBMeta

logger = logging.getLogger("flow")


class MySQLDBMetaService(BaseService):
    """
    根据MySQL单据类型来更新cmdb
    """

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        global_data = data.get_one_of_inputs("global_data")
        trans_data = data.get_one_of_inputs("trans_data")

        # 传入调用结果
        cluster_info = copy.deepcopy(kwargs["cluster"])

        if kwargs["is_update_trans_data"]:
            # 表示合并上下文的内容
            cluster_info = {**kwargs["cluster"], **asdict(trans_data)}

        self.log_info(_("集群元信息:{}").format(cluster_info))

        mysql_meta = MySQLDBMeta(ticket_data=global_data, cluster=cluster_info)

        result = getattr(mysql_meta, kwargs.get("db_meta_class_func"))()

        self.log_info("DBMata re successfully")
        data.outputs.ext_result = result
        return result


class MySQLDBMetaComponent(Component):
    name = __name__
    code = "mysql_db_meta"
    bound_service = MySQLDBMetaService
