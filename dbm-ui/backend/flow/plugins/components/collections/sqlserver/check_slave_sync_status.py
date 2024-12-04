"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""

from pipeline.component_framework.component import Component

from backend.db_meta.enums import InstanceRole
from backend.db_meta.models import Cluster
from backend.db_meta.models.storage_set_dtl import SqlserverClusterSyncMode
from backend.flow.consts import SqlserverSyncMode
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.sqlserver.sqlserver_db_function import (
    check_always_on_status,
    exec_resume_sp,
    get_dbs_for_drs,
    get_group_name,
    get_no_sync_dbs,
    get_restoring_dbs,
)


class CheckSlaveSyncStatusService(BaseService):
    """
    判断带重建的slave处于什么状态，状态值都是用fix_number返回，不同fix_number代表不同修复流程：
    1: 可用组缺失
    2: slave可用组状态异常
    3: master部分库尚未建立同步
    4: master所有库都建立同步，同步处于健康状态
    """

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        trans_data = data.get_one_of_inputs("trans_data")

        # 获取集群的相关的信息
        cluster = Cluster.objects.get(id=kwargs["cluster_id"])
        fix_slave = cluster.storageinstance_set.get(machine__ip=kwargs["fix_slave_host"])
        master = cluster.storageinstance_set.get(instance_role=InstanceRole.BACKEND_MASTER)
        cluster_sync_mode = SqlserverClusterSyncMode.objects.get(cluster_id=cluster.id).sync_mode

        # 首先确认集群同步类型
        if cluster_sync_mode == SqlserverSyncMode.ALWAYS_ON:
            # 先确认可用组是否有配置
            sync_dbs = get_dbs_for_drs(cluster_id=cluster.id, db_list=["*"], ignore_db_list=[])
            clean_dbs = list(set(sync_dbs) | set(get_restoring_dbs(fix_slave, cluster.bk_cloud_id)))
            if not get_group_name(master_instance=master, bk_cloud_id=cluster.bk_cloud_id, is_check_group=True):
                # 如果可用组配置缺失，走建立可用组的流程
                self.log_info("group_name if null")
                data.outputs.fix_number = 1
                trans_data.sync_dbs = sync_dbs
                trans_data.clean_dbs = clean_dbs
                data.outputs["trans_data"] = trans_data
                return True

            elif not check_always_on_status(cluster, fix_slave):
                # 如果可用组状态异常，走重建可用组流程
                self.log_info("always_on_status is abnormal")
                data.outputs.fix_number = 2
                trans_data.sync_dbs = sync_dbs
                trans_data.clean_dbs = clean_dbs
                data.outputs["trans_data"] = trans_data
                return True

        # 判断数据库同步状态
        if get_no_sync_dbs(cluster_id=cluster.id):
            # 如果有数据库尚未同步，先修复同步，在判断同步是否正常
            exec_resume_sp(
                slave_instances=[fix_slave],
                master_host=master.machine.ip,
                master_port=master.port,
                bk_cloud_id=cluster.bk_cloud_id,
            )
            self.log_info("exec exec_resume_sp finish, check the result...")
            # 监测数据同步状态
            sync_dbs = get_no_sync_dbs(cluster_id=kwargs["cluster_id"])
            if sync_dbs:
                # 表示修复失败
                self.log_warning("exec exec_resume_sp unsuccessfully")
                trans_data.sync_dbs = sync_dbs
                trans_data.clean_dbs = list(set(sync_dbs) | set(get_restoring_dbs(fix_slave, cluster.bk_cloud_id)))
                data.outputs.fix_number = 3
                data.outputs["trans_data"] = trans_data
                return True
            else:
                # 代表数据库重新建立成功
                self.log_info("exec exec_resume_sp successfully")
                data.outputs.fix_number = 4
                return True

        self.log_info("no dbs fix sync")
        data.outputs.fix_number = 4
        return True


class CheckSlaveSyncStatusComponent(Component):
    name = __name__
    code = "sqlserver_check_rebuild_slave"
    bound_service = CheckSlaveSyncStatusService
