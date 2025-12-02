"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
import copy
from dataclasses import asdict

from django.utils.translation import gettext as _

from backend.configuration.constants import DBType
from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.models import Cluster
from backend.flow.consts import TendbSingleRestoreType
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.mysql.clone_user import CloneUserComponent
from backend.flow.plugins.components.collections.mysql.dns_manage import MySQLDnsManageComponent
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.mysql_check_slave_delay import MySQLCheckSlaveDelayComponent
from backend.flow.plugins.components.collections.mysql.mysql_rds_execute import MySQLExecuteRdsComponent
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.utils.mysql.mysql_act_dataclass import (
    CheckSlaveStatusKwargs,
    CreateDnsKwargs,
    DownloadMediaKwargs,
    ExecActuatorKwargs,
    ExecuteRdsKwargs,
    InstanceUserCloneKwargs,
    RecycleDnsRecordKwargs,
)
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload


def single_migrate_switch_sub_flow(
    root_id: str,
    ticket_data: dict,
    orphan_restore_type: str,
    cluster: Cluster,
    old_orphan_ip: str,
    new_orphan_ip: str,
    domains: list,
):
    """"""
    #  todo tendbSingle 切换过程:
    #  1. 克隆权限(故障迁移跳过)
    #  2. 设置原实例为readonly (故障迁移跳过)
    #  3. 添加新节点域名
    #  4. 删除旧节点域名
    #  5. 停止目标实例同步 (实时同步单据适用)
    #  6. 停止目标实例. ((故障迁移跳过)
    #  7. 由于旧实例被停止,这里屏蔽旧实例告警15天。
    #  附: tendbSingle不做链接检查/数据一致性检查(日常无检查), 主从同步数据是否要生成checksum单据。
    old_orphan_storage = cluster.storageinstance_set.get(
        machine__ip=old_orphan_ip, machine__bk_cloud_id=cluster.bk_cloud_id
    )
    old_orphan = "{}{}{}".format(old_orphan_ip, IP_PORT_DIVIDER, old_orphan_storage.port)
    new_orphan = "{}{}{}".format(new_orphan_ip, IP_PORT_DIVIDER, old_orphan_storage.port)
    sub_pipeline = SubBuilder(root_id=root_id, data=copy.deepcopy(ticket_data))

    # if orphan_restore_type not in [
    #     TendbSingleRestoreType.RESTORE_WITH_STRUCT,
    #     TendbSingleRestoreType.RESTORE_WITH_DATA,
    # ]:
    sub_pipeline.add_act(
        act_name=_("下发db-actuator介质"),
        act_component_code=TransFileComponent.code,
        kwargs=asdict(
            DownloadMediaKwargs(
                bk_cloud_id=cluster.bk_cloud_id,
                exec_ip=[old_orphan_ip, new_orphan_ip],
                file_list=GetFileList(db_type=DBType.MySQL).get_db_actuator_package(),
            )
        ),
    )
    clone_data = [
        {
            "source": old_orphan,
            "target": new_orphan,
            "bk_cloud_id": cluster.bk_cloud_id,
        }
    ]

    if orphan_restore_type in [
        TendbSingleRestoreType.REPLICATE_WITH_STRUCT,
        TendbSingleRestoreType.REPLICATE_WITH_DATA,
    ]:
        sub_pipeline.add_act(
            act_name=_("检查主从延迟 {}").format(new_orphan),
            act_component_code=MySQLCheckSlaveDelayComponent.code,
            kwargs=asdict(
                CheckSlaveStatusKwargs(
                    bk_cloud_id=cluster.bk_cloud_id,
                    instance_ip=new_orphan_ip,
                    instance_port=old_orphan_storage.port,
                    slave_delay_threshold=100000,
                    check_file_delay=1,
                )
            ),
        )

    sub_pipeline.add_act(
        act_name=_("克隆权限"),
        act_component_code=CloneUserComponent.code,
        kwargs=asdict(InstanceUserCloneKwargs(clone_data=clone_data)),
    )

    sub_pipeline.add_act(
        act_name=_("源节点{} set global read_only=ON ").format(old_orphan_storage.ip_port),
        act_component_code=MySQLExecuteRdsComponent.code,
        kwargs=asdict(
            ExecuteRdsKwargs(
                bk_cloud_id=cluster.bk_cloud_id,
                instance_ip=old_orphan_storage.machine.ip,
                instance_port=old_orphan_storage.port,
                sqls=["set global read_only=ON"],
            )
        ),
    )

    if orphan_restore_type in [
        TendbSingleRestoreType.REPLICATE_WITH_STRUCT,
        TendbSingleRestoreType.REPLICATE_WITH_DATA,
    ]:
        sub_pipeline.add_act(
            act_name=_("设置readOnly后检查主从延迟 {}").format(new_orphan),
            act_component_code=MySQLCheckSlaveDelayComponent.code,
            kwargs=asdict(
                CheckSlaveStatusKwargs(
                    bk_cloud_id=cluster.bk_cloud_id,
                    instance_ip=new_orphan_ip,
                    instance_port=old_orphan_storage.port,
                    slave_delay_threshold=0,
                )
            ),
        )

    domain_add_list = []
    for domain in domains:
        domain_add_list.append(
            {
                "act_name": _("先添加新节点域名{}:{}").format(new_orphan_ip, domain),
                "act_component_code": MySQLDnsManageComponent.code,
                "kwargs": asdict(
                    CreateDnsKwargs(
                        bk_cloud_id=cluster.bk_cloud_id,
                        dns_op_exec_port=old_orphan_storage.port,
                        exec_ip=new_orphan_ip,
                        add_domain_name=domain,
                    )
                ),
            }
        )

    if len(domain_add_list) > 0:
        sub_pipeline.add_parallel_acts(acts_list=domain_add_list)

    sub_pipeline.add_act(
        act_name=_("再删除旧节点域名{}").format(old_orphan_ip),
        act_component_code=MySQLDnsManageComponent.code,
        kwargs=asdict(
            RecycleDnsRecordKwargs(
                dns_op_exec_port=old_orphan_storage.port,
                exec_ip=old_orphan_ip,
                bk_cloud_id=cluster.bk_cloud_id,
            )
        ),
    )

    if orphan_restore_type in [
        TendbSingleRestoreType.REPLICATE_WITH_STRUCT,
        TendbSingleRestoreType.REPLICATE_WITH_DATA,
    ]:
        # 目标实例断开同步
        sub_pipeline.add_act(
            act_name=_("目标实例断开同步{}").format(new_orphan),
            act_component_code=MySQLExecuteRdsComponent.code,
            kwargs=asdict(
                ExecuteRdsKwargs(
                    bk_cloud_id=cluster.bk_cloud_id,
                    instance_ip=new_orphan_ip,
                    instance_port=old_orphan_storage.port,
                    sqls=["stop slave", "reset slave all"],
                )
            ),
        )
    # todo 停止旧实例
    # if orphan_restore_type not in [
    #     TendbSingleRestoreType.RESTORE_WITH_STRUCT,
    #     TendbSingleRestoreType.RESTORE_WITH_DATA,
    # ]:
    # 设置恢复任务参数
    exec_act_kwargs = ExecActuatorKwargs(
        bk_cloud_id=cluster.bk_cloud_id,
        cluster_type=cluster.cluster_type,
    )
    stop_cluster = {"port": old_orphan_storage.port}
    exec_act_kwargs.cluster = copy.deepcopy(stop_cluster)
    exec_act_kwargs.exec_ip = old_orphan_storage.machine.ip
    exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.tendb_stop_remotedb_payload.__name__
    # 添加数据恢复任务
    sub_pipeline.add_act(
        act_name=_("停止旧实例 {}".format(old_orphan_storage.ip_port)),
        act_component_code=ExecuteDBActuatorScriptComponent.code,
        kwargs=asdict(exec_act_kwargs),
    )
    print("stop old orphan")
    return sub_pipeline.build_sub_process(
        sub_name=_("{}切换到新节点{}:{}".format(cluster.name, new_orphan_ip, old_orphan_storage.port))
    )
