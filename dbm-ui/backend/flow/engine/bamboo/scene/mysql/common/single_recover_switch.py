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
from backend.db_meta.models import Cluster
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
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


def single_migrate_switch_sub_flow(
    root_id: str, ticket_data: dict, cluster: Cluster, old_orphan_ip: str, new_orphan_ip: str, domains: list
):
    """"""
    # 默认预检测连接情况、同步延时、checksum校验结果
    old_orphan_storage = cluster.storageinstance_set.get(
        machine__ip=old_orphan_ip, machine__bk_cloud_id=cluster.bk_cloud_id
    )
    old_orphan = "{}{}{}".format(old_orphan_ip, IP_PORT_DIVIDER, old_orphan_storage.port)
    new_orphan = "{}{}{}".format(new_orphan_ip, IP_PORT_DIVIDER, old_orphan_storage.port)

    sub_pipeline = SubBuilder(root_id=root_id, data=ticket_data)

    if old_orphan_storage.status == InstanceStatus.RUNNING.value:
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

        sub_pipeline.add_act(
            act_name=_("克隆权限"),
            act_component_code=CloneUserComponent.code,
            kwargs=asdict(InstanceUserCloneKwargs(clone_data=clone_data)),
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
    return sub_pipeline.build_sub_process(
        sub_name=_("{}切换到新节点{}:{}".format(cluster.name, new_orphan_ip, old_orphan_storage.port))
    )
