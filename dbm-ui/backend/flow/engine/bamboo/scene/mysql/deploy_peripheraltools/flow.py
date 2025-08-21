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
from collections import defaultdict
from copy import deepcopy
from typing import Dict, Optional

from django.utils.translation import ugettext as _

from backend.db_meta.models import Cluster
from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.engine.bamboo.scene.mysql.deploy_peripheraltools.departs import ALLDEPARTS
from backend.flow.engine.bamboo.scene.mysql.deploy_peripheraltools.subflow import (
    standardize_mysql_cluster_by_cluster_subflow,
)
from backend.flow.utils.mysql.mysql_context_dataclass import SystemInfoContext

logger = logging.getLogger("flow")


class MySQLStandardizeFlow(object):
    def __init__(self, root_id: str, data: Optional[Dict]):
        self.root_id = root_id
        self.data = deepcopy(data)

    def new_bill(self):
        """
        独立提交的标准化单据
        限定集群类型
        不支持部分实例标准化, 必须整集群
        """
        cluster_ids = list(set(self.data["cluster_ids"]))
        bk_biz_id = self.data["bk_biz_id"]

        bk_cloud_id_clusters = defaultdict(list)

        for cluster_obj in Cluster.objects.filter(bk_biz_id=bk_biz_id, id__in=cluster_ids):
            bk_cloud_id_clusters[cluster_obj.bk_cloud_id].append(cluster_obj.pk)

        subpipes = []
        for bk_cloud_id, cloud_cluster_ids in bk_cloud_id_clusters.items():
            subpipes.append(
                standardize_mysql_cluster_by_cluster_subflow(
                    root_id=self.root_id,
                    data=copy.deepcopy(self.data),
                    bk_cloud_id=bk_cloud_id,
                    bk_biz_id=bk_biz_id,
                    cluster_ids=list(set(cloud_cluster_ids)),
                    departs=ALLDEPARTS,
                    with_deploy_binary=self.data.get("with_deploy_binary", True),
                    with_push_config=self.data.get("with_push_config", True),
                    with_collect_sysinfo=self.data.get("with_collect_sysinfo", True),
                    with_actuator=True,
                    with_bk_plugin=self.data.get("with_deploy_binary", True),
                    with_cc_standardize=self.data.get("with_cc_standardize", False),
                    with_instance_standardize=self.data.get("with_instance_standardize", False),
                    with_backup_client=self.data.get("with_deploy_binary", True),
                    with_exporter_config=self.data.get("with_push_config", True),
                )
            )

        pipe = Builder(root_id=self.root_id, data=copy.deepcopy(self.data), need_random_pass_cluster_ids=cluster_ids)
        pipe.add_parallel_sub_pipeline(
            sub_flow_list=subpipes,
        )

        logger.info(_("构建MySQL标准化流程成功"))
        pipe.run_pipeline(is_drop_random_user=True, init_trans_data_class=SystemInfoContext())
