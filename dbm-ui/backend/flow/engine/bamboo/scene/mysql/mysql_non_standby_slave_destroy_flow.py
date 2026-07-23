# -*- coding: utf-8 -*-
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
from typing import Dict, Optional

from django.utils.translation import gettext as _

from backend.configuration.constants import DBType
from backend.db_meta.exceptions import DBMetaException
from backend.db_meta.models import Cluster, StorageInstance
from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.mysql.common.uninstall_instance import uninstall_instance_sub_flow
from backend.flow.plugins.components.collections.mysql.clear_machine import MySQLClearMachineComponent
from backend.flow.plugins.components.collections.mysql.mysql_db_meta import MySQLDBMetaComponent
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.utils.mysql.common.mysql_cluster_info import get_ports
from backend.flow.utils.mysql.mysql_act_dataclass import ClearMachineKwargs, DBMetaOPKwargs, DownloadMediaKwargs
from backend.flow.utils.mysql.mysql_db_meta import MySQLDBMeta


class DestroyNonStanbySlaveMySQLFlow(object):
    """
    下架非standby slave MySQL实例的流程
    """

    def __init__(self, root_id: str, ticket_data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param ticket_data : 单据传递过来的参数列表，是dict格式
        """
        self.root_id = root_id
        self.ticket_data = ticket_data
        if not self.ticket_data.get("force"):
            self.ticket_data["force"] = False

    def destroy(self):
        """
        {
            "uid": "2022051612120001",
            "created_by": "xxxx",
            "bk_biz_id": "152",
            "ticket_type": "MYSQL_RESTORE_SLAVE",
            "infos": {
                    "cluster_ids": [1001,1002],
                    "slave_ip": "127.0.0.1",
            }
        }
        """
        cluster_ids = self.ticket_data["infos"]["cluster_ids"]
        slave_ip = self.ticket_data["infos"]["slave_ip"]
        cluster_class = Cluster.objects.get(id=cluster_ids[0])
        ports = get_ports(cluster_ids)
        slave_ins_list = StorageInstance.objects.filter(machine__ip=slave_ip)

        for slave_ins in slave_ins_list:
            if slave_ins.is_stand_by:
                raise DBMetaException(message=_("{}:{}实例是standby slave,请确认").format(slave_ip, slave_ins.port))

        p = Builder(
            root_id=self.root_id,
            data=copy.deepcopy(self.ticket_data),
            need_random_pass_cluster_ids=list(set(cluster_ids)),
        )

        p.add_act(
            act_name=_("卸载实例前先删除元数据"),
            act_component_code=MySQLDBMetaComponent.code,
            kwargs=asdict(
                DBMetaOPKwargs(
                    db_meta_class_func=MySQLDBMeta.ro_slave_recover_del_instance.__name__,
                    cluster={"uninstall_ip": slave_ip, "cluster_ids": cluster_ids},
                )
            ),
        )

        p.add_act(
            act_name=_("下发db-actor到节点{}").format(slave_ip),
            act_component_code=TransFileComponent.code,
            kwargs=asdict(
                DownloadMediaKwargs(
                    bk_cloud_id=cluster_class.bk_cloud_id,
                    exec_ip=slave_ip,
                    file_list=GetFileList(db_type=DBType.MySQL).get_db_actuator_package(),
                )
            ),
        )

        p.add_act(
            act_name=_("清理机器配置"),
            act_component_code=MySQLClearMachineComponent.code,
            kwargs=asdict(
                ClearMachineKwargs(
                    exec_ip=slave_ip,
                    bk_cloud_id=cluster_class.bk_cloud_id,
                )
            ),
        )

        p.add_sub_pipeline(
            sub_flow=uninstall_instance_sub_flow(
                root_id=self.root_id,
                ticket_data=copy.deepcopy(self.ticket_data),
                ip=slave_ip,
                ports=ports,
            )
        )
        p.run_pipeline(is_drop_random_user=False)
