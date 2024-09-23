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

from backend.db_meta.api.cluster.sqlserverha.handler import SqlserverHAClusterHandler
from backend.db_meta.api.cluster.sqlserversingle.handler import SqlserverSingleClusterHandler
from backend.db_meta.enums import ClusterPhase, ClusterType
from backend.db_meta.models import Cluster, StorageInstance
from backend.db_meta.models.sqlserver_dts import DtsStatus, SqlserverDtsInfo
from backend.flow.consts import InstanceStatus, SqlserverDtsMode
from backend.flow.utils.sqlserver.sqlserver_host import Host

logger = logging.getLogger("flow")


class SqlserverDBMeta(object):
    """
    根据单据信息和集群信息，更新cmdb
    类的方法一定以单据类型的小写进行命名，否则不能根据单据类型匹配对应的方法
    """

    def __init__(self, global_data: dict, trans_data: dict):
        """
        @param global_data : 子流程单据信息,全局只读上下文
        @param trans_data: 子流程单据信息，可交互上下文
        """
        self.global_data = global_data
        self.trans_data = trans_data

    def sqlserver_single_apply(self):
        """
        单节点集群部署录入元数据
        """
        def_resource_spec = {"sqlserver_single": {"id": 0}}
        SqlserverSingleClusterHandler.create(
            bk_biz_id=self.global_data["bk_biz_id"],
            major_version=self.global_data["db_version"],
            ip=self.global_data["master_ip"],
            clusters=self.global_data["clusters"],
            db_module_id=self.global_data["db_module_id"],
            creator=self.global_data["created_by"],
            time_zone="",
            bk_cloud_id=int(self.global_data["bk_cloud_id"]),
            resource_spec=self.global_data.get("resource_spec", def_resource_spec),
            region=self.global_data["region"],
        )
        return True

    def sqlserver_ha_apply(self):
        """
        ha集群部署录入你元数据
        """
        def_resource_spec = {"sqlserver_ha": {"id": 0}}
        SqlserverHAClusterHandler.create(
            bk_biz_id=self.global_data["bk_biz_id"],
            db_module_id=self.global_data["db_module_id"],
            major_version=self.global_data["db_version"],
            master_ip=self.global_data["master_ip"],
            slave_ip=self.global_data["slave_ip"],
            clusters=self.global_data["clusters"],
            creator=self.global_data["created_by"],
            time_zone="",
            bk_cloud_id=int(self.global_data["bk_cloud_id"]),
            resource_spec=self.global_data.get("resource_spec", def_resource_spec),
            region=self.global_data["region"],
            sync_type=self.global_data["sync_type"],
            disaster_tolerance_level=self.global_data["disaster_tolerance_level"],
        )
        return True

    def sqlserver_ha_switch(self):
        """
        ha集群部署录入你元数据
        """
        SqlserverHAClusterHandler.switch_role(
            cluster_ids=self.global_data["cluster_ids"],
            old_master=Host(**self.global_data["master"]),
            new_master=Host(**self.global_data["slave"]),
            is_force=self.global_data.get("force", False),
        )
        return True

    def cluster_offline(self):
        """
        定义更新cluster集群的为offline 状态
        """
        Cluster.objects.filter(id=self.global_data["cluster_id"]).update(phase=ClusterPhase.OFFLINE)

    def cluster_online(self):
        """
        定义更新cluster集群的为online 状态
        """
        Cluster.objects.filter(id=self.global_data["cluster_id"]).update(phase=ClusterPhase.ONLINE)

    def cluster_reset(self):
        """
        定义集群重置元数据的过程
        """
        SqlserverHAClusterHandler.cluster_reset(
            cluster_id=self.global_data["cluster_id"],
            new_cluster_name=self.global_data["new_cluster_name"],
            new_immutable_domain=self.global_data["new_immutable_domain"],
            new_slave_domain=self.global_data.get("new_slave_domain", None),
            creator=self.global_data["created_by"],
        )
        return True

    def cluster_destroy(self):
        """
        定义集群下架时元数据的过程
        """
        cluster = Cluster.objects.get(id=self.global_data["cluster_id"])
        if cluster.cluster_type == ClusterType.SqlserverHA:
            SqlserverHAClusterHandler(bk_biz_id=self.global_data["bk_biz_id"], cluster_id=cluster.id).decommission()
        else:
            SqlserverSingleClusterHandler(
                bk_biz_id=self.global_data["bk_biz_id"], cluster_id=cluster.id
            ).decommission()

        return True

    def rebuild_local_slave_state(self):
        """
        原地重建后，实例状态保持running状态
        """
        instances = StorageInstance.objects.filter(
            machine__ip=self.global_data["slave_host"]["ip"],
            machine__bk_cloud_id=self.global_data["slave_host"]["bk_cloud_id"],
            port=self.global_data["port"],
        )

        # 更新状态并保存 触发信号机制
        for instance in instances:
            instance.status = InstanceStatus.RUNNING
            instance.save()

    def rebuild_in_new_slave(self):
        """
        定义机器维度，新机重建，变更集群元数据
        """
        def_resource_spec = {"sqlserver_ha": {"id": 0}}
        SqlserverHAClusterHandler.switch_slave(
            bk_biz_id=int(self.global_data["bk_biz_id"]),
            cluster_ids=self.global_data["cluster_ids"],
            old_slave_host=Host(**self.global_data["old_slave_host"]),
            new_slave_host=Host(**self.global_data["new_slave_host"]),
            creator=self.global_data["created_by"],
            resource_spec=self.global_data.get("resource_spec", def_resource_spec),
        )
        return True

    def add_slave(self):
        """
        定义机器维度，添加slave，变更集群元数据
        """
        def_resource_spec = {"sqlserver_ha": {"id": 0}}
        SqlserverHAClusterHandler.add_slave(
            bk_biz_id=int(self.global_data["bk_biz_id"]),
            cluster_ids=self.global_data["cluster_ids"],
            new_slave_host=Host(**self.global_data["new_slave_host"]),
            creator=self.global_data["created_by"],
            resource_spec=self.global_data.get("resource_spec", def_resource_spec),
            is_stand_by=False,
        )

    def reduce_slave(self):
        """
        清理slave实例
        """
        SqlserverHAClusterHandler.reduce_slave(
            cluster_ids=self.global_data["cluster_ids"], old_slave_host=Host(**self.global_data["old_slave_host"])
        )

    def update_dts_status(self):
        """
        定义更新dts状态
        """
        if self.global_data["dts_mode"] == SqlserverDtsMode.FULL.value:
            # 全量迁移
            status = DtsStatus.FullSuccess
        elif self.global_data["dts_mode"] == SqlserverDtsMode.INCR.value and not self.global_data["is_last"]:
            # 增量迁移且触发任务不停止
            status = DtsStatus.IncrOnline
        elif self.global_data["dts_mode"] == SqlserverDtsMode.INCR.value and self.global_data["is_last"]:
            # 增量迁移且触发任务停止
            status = DtsStatus.IncrSuccess
        else:
            raise Exception(
                f"not support: dts_mode[{self.global_data['dts_mode']}]; is_last[{self.global_data['is_last']}]"
            )
        # 任务结束后变更状态
        SqlserverDtsInfo.objects.filter(id=self.global_data["dts_id"]).update(status=status)

    def modify_status_for_not_joined_dbha(self):
        """
        对未接入DBHA的主从集群，如果实例出现故障主动修改实例的状态
        """
        SqlserverHAClusterHandler.modify_status(
            cluster_id=int(self.global_data["cluster_id"]),
            ip_list=self.global_data["ip_list"],
        )
