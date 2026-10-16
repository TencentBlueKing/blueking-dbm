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
import logging.config
from typing import Dict, Optional

from django.utils.translation import gettext as _

from backend.db_meta.models import Cluster
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.mysql.common.rollback_domain_exchange import (
    rollback_clb_exchange_subflow,
    rollback_domain_exchange_subflow,
    rollback_users_grant,
)
from backend.flow.utils.mysql.mysql_context_dataclass import MySQLFlashBackContext

logger = logging.getLogger("flow")


class MysqlRollbackSwitchFlow(object):
    """
    mysql rollback switch 新机回档关联的切换单据
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递过来的参数列表，是dict格式
        """
        self.root_id = root_id
        self.data = data

    def mysql_rollback_switch_flow(self):
        """
        mysql_rollback_switch_flow 集群域名互切
        tendbHa集群间切换：
        1、检查配置项
        2、proxy权限复制
        3、后端db dr权限复制
        4、切换proxy节点映射的域名、切换从节点映射的域名
        5、修改域名相关元数据信息
        """

        cluster_ids = [i["source_cluster_id"] for i in self.data["infos"]]
        dst_cluster_ids = [i["destination_cluster_id"] for i in self.data["infos"]]
        cluster_ids.extend(dst_cluster_ids)
        mysql_rollback_switch_pipeline = Builder(
            root_id=self.root_id, data=copy.deepcopy(self.data), need_random_pass_cluster_ids=list(set(cluster_ids))
        )
        sub_pipeline_list = []
        for info in self.data["infos"]:
            src_cluster = Cluster.objects.get(id=info["source_cluster_id"])
            dst_cluster = Cluster.objects.get(id=info["destination_cluster_id"])

            ticket_data = {
                "uid": self.data["uid"],
                "created_by": self.data["created_by"],
                "bk_biz_id": src_cluster.bk_biz_id,
                "bk_cloud_id": src_cluster.bk_cloud_id,
                "module": src_cluster.db_module_id,
                "db_module_id": src_cluster.db_module_id,
                "ticket_type": self.data["ticket_type"],
            }
            sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(ticket_data))

            # 步骤1 检查配置项
            # 步骤2 复制权限
            sync_grants_subflow = rollback_users_grant(
                root_id=self.root_id,
                ticket_data=copy.deepcopy(ticket_data),
                src_cluster=src_cluster,
                dst_cluster=dst_cluster,
            )
            sub_pipeline.add_sub_pipeline(sub_flow=sync_grants_subflow)

            # 步骤3 集群互换域名
            exchange_domain_subflow = rollback_domain_exchange_subflow(
                root_id=self.root_id,
                ticket_data=copy.deepcopy(ticket_data),
                src_cluster=src_cluster,
                dst_cluster=dst_cluster,
            )
            sub_pipeline.add_sub_pipeline(sub_flow=exchange_domain_subflow)

            #  步骤3 域名互切、包括clb域名、proxy 域名。从库域名
            exchange_clb_subflow = rollback_clb_exchange_subflow(
                root_id=self.root_id,
                ticket_data=copy.deepcopy(ticket_data),
                src_cluster=src_cluster,
                dst_cluster=dst_cluster,
            )
            if exchange_clb_subflow is not None:
                sub_pipeline.add_sub_pipeline(sub_flow=exchange_clb_subflow)

            #  todo 标准化。

            sub_pipeline_list.append(sub_pipeline.build_sub_process(sub_name=_("新机回档集群间互切")))
        mysql_rollback_switch_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipeline_list)
        mysql_rollback_switch_pipeline.run_pipeline(
            init_trans_data_class=MySQLFlashBackContext(), is_drop_random_user=True
        )
