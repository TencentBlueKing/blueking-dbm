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

from backend.db_meta.models import Cluster
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.sqlserver.sqlserver_db_function import exec_instance_app_login

logger = logging.getLogger("flow")


class ExecSqlserverLoginService(BaseService):
    """
    操作Sqlserver的业务账号，只有禁用和启动操作
    """

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        cluster = Cluster.objects.get(id=kwargs["cluster_id"])
        instance = cluster.storageinstance_set.get(machine__ip=kwargs["exec_ip"])
        if not instance:
            raise Exception(_("集群[{}]没有对应填入的ip[{}]的实例，请联系系统管理员".format(cluster.immute_domain, kwargs["exec_ip"])))

        if exec_instance_app_login(cluster, kwargs["exec_mode"], instance):
            self.log_info(f"exec app-logins-[{kwargs['exec_mode']}] in [{instance.ip_port}] successfully")
            return True

        return False


class ExecSqlserverLoginComponent(Component):
    name = __name__
    code = "exec_sqlserver_login"
    bound_service = ExecSqlserverLoginService
