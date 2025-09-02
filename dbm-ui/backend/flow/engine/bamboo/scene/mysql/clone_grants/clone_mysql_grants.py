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
from typing import Dict, Optional

from backend.db_meta.enums import MachineType
from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.engine.bamboo.scene.mysql.clone_grants.context import MySQLCloneGrantsContext
from backend.flow.engine.bamboo.scene.mysql.clone_grants.exceptions import MySQLCloneGrantsValidateException
from backend.flow.engine.bamboo.scene.mysql.clone_grants.subflows import (
    clone_mysql_instance_grants_subflow,
    clone_proxy_instance_userlist_subflow,
)
from backend.flow.engine.bamboo.scene.mysql.clone_grants.subflows.clone_mysql_instance_grants_subflow import (
    clone_mysql_grants_relate_cluster_ids,
)
from backend.flow.engine.bamboo.scene.mysql.clone_grants.validator.clone_mysql_grants_flow_validator import (
    CloneMySQLGrantsFlowValidator,
)


class CloneMySQLGrantsFlow(object):
    """
    1. 同时支持 存储, spider 和 proxy 的克隆
    2. 可以混在一起提交
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        self.root_id = root_id
        self.data = copy.deepcopy(data)

        if not self.data.get("validated", False):
            v = CloneMySQLGrantsFlowValidator(ticket_data=self.data)
            if v:
                raise MySQLCloneGrantsValidateException(msg=v)

    def clone_grants(self):
        """
        bk_biz_id: int,
        infos: [
          {
            "bk_cloud_id": int,
            "machine_type": str,
            "source_address": str,
            "dest_addresses": [str]
          }
        ]

        1. 每一个 info 的 source 和 dest 必须同云区域
        2. 需要按 source 聚合下
        """
        infos = self.data["infos"]

        mysql_infos = []
        proxy_infos = []
        for info in infos:
            if info["machine_type"] == MachineType.PROXY.value:
                proxy_infos.append(info)
            else:
                mysql_infos.append(info)

        root_pipe = Builder(
            root_id=self.root_id,
            data=copy.deepcopy(self.data),
            need_random_pass_cluster_ids=clone_mysql_grants_relate_cluster_ids(infos=infos),
        )

        clone_subpipes = []
        if proxy_infos:
            proxy_data = copy.deepcopy(self.data)
            proxy_data["infos"] = proxy_infos
            clone_subpipes.append(
                clone_proxy_instance_userlist_subflow(
                    root_id=self.root_id,
                    data=proxy_data,
                    infos=proxy_infos,
                    with_actuator=True,
                )
            )

        if mysql_infos:
            mysql_data = copy.deepcopy(self.data)
            mysql_data["infos"] = mysql_infos
            clone_subpipes.append(
                clone_mysql_instance_grants_subflow(
                    root_id=self.root_id, data=mysql_data, infos=mysql_infos, with_actuator=True
                )
            )

        root_pipe.add_parallel_sub_pipeline(sub_flow_list=clone_subpipes)

        root_pipe.run_pipeline(init_trans_data_class=MySQLCloneGrantsContext(), is_drop_random_user=True)
