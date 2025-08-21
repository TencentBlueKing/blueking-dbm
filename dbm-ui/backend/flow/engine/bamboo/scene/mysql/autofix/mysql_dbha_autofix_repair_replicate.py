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
import logging
from typing import Dict, Optional

from django.utils.translation import ugettext as _

from backend.db_meta.enums import ClusterType, InstanceInnerRole, InstanceRole, MachineType
from backend.db_meta.models import StorageInstance, StorageInstanceTuple
from backend.db_monitor.models import MySQLDBHAAutofixTodo
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.plugins.components.collections.mysql.autofix.mysql_dbha_autofix_change_master import (
    MySQLDBHAAutofixChangeMasterComponent,
)
from backend.flow.plugins.components.collections.mysql.autofix.mysql_dbha_autofix_check_replicate import (
    MySQLDBHAAutofixCheckReplicateComponent,
)

logger = logging.getLogger("root")


class MySQLDBHAAutofixRepairReplicateFlow(object):
    def __init__(self, root_id: str, data: Optional[Dict]):
        self.root_id = root_id
        self.data = data

    def repair_slave_replicate(self):
        """
        self.data = {
            "check_id": int
        }
        流程分2个部分
        1. 集中的数据检查
        2. 按实例并发的 change master

        数据检查做成构造 flow 的代码, 省得被意外跳过. 数据有问题单都提不了
        change master 这个必须每个实例都是独立的节点, 这样才能幂等重试
        """
        check_id = self.data["check_id"]
        records = MySQLDBHAAutofixTodo.objects.filter(check_id=check_id)
        if not records.exists():
            raise  # ToDo

        repair_subpipes = []
        for record in records:
            if record.cluster_type not in [ClusterType.TenDBHA, ClusterType.TenDBCluster]:
                raise  # ToDo
            if record.machine_type not in [MachineType.BACKEND, MachineType.REMOTE]:
                raise  # ToDo
            if record.instance_role not in [InstanceRole.BACKEND_MASTER, InstanceRole.REMOTE_MASTER]:
                raise  # Todo
            if not record.new_master_log_file.strip() or not record.new_master_log_pos > 0:
                raise  # Todo

            this_instance = StorageInstance.objects.get(
                machine__ip=record.ip,
                port=record.port,
                cluster_type=record.cluster_type,
                instance_inner_role=InstanceInnerRole.SLAVE,
                instance_role__in=[InstanceRole.BACKEND_SLAVE, InstanceRole.REMOTE_SLAVE],
            )
            new_master_instance = StorageInstance.objects.get(
                machine__ip=record.new_master_host,
                port=record.new_master_port,
                cluster_type=record.cluster_type,
                instance_inner_role=InstanceInnerRole.MASTER,
                instance_role__in=[InstanceRole.BACKEND_MASTER, InstanceRole.REMOTE_MASTER],
            )
            # Todo 如果开了 GTID 就退出
            StorageInstanceTuple.objects.get(
                ejector=new_master_instance, receiver=this_instance
            )  # 查不到说明切换有点问题, raise 出去. 这个是 dbha 保证做到的

            # 集群切换前, 所有 readonly slaves 都是 故障实例 this_instance 的 receiver
            # dbha 也不会处理这部分数据
            # filter 里的 exclude 其实有点多余
            for readonly_tuple in StorageInstanceTuple.objects.filter(
                ejector=this_instance, receiver__is_stand_by=False
            ).exclude(receiver=new_master_instance):
                readonly_slave_instance = readonly_tuple.receiver
                # Todo 如果开了 GTID 就退出

                repair_subpipe = SubBuilder(root_id=self.root_id, data=self.data)
                repair_subpipe.add_act(
                    act_name=_(f"{readonly_slave_instance.ip_port}"),
                    act_component_code=MySQLDBHAAutofixChangeMasterComponent.code,
                    kwargs={
                        "bk_cloud_id": record.bk_cloud_id,
                        "readonly_slave_ip": readonly_slave_instance.machine.ip,
                        "readonly_slave_port": readonly_slave_instance.port,
                        "old_master_host": record.ip,
                        "old_master_port": record.port,
                        "new_master_host": record.new_master_host,
                        "new_master_port": record.new_master_port,
                        "new_master_log_file": record.new_master_log_file,
                        "new_master_log_pos": record.new_master_log_pos,
                    },
                )

                repair_subpipe.add_act(
                    act_name=_("同步状态检查"),
                    act_component_code=MySQLDBHAAutofixCheckReplicateComponent.code,
                    kwargs={
                        "bk_cloud_id": record.bk_cloud_id,
                        "address": readonly_slave_instance.ip_port,
                        "master_host": f"{record.new_master_host}",
                        "master_port": f"{record.new_master_port}",
                    },
                )
                repair_subpipes.append(repair_subpipe.build_sub_process(sub_name=""))

        repair_pipe = Builder(root_id=self.root_id, data=self.data)
        repair_pipe.add_parallel_sub_pipeline(sub_flow_list=repair_subpipes)
        logger.info(_("构造修复readonly slave同步状态流程成功"))
        repair_pipe.run_pipeline()
