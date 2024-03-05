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
from backend.flow.engine.bamboo.scene.mongodb.mongodb_backup import MongoBackupFlow
from backend.flow.engine.bamboo.scene.mongodb.mongodb_cluster_scale_mongos import ScaleMongoSFlow
from backend.flow.engine.bamboo.scene.mongodb.mongodb_deinstall import MongoDBDeInstallFlow
from backend.flow.engine.bamboo.scene.mongodb.mongodb_exec_script import MongoExecScriptFlow
from backend.flow.engine.bamboo.scene.mongodb.mongodb_fake_install import MongoFakeInstallFlow
from backend.flow.engine.bamboo.scene.mongodb.mongodb_install import MongoDBInstallFlow
from backend.flow.engine.bamboo.scene.mongodb.mongodb_instance_restart import MongoRestartInstanceFlow
from backend.flow.engine.bamboo.scene.mongodb.mongodb_remove_ns import MongoRemoveNsFlow
from backend.flow.engine.bamboo.scene.mongodb.mongodb_replace import MongoReplaceFlow
from backend.flow.engine.bamboo.scene.mongodb.mongodb_restore import MongoRestoreFlow
from backend.flow.engine.bamboo.scene.mongodb.mongodb_user import MongoUserFlow
from backend.flow.engine.controller.base import BaseController
from backend.ticket.constants import TicketType


class MongoDBController(BaseController):
    """
    名字服务相关控制器
    """

    def multi_replicaset_create(self):
        """
        安装复制集
        """

        flow = MongoDBInstallFlow(root_id=self.root_id, data=self.ticket_data)
        flow.multi_replicaset_install_flow()

    def cluster_create(self):
        """
        cluster安装
        """

        flow = MongoDBInstallFlow(root_id=self.root_id, data=self.ticket_data)
        flow.cluster_install_flow()

    def mongo_backup(self):
        """
        发起任务
        """
        # Get Ticket Name. 以后再拆到url那边. 临时用法.
        ticket_name = self.ticket_data["ticket_type"]
        if ticket_name == TicketType.MONGODB_RESTORE:
            flow = MongoRestoreFlow(root_id=self.root_id, data=self.ticket_data)
        elif ticket_name == TicketType.MONGODB_FULL_BACKUP or ticket_name == TicketType.MONGODB_BACKUP:
            flow = MongoBackupFlow(root_id=self.root_id, data=self.ticket_data)
        else:
            raise Exception("Unknown ticket name: %s" % ticket_name)

        flow.start()

    def fake_install(self):
        """
        在Meta中生成一个ReplicaSet，用于测试
        """
        flow = MongoFakeInstallFlow(root_id=self.root_id, data=self.ticket_data)
        flow.start()

    def create_user(self):
        """
        创建用户
        """

        flow = MongoUserFlow(root_id=self.root_id, data=self.ticket_data)
        flow.multi_cluster_user_flow(create=True)

    def delete_user(self):
        """
        删除用户
        """

        flow = MongoUserFlow(root_id=self.root_id, data=self.ticket_data)
        flow.multi_cluster_user_flow(create=False)

    def exec_script(self):
        """
        执行脚本
        """

        flow = MongoExecScriptFlow(root_id=self.root_id, data=self.ticket_data)
        flow.multi_cluster_exec_script_flow()

    def instance_restart(self):
        """
        实例重启
        """

        flow = MongoRestartInstanceFlow(root_id=self.root_id, data=self.ticket_data)
        flow.multi_instance_restart_flow()

    def mongo_remove_ns(self):
        """
        发起删除库表任务
        """
        MongoRemoveNsFlow(root_id=self.root_id, data=self.ticket_data).start()

    def machine_replace(self):
        """
        整机替换
        """

        flow = MongoReplaceFlow(root_id=self.root_id, data=self.ticket_data)
        flow.multi_host_replace_flow()

    def increase_mongos(self):
        """
        增加mongos
        """

        flow = ScaleMongoSFlow(root_id=self.root_id, data=self.ticket_data)
        flow.multi_cluster_mongos_flow(increase=True)

    def reduce_mongos(self):
        """
        减少mongos
        """

        flow = ScaleMongoSFlow(root_id=self.root_id, data=self.ticket_data)
        flow.multi_cluster_mongos_flow(increase=False)

    def deinstall_cluster(self):
        """
        下架集群
        """

        flow = MongoDBDeInstallFlow(root_id=self.root_id, data=self.ticket_data)
        flow.multi_cluster_deinstall_flow()
