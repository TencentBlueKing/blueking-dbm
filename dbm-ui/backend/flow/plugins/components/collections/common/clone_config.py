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

from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component

from backend.components import DBConfigApi
from backend.flow.plugins.components.collections.common.base_service import BaseService

logger = logging.getLogger("flow")


class CloneModuleConfigService(BaseService):
    """
    克隆模块配置服务

    功能说明：
    用于在数据库模块升级场景中，将源模块的配置克隆到目标模块。
    主要用于spider节点升级时，将旧模块的配置项复制到新模块，确保配置的一致性。

    使用场景：
    - spider节点升级时，模块ID发生变化，需要将旧模块的配置克隆到新模块
    - 配置类型通常为 "dbconf"，命名空间为集群类型（如 "tendbcluster"）

    参数说明：
    - source_module_id: 源模块ID（旧模块）
    - target_module_id: 目标模块ID（新模块）
    - source_bk_biz_id: 源业务ID
    - target_bk_biz_id: 目标业务ID
    - source_conf_file: 源配置文件名称（如 "MySQL-5.7"）
    - target_conf_file: 目标配置文件名称（如 "MySQL-5.8"）
    - conf_type: 配置类型，默认为 "dbconf"
    - namespace: 命名空间，通常为集群类型（如 "tendbcluster"）
    """

    def _execute(self, data, parent_data) -> bool:
        """
        执行克隆模块配置操作

        Args:
            data: 流程节点输入数据
            parent_data: 父流程数据

        Returns:
            bool: 执行结果，True表示成功，False表示失败
        """
        kwargs = data.get_one_of_inputs("kwargs")

        # 获取参数
        source_module_id = kwargs.get("source_module_id")
        target_module_id = kwargs.get("target_module_id")
        source_bk_biz_id = kwargs.get("source_bk_biz_id")
        target_bk_biz_id = kwargs.get("target_bk_biz_id")
        source_conf_file = kwargs.get("source_conf_file")
        target_conf_file = kwargs.get("target_conf_file")
        conf_type = kwargs.get("conf_type", "dbconf")
        namespace = kwargs.get("namespace")

        try:
            # 调用克隆模块配置API
            # 将源模块的配置项复制到目标模块，保持配置的一致性
            result = DBConfigApi.clone_module_config(
                {
                    "source_module_id": str(source_module_id),
                    "target_module_id": str(target_module_id),
                    "source_bk_biz_id": str(source_bk_biz_id),
                    "target_bk_biz_id": str(target_bk_biz_id),
                    "source_conf_file": source_conf_file,
                    "target_conf_file": target_conf_file,
                    "conf_type": conf_type,
                    "namespace": namespace,
                }
            )

            self.log_info(_("克隆模块配置成功: {}").format(result))
            return True

        except Exception as e:
            self.log_error(_("克隆模块配置失败: {}").format(str(e)))
            return False


class CloneModuleConfigComponent(Component):
    """
    克隆模块配置组件

    组件代码: clone_module_config
    用于在流程中调用克隆模块配置服务
    """

    name = _("克隆模块配置")
    code = "clone_module_config"
    bound_service = CloneModuleConfigService


class CloneClusterConfigService(BaseService):
    """
    克隆集群配置服务

    功能说明：
    用于在数据库模块升级场景中，将源模块的集群配置克隆到目标模块。
    与克隆模块配置的区别在于，此服务还会克隆集群级别的配置项。

    使用场景：
    - spider节点升级时，模块ID发生变化，需要将旧模块的集群配置克隆到新模块
    - 配置类型通常为 "dbconf"，命名空间为集群类型（如 "tendbcluster"）

    参数说明：
    - source_module_id: 源模块ID（旧模块）
    - target_module_id: 目标模块ID（新模块）
    - source_bk_biz_id: 源业务ID
    - target_bk_biz_id: 目标业务ID
    - source_conf_file: 源配置文件名称（如 "MySQL-5.7"）
    - target_conf_file: 目标配置文件名称（如 "MySQL-5.8"）
    - conf_type: 配置类型，默认为 "dbconf"
    - namespace: 命名空间，通常为集群类型（如 "tendbcluster"）
    - cluster_domains: 集群域名列表，用于指定需要克隆配置的集群
    """

    def _execute(self, data, parent_data) -> bool:
        """
        执行克隆集群配置操作

        Args:
            data: 流程节点输入数据
            parent_data: 父流程数据

        Returns:
            bool: 执行结果，True表示成功，False表示失败
        """
        kwargs = data.get_one_of_inputs("kwargs")

        # 获取参数
        source_module_id = kwargs.get("source_module_id")
        target_module_id = kwargs.get("target_module_id")
        source_bk_biz_id = kwargs.get("source_bk_biz_id")
        target_bk_biz_id = kwargs.get("target_bk_biz_id")
        source_conf_file = kwargs.get("source_conf_file")
        target_conf_file = kwargs.get("target_conf_file")
        conf_type = kwargs.get("conf_type", "dbconf")
        namespace = kwargs.get("namespace")
        cluster_domains = kwargs.get("cluster_domains", [])

        try:
            # 调用克隆集群配置API
            # 将源模块的模块级配置和集群级配置都复制到目标模块
            result = DBConfigApi.clone_cluster_config(
                {
                    "source_module_id": str(source_module_id),
                    "target_module_id": str(target_module_id),
                    "source_bk_biz_id": str(source_bk_biz_id),
                    "target_bk_biz_id": str(target_bk_biz_id),
                    "source_conf_file": source_conf_file,
                    "target_conf_file": target_conf_file,
                    "conf_type": conf_type,
                    "namespace": namespace,
                    "cluster_domains": cluster_domains,
                }
            )

            self.log_info(_("克隆集群配置成功: {}").format(result))
            return True

        except Exception as e:
            self.log_error(_("克隆集群配置失败: {}").format(str(e)))
            return False


class CloneClusterConfigComponent(Component):
    """
    克隆集群配置组件

    组件代码: clone_cluster_config
    用于在流程中调用克隆集群配置服务
    """

    name = _("克隆集群配置")
    code = "clone_cluster_config"
    bound_service = CloneClusterConfigService
