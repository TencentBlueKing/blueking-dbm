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
from copy import deepcopy
from typing import Dict, List, Optional

from django.utils.translation import ugettext as _

from backend.db_meta.models import Cluster
from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.engine.bamboo.scene.mysql.deploy_peripheraltools.subflow import standardize_mysql_cluster_subflow
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
        cluster_type = self.data["cluster_type"]
        bk_biz_id = self.data["bk_biz_id"]

        # 按云区域聚合的集群描述结构
        # {
        #    0: {
        #            "single.test.db": {
        #                                 "proxy": ["1.1.1.1:1000", ...],
        #                                 "storage": ["2.2.2.2:2000", ...],
        #                              },
        #            ...
        #       },
        #    ...
        bk_cloud_id_cluster_details = {}

        for cluster_obj in Cluster.objects.filter(bk_biz_id=bk_biz_id, cluster_type=cluster_type, id__in=cluster_ids):
            # 集群描述结构
            # {
            #    "proxy": ["1.1.1.1:1000", ...],
            #    "storage": ["2.2.2.2:20000", ]
            # {
            cluster_detail: Dict[str, List[str]] = {
                "proxy": [i.ip_port for i in cluster_obj.proxyinstance_set.all()],
                "storage": [i.ip_port for i in cluster_obj.storageinstance_set.all()],
            }
            if cluster_obj.bk_cloud_id not in bk_cloud_id_cluster_details:
                bk_cloud_id_cluster_details[cluster_obj.bk_cloud_id] = {}

            bk_cloud_id_cluster_details[cluster_obj.bk_cloud_id][cluster_obj.immute_domain] = cluster_detail

        subpipes = []
        for bk_cloud_id, cluster_details in bk_cloud_id_cluster_details.items():
            subpipes.append(
                standardize_mysql_cluster_subflow(
                    root_id=self.root_id,
                    data=copy.deepcopy(self.data),
                    bk_cloud_id=bk_cloud_id,
                    bk_biz_id=bk_biz_id,
                    cluster_type=self.data.get("cluster_type"),
                    clusters_detail=cluster_details,
                    departs=self.data.get("departs"),
                    with_deploy_binary=self.data.get("with_deploy_binary"),
                    with_push_config=self.data.get("with_push_config"),
                    with_collect_sysinfo=self.data.get("with_collect_sysinfo"),
                    with_actuator=True,
                    with_bk_plugin=self.data.get("with_bk_plugin"),
                    with_cc_standardize=self.data.get("with_cc_standardize"),
                    with_instance_standardize=self.data.get("with_instance_standardize"),
                )
            )

        pipe = Builder(root_id=self.root_id, data=copy.deepcopy(self.data), need_random_pass_cluster_ids=cluster_ids)
        pipe.add_parallel_sub_pipeline(
            sub_flow_list=subpipes,
        )

        logger.info(_("构建MySQL标准化流程成功"))
        pipe.run_pipeline(is_drop_random_user=True, init_trans_data_class=SystemInfoContext())
