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
from backend.flow.utils.mysql.dts.migrate_helper import load_active_dts_cluster

logger = logging.getLogger("flow")


class MysqlDtsPrepareMigrateUserService(BaseService):
    """写入临时账号，并在 migrate 层解析一次 DTS 集群主键（deploy 子流程 trans_data 不上行）。"""

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        trans_data = data.get_one_of_inputs("trans_data")

        dts_user = kwargs.get("dts_user") or ""
        dts_password = kwargs.get("dts_password") or ""
        grant_hosts = list(kwargs.get("grant_hosts") or [])
        grant_targets = list(kwargs.get("grant_targets") or [])

        if not dts_user or not dts_password:
            self.log_error(_("dts_user/dts_password 为空，无法准备迁移临时账号"))
            return False
        if not grant_hosts:
            self.log_error(_("grant_hosts 为空，拒绝使用 %% 授权，请先确保 DTS Worker 可解析"))
            return False
        if not grant_targets:
            self.log_error(_("grant_targets 为空，未找到需要授权的迁移实例"))
            return False

        migrate_context = trans_data.migrate_context
        dts_cluster = load_active_dts_cluster(
            dts_cluster_id=kwargs.get("dts_cluster_id") or migrate_context.dts_cluster_id,
            bk_biz_id=kwargs.get("bk_biz_id"),
            cluster_name=kwargs.get("cluster_name") or getattr(migrate_context, "cluster_name", None),
        )
        if dts_cluster is None:
            self.log_error(
                _("未找到可写入上下文的 DTS 集群: dts_cluster_id={}, bk_biz_id={}, cluster_name={}").format(
                    kwargs.get("dts_cluster_id"),
                    kwargs.get("bk_biz_id"),
                    kwargs.get("cluster_name"),
                )
            )
            return False

        migrate_context.dts_user = dts_user
        migrate_context.dts_password = dts_password
        migrate_context.grant_hosts = grant_hosts
        migrate_context.grant_targets = grant_targets
        migrate_context.dts_cluster_id = dts_cluster.id
        migrate_context.cluster_name = dts_cluster.name or ""
        migrate_context.master_addr = dts_cluster.master_addr
        migrate_context.bk_cloud_id = dts_cluster.bk_cloud_id
        data.outputs["trans_data"] = trans_data
        self.log_info(
            _("准备 DTS 迁移临时账号: user={}, hosts={}, targets={}, dts_cluster_id={}").format(
                dts_user, len(grant_hosts), len(grant_targets), dts_cluster.id
            )
        )
        return True


class MysqlDtsPrepareMigrateUserComponent(Component):
    name = __name__
    code = "mysql_dts_prepare_migrate_user"
    bound_service = MysqlDtsPrepareMigrateUserService
