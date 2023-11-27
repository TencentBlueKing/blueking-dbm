"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from dataclasses import asdict

from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.enums import InstanceStatus
from backend.db_meta.models import Cluster, ClusterEntry
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.mysql.common.common_sub_flow import check_sub_flow
from backend.flow.plugins.components.collections.mysql.clone_user import CloneUserComponent
from backend.flow.plugins.components.collections.mysql.dns_manage import MySQLDnsManageComponent
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.utils.mysql.mysql_act_dataclass import (
    CreateDnsKwargs,
    DownloadMediaKwargs,
    InstanceUserCloneKwargs,
    RecycleDnsRecordKwargs,
)

"""
tendb ha 从库恢复切换
"""


def slave_migrate_switch_sub_flow(
    root_id: str,
    ticket_data: dict,
    cluster: Cluster,
    old_slave_ip: str,
    new_slave_ip: str,
):
    """"""
    # 默认预检测连接情况、同步延时、checksum校验结果
    domain = ClusterEntry.get_cluster_entry_map_by_cluster_ids([cluster.id])
    master = cluster.main_storage_instances()[0]
    old_slave = ("{}{}{}".format(old_slave_ip, IP_PORT_DIVIDER, master.port),)
    new_slave = ("{}{}{}".format(new_slave_ip, IP_PORT_DIVIDER, master.port),)
    old_master = ("{}{}{}".format(master.machine.ip, IP_PORT_DIVIDER, master.port),)
    # cluster["master_domain"] = domain[cluster.id]["master_domain"]
    # cluster["slave_domain"] = domain[cluster.id]["slave_domain"]

    sub_pipeline = SubBuilder(root_id=root_id, data=ticket_data)
    sub_pipeline.add_act(
        act_name=_("下发db-actuator介质"),
        act_component_code=TransFileComponent.code,
        kwargs=asdict(
            DownloadMediaKwargs(
                bk_cloud_id=cluster.bk_cloud_id,
                exec_ip=[master.machine.ip, new_slave_ip],
                file_list=GetFileList(db_type=DBType.MySQL).get_db_actuator_package(),
            )
        ),
    )

    # 切换前做预检测
    verify_checksum_tuples = []
    # for m in migrate_tuples:
    # old_master-> new_master ; new_master -> new_slave 都需要检测checksum结果
    verify_checksum_tuples.append({"master": old_master, "slave": new_slave})
    sub_pipeline.add_sub_pipeline(
        sub_flow=check_sub_flow(
            uid=ticket_data["uid"],
            root_id=root_id,
            cluster=cluster,
            is_check_client_conn=True,
            is_verify_checksum=True,
            check_client_conn_inst=["{}:{}".format(new_slave_ip, master.port)],
            verify_checksum_tuples=verify_checksum_tuples,
        )
    )

    clone_data = []
    clone_data.append(
        {
            "source": old_master,
            "target": new_slave,
            # "machine_type": MachineType.REMOTE.value,
            "bk_cloud_id": cluster.bk_cloud_id,
        }
    )
    slaveStorage = cluster.storageinstance_set.filter(status=InstanceStatus.RUNNING.value, machine__ip=old_slave_ip)
    if slaveStorage:
        clone_data.append(
            {
                "source": old_slave,
                "target": new_slave,
                # "machine_type": MachineType.REMOTE.value,
                "bk_cloud_id": cluster.bk_cloud_id,
            }
        )

    sub_pipeline.add_act(
        act_name=_("克隆权限"),
        act_component_code=CloneUserComponent.code,
        kwargs=asdict(InstanceUserCloneKwargs(clone_data=clone_data)),
    )

    sub_pipeline.add_act(
        act_name=_("先添加新从库域名{}").format(new_slave_ip),
        act_component_code=MySQLDnsManageComponent.code,
        kwargs=asdict(
            CreateDnsKwargs(
                bk_cloud_id=cluster.bk_cloud_id,
                dns_op_exec_port=master.port,
                exec_ip=new_slave_ip,
                add_domain_name=domain[cluster.id]["slave_domain"],
            )
        ),
    )

    sub_pipeline.add_act(
        act_name=_("再删除旧从库域名{}").format(new_slave_ip),
        act_component_code=MySQLDnsManageComponent.code,
        kwargs=asdict(
            RecycleDnsRecordKwargs(
                dns_op_exec_port=master.port,
                exec_ip=old_slave_ip,
                bk_cloud_id=cluster.bk_cloud_id,
            )
        ),
    )
    return sub_pipeline.build_sub_process(sub_name=_("[{}]成对切换".format(cluster.name)))
