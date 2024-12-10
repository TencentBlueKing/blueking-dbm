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

from typing import Dict, Optional

from django.utils.translation import ugettext as _

from backend.db_meta.enums import ClusterEntryRole, ClusterEntryType
from backend.db_meta.models import Cluster, ClusterEntry
from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.plugins.components.collections.common.clone_priv_rules_to_other_biz import (
    ClonePrivRulesToOtherComponent,
)
from backend.flow.plugins.components.collections.common.pause import PauseComponent
from backend.flow.plugins.components.collections.common.transfer_cluster_meta_to_other_biz import (
    TransferClusterMetaToOtherBizComponent,
    UpdateClusterDnsBelongAppComponent,
)


class TransferMySQLClusterToOtherBizFlow(object):
    """
    将MySQL集群转移到其他业务
    """

    def __init__(self, root_id: str, data: Optional[Dict]) -> None:
        self.root_id = root_id
        self.data = data
        self.bk_biz_id = data.get("bk_biz_id")
        self.target_biz_id = data.get("target_biz_id")
        self.cluster_domain_list = data.get("cluster_domain_list")
        self.dest_db_module_id = data.get("db_module_id")
        self.need_clone_priv_rules = data.get("need_clone_priv_rules")

    def transfer_to_other_biz_flow(self):

        clusters = Cluster.objects.filter(bk_biz_id=self.bk_biz_id, immute_domain__in=self.cluster_domain_list).all()
        bk_cloud_ids = []
        source_bk_biz_ids = []
        slave_domain_list = []
        for cluster in clusters:
            bk_cloud_ids.append(cluster.bk_cloud_id)
            source_bk_biz_ids.append(cluster.bk_biz_id)
            slave_entrys = ClusterEntry.objects.filter(
                cluster_id=cluster.id,
                cluster_entry_type=ClusterEntryType.DNS,
                role=ClusterEntryRole.SLAVE_ENTRY,
            ).all()
            for slave_entry in slave_entrys:
                slave_domain_list.append(slave_entry.entry)

        uniq_bk_cloud_ids = list(set(bk_cloud_ids))
        uniq_source_bk_biz_ids = list(set(source_bk_biz_ids))
        if len(uniq_bk_cloud_ids) != 1:
            raise Exception(_("迁移的集群必须在同一个云区域"))
        if len(uniq_source_bk_biz_ids) != 1:
            raise Exception(_("迁移的集群必须在同一个业务"))

        bk_cloud_id = uniq_bk_cloud_ids[0]
        source_bk_biz_id = uniq_source_bk_biz_ids[0]

        p = Builder(root_id=self.root_id, data=self.data)

        if self.need_clone_priv_rules:
            p.add_act(
                act_name=_("clone权限规则"),
                act_component_code=ClonePrivRulesToOtherComponent.code,
                kwargs={
                    "source_biz": self.bk_biz_id,
                    "target_biz_id": self.target_biz_id,
                },
            )

        p.add_act(
            act_name=_("迁移元数据"),
            act_component_code=TransferClusterMetaToOtherBizComponent.code,
            kwargs={
                "target_biz_id": self.target_biz_id,
                "cluster_domain_list": self.cluster_domain_list,
                "db_module_id": self.dest_db_module_id,
            },
        )

        p.add_act(act_name=_("请先跑一下集群标准化，完成之后确认"), act_component_code=PauseComponent.code, kwargs={})

        p.add_act(
            act_name=_("更新dns记录归属业务"),
            act_component_code=UpdateClusterDnsBelongAppComponent.code,
            kwargs={
                "target_biz_id": self.target_biz_id,
                "source_biz_id": source_bk_biz_id,
                "cluster_domain_list": self.cluster_domain_list + slave_domain_list,
                "db_module_id": self.dest_db_module_id,
                "bk_cloud_id": bk_cloud_id,
            },
        )

        p.run_pipeline(is_drop_random_user=False)
