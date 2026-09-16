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
from typing import List

from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component

from backend.db_meta.models import Cluster
from backend.db_proxy.constants import ExtensionType
from backend.db_proxy.models import DBExtension
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.base.validate_handler import ValidateHandler, validate_ip_in_list, validate_string
from backend.flow.utils.sqlserver.sqlserver_act_dataclass import NginxInfo
from backend.flow.utils.sqlserver.sqlserver_db_function import init_dbm_nginx_proxy_config

logger = logging.getLogger("flow")


@dataclass()
class InitDBMNginxForSQLServerKwargs(ValidateHandler):
    """
    定义SQLServer 集群初始化 DBM Nginx 代理配置服务的私有参数

    :attribute cluster_domain: 集群主域名（不可变域名），必填
    :attribute exclude_ips: 需要在本次初始化中排除的机器 IP 列表；
                            匹配到的存储实例（同 IP 的全部端口实例）都不再下发 Nginx 配置。
                            典型使用场景：机器已下架 / 已隔离 / 待剔除；
                            允许为空列表（默认），表示不排除任何实例。
    """

    # 集群主域名（一个集群唯一对应一个主域名）
    cluster_domain: str = field(metadata={"validate": validate_string})

    # 需要排除的机器 IP 列表；默认空，向后兼容；is_allow_null=True 允许列表为空
    exclude_ips: List[str] = field(
        default_factory=list,
        metadata={"validate": lambda v: validate_ip_in_list(v, is_allow_null=True)},
    )


class InitDBMNginxForSQLServerService(BaseService):
    """
    SQLServer 集群初始化 DBM Nginx 代理配置服务

    该服务节点用于在 SQLServer 集群的所有存储实例上初始化 Nginx 代理信息，
    将集群所在云区域的 Nginx 节点的 IP 和端口写入到各实例的系统库中，
    以便实例后续可以通过 Nginx 代理与 DBM 平台进行通信。

    支持通过 kwargs.exclude_ips 传入待排除的机器 IP 列表，跳过对应实例的下发。
    """

    def _execute(self, data, parent_data) -> bool:
        """
        执行 Nginx 代理配置初始化

        执行流程：
        1. 根据集群域名获取集群信息
        2. 查询集群所在云区域的 Nginx 节点列表
        3. 收集集群所有存储实例，剔除 kwargs.exclude_ips 命中的机器（按 IP 精确匹配）
        4. 将 Nginx 节点信息写入剩余存储实例

        @param data: 流程节点数据，kwargs 需包含 cluster_domain（集群主域名），
                     可选包含 exclude_ips（待排除的机器 IP 列表）
        @param parent_data: 父流程数据
        @return: 执行成功返回 True
        @raises Exception: 当集群所在云区域没有可用的 Nginx 节点时抛出异常；
                           当剔除 exclude_ips 后没有任何存活实例时抛出异常
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

        # 待排除 IP 列表：用 set 加速命中判断；缺省为空列表则不排除任何实例
        exclude_ip_set: set = set(kwargs.get("exclude_ips") or [])

        # 收集目标实例（ip:port 形式）：
        #   - 数据源：cluster.storageinstance_set 全量存储实例
        #   - 过滤规则：若实例的机器 IP 命中 exclude_ip_set，则整台机器上所有实例均剔除
        #   - 语义：exclude_ips 表示"按机器维度"排除，而非"按 ip:port 维度"
        target_instances: List[str] = [
            s.ip_port for s in cluster.storageinstance_set.all() if s.machine.ip not in exclude_ip_set
        ]

        # 保险起见：若 exclude_ips 把所有实例都过滤空了，直接抛错，避免"静默无下发"
        if not target_instances:
            raise Exception(
                _("集群[{domain}]在剔除exclude_ips={excluded}后无任何可下发实例，请检查参数").format(
                    domain=kwargs["cluster_domain"], excluded=sorted(exclude_ip_set)
                )
            )

        # 通过 DRS 远程调用，将 Nginx 代理信息写入过滤后的存储实例的系统库
        init_dbm_nginx_proxy_config(
            nginx_list=init_nginx_list,
            bk_cloud_id=cluster.bk_cloud_id,
            target_instances=target_instances,
        )
        return True


class InitDBMNginxForSQLServerComponent(Component):
    """SQLServer 初始化 DBM Nginx 代理配置的 Pipeline 组件"""

    name = __name__
    code = "sqlserver_init_dbm_nginx_proxy"
    bound_service = InitDBMNginxForSQLServerService
    kwargs = InitDBMNginxForSQLServerKwargs
