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
from backend.flow.engine.bamboo.scene.mongodb.mongodb_autofix import MongoAutofixFlow
from backend.flow.engine.bamboo.scene.mongodb.mongodb_backup import MongoBackupFlow
from backend.flow.engine.bamboo.scene.mongodb.mongodb_cluster_scale_mongos import ScaleMongoSFlow
from backend.flow.engine.bamboo.scene.mongodb.mongodb_deinstall import MongoDBDeInstallFlow
from backend.flow.engine.bamboo.scene.mongodb.mongodb_enable_disable import MongoEnableDisableFlow
from backend.flow.engine.bamboo.scene.mongodb.mongodb_exec_script import MongoExecScriptFlow
from backend.flow.engine.bamboo.scene.mongodb.mongodb_fake_install import MongoFakeInstallFlow
from backend.flow.engine.bamboo.scene.mongodb.mongodb_install import MongoDBInstallFlow
from backend.flow.engine.bamboo.scene.mongodb.mongodb_install_dbmon import MongoInstallDBMonFlow
from backend.flow.engine.bamboo.scene.mongodb.mongodb_instance_deinstall import MongoInstanceDeInstallFlow
from backend.flow.engine.bamboo.scene.mongodb.mongodb_instance_restart import MongoRestartInstanceFlow
from backend.flow.engine.bamboo.scene.mongodb.mongodb_migrate import MongoDBMigrateMetaFlow
from backend.flow.engine.bamboo.scene.mongodb.mongodb_pitr_restore import MongoPitrRestoreFlow
from backend.flow.engine.bamboo.scene.mongodb.mongodb_remove_ns import MongoRemoveNsFlow
from backend.flow.engine.bamboo.scene.mongodb.mongodb_replace import MongoReplaceFlow
from backend.flow.engine.bamboo.scene.mongodb.mongodb_restore import MongoRestoreFlow
from backend.flow.engine.bamboo.scene.mongodb.mongodb_scale_node import MongoScaleNodeFlow
from backend.flow.engine.bamboo.scene.mongodb.mongodb_scale_storage import MongoScaleFlow
from backend.flow.engine.bamboo.scene.mongodb.mongodb_user import MongoUserFlow
from backend.flow.engine.controller.base import BaseController


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
        MongoBackupFlow(root_id=self.root_id, data=self.ticket_data).start()

    def mongo_restore(self):
        # 发起恢复任务
        MongoRestoreFlow(root_id=self.root_id, data=self.ticket_data).start()

    def mongo_pitr_restore(self):
        # 发起PITR恢复任务
        MongoPitrRestoreFlow(root_id=self.root_id, data=self.ticket_data).start()

    def install_dbmon(self):
        # 部署MongoDB bk-dbmon
        MongoInstallDBMonFlow(root_id=self.root_id, data=self.ticket_data).start()

    def mongo_remove_ns(self):
        """
        发起删除库表任务
        """
        MongoRemoveNsFlow(root_id=self.root_id, data=self.ticket_data).start()

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

    def scale_cluster(self):
        """
        集群容量变更
        """

        flow = MongoScaleFlow(root_id=self.root_id, data=self.ticket_data)
        flow.multi_cluster_scale_flow()

    def increase_node(self):
        """
        增加node数
        """

        flow = MongoScaleNodeFlow(root_id=self.root_id, data=self.ticket_data)
        flow.multi_cluster_scale_node_flow(increase=True)

    def reduce_node(self):
        """
        减少node数
        """

        flow = MongoScaleNodeFlow(root_id=self.root_id, data=self.ticket_data)
        flow.multi_cluster_scale_node_flow(increase=False)

    def enable_cluster(self):
        """
        启用cluster
        """

        flow = MongoEnableDisableFlow(root_id=self.root_id, data=self.ticket_data)
        flow.multi_cluster_flow(enable=True)

    def disable_cluster(self):
        """
        禁用cluster
        """

        flow = MongoEnableDisableFlow(root_id=self.root_id, data=self.ticket_data)
        flow.multi_cluster_flow(enable=False)

    def instance_deinstall(self):
        """
        instance卸载
        """

        flow = MongoInstanceDeInstallFlow(root_id=self.root_id, data=self.ticket_data)
        flow.multi_instance_deinstall_flow()

    def mongo_autofix(self):
        """
        mongodb自愈
        """

        flow = MongoAutofixFlow(root_id=self.root_id, data=self.ticket_data)
        flow.autofix()

    def migrate_meta(self):
        """
        迁移元数据
        """

        flow = MongoDBMigrateMetaFlow(root_id=self.root_id, data=self.ticket_data)
        flow.multi_cluster_migrate_flow()
