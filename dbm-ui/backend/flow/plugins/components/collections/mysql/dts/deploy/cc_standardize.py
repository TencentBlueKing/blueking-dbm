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

from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.mysql.dts.cc_standardize import resolve_dts_cc_context, transfer_dts_hosts_to_cluster_module

logger = logging.getLogger("flow")


class MysqlDtsCcStandardizeService(BaseService):
    """DTS 集群 CC 标准化：托管业务 Set(db.mysql.dts) + Module(集群名) + 挪机。"""

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs") or {}
        try:
            bk_biz_id, cluster_name, ips = resolve_dts_cc_context(
                bk_biz_id=kwargs.get("bk_biz_id"),
                cluster_name=kwargs.get("cluster_name"),
                master_nodes=kwargs.get("master_nodes"),
                worker_nodes=kwargs.get("worker_nodes"),
                dts_cluster_id=kwargs.get("dts_cluster_id"),
            )
            bk_cloud_id = kwargs.get("bk_cloud_id")
            if bk_cloud_id is None and kwargs.get("dts_cluster_id"):
                from backend.db_meta.models import MysqlDtsCluster

                bk_cloud_id = MysqlDtsCluster.objects.get(id=kwargs["dts_cluster_id"]).bk_cloud_id
            if bk_cloud_id is None:
                raise ValueError("bk_cloud_id is required for DTS CC standardize")

            module_id = transfer_dts_hosts_to_cluster_module(
                bk_biz_id=bk_biz_id,
                bk_cloud_id=int(bk_cloud_id),
                cluster_name=cluster_name,
                ips=ips,
            )
            self.log_info(_("DTS CC 标准化完成: cluster={} ips={} module_id={}").format(cluster_name, ips, module_id))
            return True
        except Exception as err:  # pylint: disable=broad-except
            self.log_error(_("DTS CC 标准化失败: {}").format(err))
            logger.exception("DTS CC standardize failed")
            return False


class MysqlDtsCcStandardizeComponent(Component):
    name = __name__
    code = "mysql_dts_cc_standardize"
    bound_service = MysqlDtsCcStandardizeService
