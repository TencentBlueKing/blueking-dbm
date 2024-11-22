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

from pipeline.component_framework.component import Component

from backend.db_meta.models import Cluster
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.sqlserver.sqlserver_bk_config import (
    get_module_infos,
    get_sqlserver_alarm_config,
    get_sqlserver_backup_config,
)
from backend.flow.utils.sqlserver.sqlserver_db_function import insert_sqlserver_config

logger = logging.getLogger("flow")


class InsertAppSettingService(BaseService):
    """
    插入实例app_setting配置数据
    """

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")

        # 理论上一个集群对应一个主域名
        cluster = Cluster.objects.get(immute_domain=kwargs["cluster_domain"])

        storages = cluster.storageinstance_set.filter(machine__ip__in=kwargs["ips"])

        # 获取集群字符集配置
        charset = get_module_infos(
            bk_biz_id=cluster.bk_biz_id, db_module_id=cluster.db_module_id, cluster_type=cluster.cluster_type
        )["charset"]

        # 获取集群的备份配置
        backup_config = get_sqlserver_backup_config(
            bk_biz_id=cluster.bk_biz_id,
            db_module_id=cluster.db_module_id,
            cluster_domain=cluster.immute_domain,
        )

        # 获取集群的个性化配置
        alarm_config = get_sqlserver_alarm_config(
            bk_biz_id=cluster.bk_biz_id,
            db_module_id=cluster.db_module_id,
            cluster_domain=cluster.immute_domain,
        )

        if not storages:
            raise Exception(f"no storages in cluster [{cluster.name}]: ips:{kwargs['ips']}")

        # 配置数据
        if insert_sqlserver_config(
            cluster=cluster,
            storages=list(storages),
            charset=charset,
            backup_config=backup_config,
            alarm_config=alarm_config,
            is_get_old_backup_config=kwargs["is_get_old_backup_config"],
        ):
            self.log_info("exec insert-app-setting successfully")
            return True

        return False


class InsertAppSettingComponent(Component):
    name = __name__
    code = "sqlserver_insert_app_setting"
    bound_service = InsertAppSettingService
