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

from django.db.models import QuerySet
from django.utils.translation import ugettext as _
from pipeline.component_framework.component import Component

from backend.db_meta.enums import InstanceStatus
from backend.db_meta.exceptions import ClusterNotExistException
from backend.db_meta.models import Cluster
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.sqlserver.sqlserver_db_function import create_sqlserver_random_job_user

logger = logging.getLogger("flow")


class SqlserverAddJobUserService(BaseService):
    """
    为Sqlserver单据添加job的临时本地账号，操作目标实例
    单据是以集群维度来添加，如果单据涉及到集群，应该统一添加账号密码，以便后续操作方便
    """

    def _add_job_user(
        self,
        job_root_id: str,
        pwd: str,
        sid: str,
        storages: QuerySet,
        other_instances: list,
        bk_cloud_id: int,
    ) -> bool:
        # 执行添加随机账号
        ret = create_sqlserver_random_job_user(
            job_root_id=job_root_id,
            pwd=pwd,
            sid=sid,
            storages=storages,
            other_instances=other_instances,
            bk_cloud_id=bk_cloud_id,
        )

        # 判断结果
        is_error = False
        for info in ret:
            if info["error_msg"]:
                self.log_error(f"add_job_user in instance [{info['address']}]: err: [{info['error_msg']}]")
                if info["address"] in other_instances:
                    # 如果在集群之外的实例报错，直接异常
                    is_error = True

                inst_status = storages.get(
                    machine__ip=info["address"].split(":")[0], port=int(info["address"].split(":")[1])
                )
                if inst_status == InstanceStatus.UNAVAILABLE:
                    # 如果实例的状态本身是unavailable，则失败可以忽略
                    self.log_warning(f"the instance [{info['address']}] is already unavailable, ignore")
                    continue
                is_error = True

        return is_error

    def _execute(self, data, parent_data, callback=None) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        global_data = data.get_one_of_inputs("global_data")

        for cluster_id in kwargs["cluster_ids"]:
            # 获取每个cluster_id对应的对象
            try:
                cluster = Cluster.objects.get(id=cluster_id, bk_biz_id=global_data["bk_biz_id"])
            except Cluster.DoesNotExist:
                raise ClusterNotExistException(
                    cluster_id=cluster_id, bk_biz_id=global_data["bk_biz_id"], message=_("集群不存在")
                )

            # 执行
            if self._add_job_user(
                job_root_id=global_data["job_root_id"],
                pwd=global_data["job_root_id"],
                sid=kwargs["sid"],
                storages=cluster.storageinstance_set.all(),
                other_instances=kwargs["other_instances"],
                bk_cloud_id=cluster.bk_cloud_id,
            ):
                self.log_error(f"execute add random-job-user failed in cluster [{cluster.name}]")
                return False

            self.log_info(f"execute add job random-job-user successfully in cluster [{cluster.name}]")

        return True


class SqlserverAddJobUserComponent(Component):
    name = __name__
    code = "sqlserver_add_job_user"
    bound_service = SqlserverAddJobUserService
