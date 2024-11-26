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

from django.utils.translation import ugettext as _
from pipeline.component_framework.component import Component

from backend.components import DRSApi
from backend.db_meta.exceptions import ClusterNotExistException
from backend.db_meta.models import Cluster, StorageInstance
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.plugins.components.collections.mysql.drop_proxy_client_in_backend import (
    DropProxyUsersInBackendService,
)
from backend.flow.utils.mysql.mysql_commom_query import show_privilege_for_user

logger = logging.getLogger("flow")


class CloneProxyUsersInBackendService(BaseService):
    """
    在集群内,根据旧proxy权限，克隆一份对新proxy的权限。proxy替换和添加单据调用
    操作步骤：
    1: 先处理新proxy在集群所有backend节点的残留权限，避免冲突。因为理论上新proxy的授权出现在集群上
    2：根据旧proxy的授权模式，给新proxy授权一份
    """

    def clone_proxy_client(
        self, origin_proxy_host: str, target_proxy_host: str, backend: StorageInstance, cluster: Cluster
    ):
        """
        克隆proxy权限
        """
        result, grant_sqls = show_privilege_for_user(
            host=origin_proxy_host, instance=backend, db_version=cluster.major_version
        )
        if not result:
            return f"[{backend.ip_port}] show proxy client[{origin_proxy_host}] failed"

        if not grant_sqls:
            self.log_info(f"[{backend.ip_port}] show proxy client[{origin_proxy_host}] is null, skip")
            return ""

        # 执行授权
        res = DRSApi.rpc(
            {
                "addresses": [backend.ip_port],
                "cmds": [i.replace(origin_proxy_host, target_proxy_host, -1) for i in grant_sqls],
                "force": False,
                "bk_cloud_id": backend.machine.bk_cloud_id,
            }
        )
        if res[0]["error_msg"]:
            return f"[{backend.ip_port}] clone proxy client[{target_proxy_host}] failed: [{res['error_msg']}]"

        return ""

    def _execute(self, data, parent_data, callback=None) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        global_data = data.get_one_of_inputs("global_data")
        try:
            cluster = Cluster.objects.get(id=kwargs["cluster_id"])
        except Cluster.DoesNotExist:
            raise ClusterNotExistException(
                cluster_id=kwargs["cluster_id"], bk_biz_id=int(global_data["bk_biz_id"]), message=_("集群不存在")
            )
        err_no = False
        for s in cluster.storageinstance_set.all():
            # 1： 先处理新proxy在集群所有backend节点的残留权限
            status, err = DropProxyUsersInBackendService.drop_proxy_client(kwargs["target_proxy_host"], s)
            if not status:
                self.log_error(err)
                err_no = True
                continue
            self.log_info(f"[{s.ip_port}] drop new proxy client[{kwargs['target_proxy_host']}] successfully")

            # 2: 根据旧proxy的授权模式，给新proxy授权一份
            log = self.clone_proxy_client(
                origin_proxy_host=kwargs["origin_proxy_host"],
                target_proxy_host=kwargs["target_proxy_host"],
                backend=s,
                cluster=cluster,
            )
            if log:
                self.log_error(log)
                err_no = True
                continue

            self.log_info(f"[{s.ip_port}]clone proxy client [{kwargs['target_proxy_host']}] successfully")

        if err_no:
            return False

        return True


class CloneProxyUsersInBackendComponent(Component):
    name = __name__
    code = "clone_proxy_client_in_backend"
    bound_service = CloneProxyUsersInBackendService
