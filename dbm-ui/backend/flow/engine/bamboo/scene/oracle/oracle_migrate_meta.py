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
import logging.config
from typing import Dict, Optional

from django.utils.translation import gettext as _

from backend.flow.consts import DEPENDENCIES_PLUGINS
from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.plugins.components.collections.common.install_nodeman_plugin import (
    InstallNodemanPluginServiceComponent,
)
from backend.flow.plugins.components.collections.oracle.oracle_migrate_meta import OracleMigrateMetaComponent
from backend.flow.utils.oracle.oracle_migrate_meta_dataclass import MigrateActKwargs

logger = logging.getLogger("flow")


class OracleMigrateMetaFlow(object):
    """元数据迁移flow"""

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        传入参数
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递过来的参数列表，是dict格式
        """

        self.root_id = root_id
        self.data = data
        self.get_kwargs = MigrateActKwargs()
        self.get_kwargs.source_cluster_info = data
        self.get_kwargs.get_storages()
        self.get_kwargs.bk_biz_id = data.get("bk_biz_id")

    def cluster_migrate_flow(self):
        """
        cluster migrate流程
        """

        # 创建流程实例
        pipeline = Builder(root_id=self.root_id, data=self.data)

        # 检查 是否已经迁移 从目标环境检查迁移ip是否复用
        kwargs = self.get_kwargs.get_check_dest_cluster_info(
            cluster_name=self.get_kwargs.source_cluster_info.get("name")
        )
        pipeline.add_act(
            act_name=_("检查cluster目标端是否存在"), act_component_code=OracleMigrateMetaComponent.code, kwargs=kwargs
        )

        # 检查机器规格是否在目标端存在
        kwargs = self.get_kwargs.get_check_spec_info()
        pipeline.add_act(act_name=_("检查目标端机器规格"), act_component_code=OracleMigrateMetaComponent.code, kwargs=kwargs)

        # 目标业务更新dba 检查目标业务的dba，不一致则更新
        kwargs = self.get_kwargs.get_dba_info()
        pipeline.add_act(act_name=_("更新dba"), act_component_code=OracleMigrateMetaComponent.code, kwargs=kwargs)

        # 保存密码到密码服务  perfstat execute_user
        kwargs = self.get_kwargs.get_save_password_info()
        pipeline.add_act(act_name=_("保存密码"), act_component_code=OracleMigrateMetaComponent.code, kwargs=kwargs)

        # 迁移数据
        kwargs = self.get_kwargs.get_migrate_info()
        pipeline.add_act(
            act_name=_("迁移meta"),
            act_component_code=OracleMigrateMetaComponent.code,
            kwargs=kwargs,
        )

        # 修改dns的app字段
        kwargs = self.get_kwargs.get_change_dns_app_info()
        pipeline.add_act(act_name=_("更新dns的app"), act_component_code=OracleMigrateMetaComponent.code, kwargs=kwargs)

        # 安装蓝鲸插件
        acts_list = []
        for plugin_name in DEPENDENCIES_PLUGINS:
            acts_list.append(
                {
                    "act_name": _("安装[{}]插件".format(plugin_name)),
                    "act_component_code": InstallNodemanPluginServiceComponent.code,
                    "kwargs": self.get_kwargs.get_install_plugin_info(plugin_name=plugin_name),
                }
            )
        pipeline.add_parallel_acts(acts_list=acts_list)

        # 运行流程
        pipeline.run_pipeline()
