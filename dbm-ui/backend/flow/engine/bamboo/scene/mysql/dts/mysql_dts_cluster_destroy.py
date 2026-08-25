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
from backend.flow.engine.bamboo.scene.mysql.dts.mysql_dts_cleanup_subflow import mysql_dts_cleanup_subflow
from backend.flow.utils.mysql.dts.context import MysqlDtsCleanupSubflowInput, MysqlDtsTransData
from backend.flow.utils.mysql.dts.migrate_helper import resolve_destroy_cluster_ids

logger = logging.getLogger("flow")


class MysqlDtsClusterDestroyFlow:
    """MySQL DTS 集群独立清理 Flow。"""

    def __init__(self, root_id: str, data: Optional[Dict]):
        self.root_id = root_id
        self.data = data

    def run_flow(self):
        self.data.setdefault("uid", self.root_id)
        cluster_ids = resolve_destroy_cluster_ids(self.data)
        if not cluster_ids:
            raise ValueError(_("销毁 Flow 缺少 dts_cluster_id / dts_cluster_ids"))
        dts_clusters = list(MysqlDtsCluster.objects.filter(id__in=cluster_ids))
        by_id = {c.id: c for c in dts_clusters}
        missing = [cid for cid in cluster_ids if cid not in by_id]
        if missing:
            raise MysqlDtsCluster.DoesNotExist(_("DTS 集群不存在: {}").format(missing))

        pipeline = Builder(root_id=self.root_id, data=self.data)
        recycle_hosts = self.data.get("recycle_hosts", True)
        if isinstance(recycle_hosts, list):
            recycle_flag = bool(recycle_hosts)
        else:
            recycle_flag = bool(recycle_hosts)
        subs = []
        for cid in cluster_ids:
            dts_cluster = by_id[cid]
            cleanup_inp = MysqlDtsCleanupSubflowInput(
                root_id=self.root_id,
                dts_cluster_id=dts_cluster.id,
                bk_biz_id=dts_cluster.bk_biz_id,
                bk_cloud_id=dts_cluster.bk_cloud_id,
                master_addr=dts_cluster.master_addr,
                master_nodes=dts_cluster.master_nodes,
                worker_nodes=dts_cluster.worker_nodes,
                deploy_path=dts_cluster.deploy_path,
                force_destroy=self.data.get("force_destroy", False),
                recycle_hosts=recycle_flag,
                clean_data_dir=self.data.get("clean_data_dir", True),
                creator=self.data.get("created_by", ""),
                cluster_name=dts_cluster.name,
            )
            subs.append(
                mysql_dts_cleanup_subflow(cleanup_inp).build_sub_process(
                    sub_name=_("清理 DTS 集群 {}").format(dts_cluster.name or dts_cluster.id)
                )
            )
        if len(subs) == 1:
            pipeline.add_sub_pipeline(subs[0])
        else:
            pipeline.add_parallel_sub_pipeline(sub_flow_list=subs)
        pipeline.run_pipeline(init_trans_data_class=MysqlDtsTransData())
