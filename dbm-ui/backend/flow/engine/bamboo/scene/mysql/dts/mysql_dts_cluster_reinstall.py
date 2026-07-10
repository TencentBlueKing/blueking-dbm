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

from backend.db_meta.models import MysqlDtsCluster
from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_reinstall_subflow import mysql_dts_reinstall_subflow
from backend.flow.utils.mysql.dts.context import MysqlDtsReinstallSubflowInput, MysqlDtsTransData

logger = logging.getLogger("flow")


class MysqlDtsClusterReinstallFlow:
    """MySQL DTS 集群重装 Flow。

    原地重装：停止现有 DTS 进程，下发新版介质，仅更新 bin 软链接后按原节点名拉起，
    经 OpenAPI 连通性验收通过后回写元数据版本。

    注意：
    - 不渲染/推送配置（既有 conf 绝对不动）
    - 不 rm -rf deploy_path
    - 支持 force_reinstall 强制重装（跳过活跃迁移检查）
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        self.root_id = root_id
        self.data = data

    def run_flow(self):
        self.data.setdefault("uid", self.root_id)
        dts_cluster = MysqlDtsCluster.objects.get(id=self.data["dts_cluster_id"])
        pipeline = Builder(root_id=self.root_id, data=self.data)
        reinstall_inp = MysqlDtsReinstallSubflowInput(
            root_id=self.root_id,
            dts_cluster_id=dts_cluster.id,
            bk_biz_id=dts_cluster.bk_biz_id,
            bk_cloud_id=dts_cluster.bk_cloud_id,
            master_addr=dts_cluster.master_addr,
            master_nodes=dts_cluster.master_nodes,
            worker_nodes=dts_cluster.worker_nodes,
            deploy_path=dts_cluster.deploy_path,
            force_reinstall=self.data.get("force_reinstall", False),
            dts_pkg_id=self.data.get("dts_pkg_id"),
            creator=self.data.get("created_by", ""),
        )
        pipeline.add_sub_pipeline(
            mysql_dts_reinstall_subflow(reinstall_inp).build_sub_process(sub_name=_("重装 DTS 集群"))
        )
        pipeline.run_pipeline(init_trans_data_class=MysqlDtsTransData())
