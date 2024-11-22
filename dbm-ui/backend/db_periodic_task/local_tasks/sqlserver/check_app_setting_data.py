"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""

from backend.db_meta.enums import ClusterPhase, ClusterType, InstanceInnerRole, InstanceRole, InstanceStatus
from backend.db_meta.models import Cluster, StorageInstance
from backend.db_meta.models.storage_set_dtl import SqlserverClusterSyncMode
from backend.db_report.models.sqlserver_check_report import (
    SqlserverCheckAppSettingReport,
    SqlserverCheckJobSyncReport,
    SqlserverCheckLinkServerReport,
    SqlserverCheckSysJobStatuReport,
    SqlserverCheckUserSyncReport,
)
from backend.flow.utils.sqlserver.sqlserver_bk_config import (
    get_module_infos,
    get_sqlserver_alarm_config,
    get_sqlserver_backup_config,
)
from backend.flow.utils.sqlserver.sqlserver_db_function import (
    check_ha_config,
    check_sys_job_status,
    fix_app_setting_data,
    get_app_setting_data,
    insert_sqlserver_config,
)


class CheckAppSettingData(object):
    """
    已dbm元数据为准
    检查实例的app_setting表的信息是否符合预期，如果存在信息不一致，则需要已某种方式输出告知相关DBA
    """

    def __init__(self):
        # 获取所有的online状态的cluster
        self.clusters = Cluster.objects.prefetch_related(
            "storageinstance_set",
            "storageinstance_set__machine",
        ).filter(phase=ClusterPhase.ONLINE, cluster_type__in=[ClusterType.SqlserverHA, ClusterType.SqlserverSingle])

    def check_task(self):
        """
        定义巡检逻辑
        """
        for cluster in self.clusters:
            print(cluster.name)
            self.check_app_setting_data(cluster)
            self.check_job_is_disabled(cluster)
            if cluster.cluster_type == ClusterType.SqlserverHA:
                master = cluster.storageinstance_set.get(instance_inner_role=InstanceInnerRole.MASTER)
                for s in cluster.storageinstance_set.filter(
                    status=InstanceStatus.RUNNING, instance_inner_role=InstanceInnerRole.SLAVE
                ):
                    self.check_user(master_instance=master, slave_instance=s, cluster=cluster)
                    self.check_job(master_instance=master, slave_instance=s, cluster=cluster)
                    self.check_link_server(master_instance=master, slave_instance=s, cluster=cluster)

    @staticmethod
    def fix_app_setting_data(cluster: Cluster, instance: StorageInstance, sync_mode: str, master: StorageInstance):
        """
        存在不一致元数据，进行修复
        """
        is_fix = 0
        status, msg = fix_app_setting_data(cluster=cluster, instance=instance, sync_mode=sync_mode, master=master)
        if status:
            is_fix = 1
        SqlserverCheckAppSettingReport.objects.create(
            cluster=cluster.name,
            cluster_type=cluster.cluster_type,
            instance_host=instance.machine.ip,
            instance_port=instance.port,
            is_inconsistent=1,
            is_fix=is_fix,
            status=status,
            msg=msg,
        )
        return True

    @staticmethod
    def add_app_setting_data(cluster: Cluster, instance: StorageInstance):
        """
        插入app_setting数据
        """
        is_fix = 0
        fix_status = False
        msg = "fix failed"
        # 获取集群字符集配置
        charset = get_module_infos(
            bk_biz_id=cluster.bk_biz_id,
            db_module_id=cluster.db_module_id,
            cluster_type=ClusterType(cluster.cluster_type),
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

        # 配置数据
        try:
            fix_status = insert_sqlserver_config(
                cluster=cluster,
                storages=[instance],
                charset=charset,
                backup_config=backup_config,
                alarm_config=alarm_config,
            )
        except Exception:
            is_fix = 0

        if fix_status:
            is_fix = 1
            msg = "fix successfully"

        SqlserverCheckAppSettingReport.objects.create(
            cluster=cluster.name,
            cluster_type=cluster.cluster_type,
            instance_host=instance.machine.ip,
            instance_port=instance.port,
            is_inconsistent=1,
            is_fix=is_fix,
            status=fix_status,
            msg=msg,
        )
        return True

    def check_app_setting_data(self, cluster: Cluster):
        master = cluster.storageinstance_set.get(instance_role__in=[InstanceRole.ORPHAN, InstanceRole.BACKEND_MASTER])
        if cluster.cluster_type == ClusterType.SqlserverHA:
            sync_mode = SqlserverClusterSyncMode.objects.get(cluster_id=cluster.id).sync_mode
        else:
            sync_mode = ""

        # 按照集群维度查询所有的实例，状态running中的
        for instance in cluster.storageinstance_set.filter(status=InstanceStatus.RUNNING):
            data, err = get_app_setting_data(instance=instance, bk_cloud_id=cluster.bk_cloud_id)
            if data is None:
                # 如果返回是空则,则大概率是访问异常，录入异常信息,跳过这次的校验
                SqlserverCheckAppSettingReport.objects.create(
                    cluster=cluster.name,
                    cluster_type=cluster.cluster_type,
                    instance_host=instance.machine.ip,
                    instance_port=instance.port,
                    is_inconsistent=1,
                    is_fix=0,
                    status=False,
                    msg=err,
                )
                continue

            if len(data) == 0:
                # 则说明没有配置app_setting,需要重新执行
                self.add_app_setting_data(cluster=cluster, instance=instance)

            elif (
                int(data["APP"]) != cluster.bk_biz_id
                or int(data["BK_BIZ_ID"]) != cluster.bk_biz_id
                or int(data["BK_CLOUD_ID"]) != cluster.bk_cloud_id
                or int(data["CLUSTER_ID"]) != cluster.id
                or data["CLUSTER_DOMAIN"] != cluster.immute_domain
                or int(data["PORT"]) != instance.port
                or data["ROLE"] != instance.instance_inner_role
                or data["SYNCHRONOUS_MODE"] != sync_mode
                or data["MASTER_IP"] != master.machine.ip
                or int(data["MASTER_PORT"]) != master.port
            ):
                # 尝试修复数据
                self.fix_app_setting_data(cluster=cluster, instance=instance, sync_mode=sync_mode, master=master)

    @staticmethod
    def check_user(master_instance: StorageInstance, slave_instance: StorageInstance, cluster: Cluster):
        """
        检查主从的用户是否一致
        """
        status, msg = check_ha_config(
            master_instance=master_instance,
            slave_instance=slave_instance,
            bk_cloud_id=cluster.bk_cloud_id,
            check_tag="user",
        )
        if not status:
            SqlserverCheckUserSyncReport.objects.create(
                cluster=cluster.name,
                cluster_type=cluster.cluster_type,
                instance_host=slave_instance.machine.ip,
                instance_port=slave_instance.port,
                is_user_inconsistent=1,
                status=status,
                msg=msg,
            )

    @staticmethod
    def check_job(master_instance: StorageInstance, slave_instance: StorageInstance, cluster: Cluster):
        """
        检测主从的业务作业是否一致
        """
        status, msg = check_ha_config(
            master_instance=master_instance,
            slave_instance=slave_instance,
            bk_cloud_id=cluster.bk_cloud_id,
            check_tag="job",
        )
        if not status:
            SqlserverCheckJobSyncReport.objects.create(
                cluster=cluster.name,
                cluster_type=cluster.cluster_type,
                instance_host=slave_instance.machine.ip,
                instance_port=slave_instance.port,
                is_job_inconsistent=1,
                status=status,
                msg=msg,
            )

    @staticmethod
    def check_link_server(master_instance: StorageInstance, slave_instance: StorageInstance, cluster: Cluster):
        """
        检测主从的link_server是否一致
        """
        status, msg = check_ha_config(
            master_instance=master_instance,
            slave_instance=slave_instance,
            bk_cloud_id=cluster.bk_cloud_id,
            check_tag="job",
        )
        if not status:
            SqlserverCheckLinkServerReport.objects.create(
                cluster=cluster.name,
                cluster_type=cluster.cluster_type,
                instance_host=slave_instance.machine.ip,
                instance_port=slave_instance.port,
                is_link_server_inconsistent=1,
                status=status,
                msg=msg,
            )

    @staticmethod
    def check_job_is_disabled(cluster: Cluster):
        # 按照集群维度查询所有的实例，状态running中的
        for instance in cluster.storageinstance_set.filter(status=InstanceStatus.RUNNING):
            status, msg = check_sys_job_status(cluster=cluster, instance=instance)
            if not status:
                # 只有异常才记录
                SqlserverCheckSysJobStatuReport.objects.create(
                    cluster=cluster.name,
                    cluster_type=cluster.cluster_type,
                    instance_host=instance.machine.ip,
                    instance_port=instance.port,
                    is_job_disable=1,
                    status=status,
                    msg=msg,
                )
