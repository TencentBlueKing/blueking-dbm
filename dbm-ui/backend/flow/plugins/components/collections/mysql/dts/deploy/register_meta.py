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

from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component

from backend.db_meta.api.cluster.mysqldts import create
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.mysql.dts.constants import DtsRegisterMode

logger = logging.getLogger("flow")


class MysqlDtsRegisterClusterMetaService(BaseService):
    """注册 MySQL DTS 集群 DBM 元数据。"""

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        trans_data = data.get_one_of_inputs("trans_data")
        register_mode = kwargs.get("register_mode", DtsRegisterMode.CREATE.value)

        if register_mode == DtsRegisterMode.APPEND_WORKER.value:
            from backend.db_meta.api.cluster.mysqldts import append_worker_nodes

            append_worker_nodes(
                dts_cluster_id=kwargs["dts_cluster_id"],
                new_worker_nodes=kwargs["new_worker_nodes"],
                updater=kwargs.get("creator", ""),
            )
            trans_data.deploy_context.deployed_worker_nodes.extend(kwargs["new_worker_nodes"])
            self.log_info(_("追加 Worker 元数据成功: {}").format(kwargs["dts_cluster_id"]))
            return True

        dts_cluster = create(
            bk_biz_id=kwargs["bk_biz_id"],
            bk_cloud_id=kwargs["bk_cloud_id"],
            name=kwargs["cluster_name"],
            master_nodes=kwargs["master_nodes"],
            worker_nodes=kwargs["worker_nodes"],
            master_addr=kwargs["master_addr"],
            deploy_path=kwargs["deploy_path"],
            version=kwargs.get("version", ""),
            creator=kwargs.get("creator", ""),
            db_module_id=kwargs.get("db_module_id", 0),
        )
        trans_data.deploy_context.master_addr = kwargs["master_addr"]
        trans_data.deploy_context.deployed_master_nodes = kwargs["master_nodes"]
        trans_data.deploy_context.deployed_worker_nodes = kwargs["worker_nodes"]
        trans_data.migrate_context.master_addr = kwargs["master_addr"]
        trans_data.migrate_context.bk_cloud_id = kwargs["bk_cloud_id"]
        trans_data.migrate_context.dts_cluster_id = dts_cluster.id
        data.outputs.dts_cluster_id = dts_cluster.id
        self.log_info(_("MySQL DTS 集群元数据注册成功: id={}").format(dts_cluster.id))
        return True


class MysqlDtsRegisterClusterMetaComponent(Component):
    name = __name__
    code = "mysql_dts_register_cluster_meta"
    bound_service = MysqlDtsRegisterClusterMetaService
