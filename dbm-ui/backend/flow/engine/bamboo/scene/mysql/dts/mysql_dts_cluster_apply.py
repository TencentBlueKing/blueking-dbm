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
from typing import Dict, Optional

from django.utils.translation import gettext as _

from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_deploy_subflow import mysql_dts_deploy_subflow
from backend.flow.utils.mysql.dts.constants import get_default_deploy_path
from backend.flow.utils.mysql.dts.context import DtsHostSpec, MysqlDtsDeploySubflowInput, MysqlDtsTransData

logger = logging.getLogger("flow")


class MysqlDtsClusterApplyFlow:
    """MySQL DTS 集群独立部署 Flow。"""

    def __init__(self, root_id: str, data: Optional[Dict]):
        self.root_id = root_id
        self.data = data

    def run_flow(self):
        self.data.setdefault("uid", self.root_id)
        pipeline = Builder(root_id=self.root_id, data=self.data)
        deploy_inp = MysqlDtsDeploySubflowInput(
            root_id=self.root_id,
            bk_biz_id=int(self.data["bk_biz_id"]),
            bk_cloud_id=int(self.data["bk_cloud_id"]),
            cluster_name=self.data["cluster_name"],
            master_hosts=[DtsHostSpec(**h) for h in self.data["master_hosts"]],
            worker_hosts=[DtsHostSpec(**h) for h in self.data["worker_hosts"]],
            deploy_path=self.data.get("deploy_path") or get_default_deploy_path(self.data["cluster_name"]),
            master_ha=self.data.get("master_ha", False),
            # 介质默认取最新包，不由单据指定
            creator=self.data.get("created_by", ""),
        )
        pipeline.add_sub_pipeline(mysql_dts_deploy_subflow(deploy_inp).build_sub_process(sub_name=_("部署 DTS 集群")))
        pipeline.run_pipeline(init_trans_data_class=MysqlDtsTransData())
