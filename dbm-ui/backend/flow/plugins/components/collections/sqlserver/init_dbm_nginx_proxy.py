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
from dataclasses import dataclass, field

from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component

from backend.db_meta.models import Cluster
from backend.db_proxy.constants import ExtensionType
from backend.db_proxy.models import DBExtension
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.base.validate_handler import ValidateHandler, validate_string
from backend.flow.utils.sqlserver.sqlserver_act_dataclass import NginxInfo
from backend.flow.utils.sqlserver.sqlserver_db_function import init_dbm_nginx_proxy_config

logger = logging.getLogger("flow")


@dataclass()
class InitDBMNginxForSQLServerKwargs(ValidateHandler):
    """
    定义SQLServer 集群初始化 DBM Nginx 代理配置服务的私有参数
    """

    cluster_domain: str = field(metadata={"validate": validate_string})  # 主域名信息


class InitDBMNginxForSQLServerService(BaseService):
    """
    SQLServer 集群初始化 DBM Nginx 代理配置服务

    该服务节点用于在 SQLServer 集群的所有存储实例上初始化 Nginx 代理信息，
    将集群所在云区域的 Nginx 节点的 IP 和端口写入到各实例的系统库中，
    以便实例后续可以通过 Nginx 代理与 DBM 平台进行通信。
    """

    def _execute(self, data, parent_data) -> bool:
        """
        执行 Nginx 代理配置初始化

        执行流程：
        1. 根据集群域名获取集群信息
        2. 查询集群所在云区域的 Nginx 节点列表
        3. 将 Nginx 节点信息写入集群所有存储实例

        @param data: 流程节点数据，kwargs 中需包含 cluster_domain（集群主域名）
        @param parent_data: 父流程数据
        @return: 执行成功返回 True
        @raises Exception: 当集群所在云区域没有可用的 Nginx 节点时抛出异常
        """
        kwargs = data.get_one_of_inputs("kwargs")

        # 通过集群主域名获取集群对象（一个集群对应一个唯一的主域名）
        cluster = Cluster.objects.get(immute_domain=kwargs["cluster_domain"])

        # 查询集群所在云区域下的所有 Nginx 扩展节点
        nginx_list = DBExtension.get_extension_in_cloud(
            bk_cloud_id=cluster.bk_cloud_id, extension_type=ExtensionType.NGINX
        )
        if not nginx_list:
            raise Exception(_("没有查询到该云区域的Nginx节点信息，请联系DBM系统管理员"))

        # 将查询结果转换为 NginxInfo 数据对象列表
        init_nginx_list = [
            NginxInfo(
                bk_cloud_id=cluster.bk_cloud_id, nginx_proxy_ip=i.details["ip"], nginx_proxy_port=i.details["dbm_port"]
            )
            for i in nginx_list
        ]

        # 通过 DRS 远程调用，将 Nginx 代理信息写入集群所有存储实例的系统库
        init_dbm_nginx_proxy_config(
            nginx_list=init_nginx_list,
            bk_cloud_id=cluster.bk_cloud_id,
            target_instances=[s.ip_port for s in cluster.storageinstance_set.all()],
        )
        return True


class InitDBMNginxForSQLServerComponent(Component):
    """SQLServer 初始化 DBM Nginx 代理配置的 Pipeline 组件"""

    name = __name__
    code = "sqlserver_init_dbm_nginx_proxy"
    bound_service = InitDBMNginxForSQLServerService
    kwargs = InitDBMNginxForSQLServerKwargs
