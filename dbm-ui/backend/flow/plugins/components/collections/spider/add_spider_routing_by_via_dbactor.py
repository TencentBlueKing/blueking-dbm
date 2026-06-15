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

from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.models import Cluster
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptService

logger = logging.getLogger("flow")


class AddSpiderRoutingByViaDbactorService(ExecuteDBActuatorScriptService):
    """
    通过 db-actuator 子命令 `spider-ctl add-spider-routing` 给已有 TenDB Cluster 集群
    添加 spider 节点路由的活动节点。

    设计动机：
        db-actuator 子命令 `spider-ctl add-spider-routing` 内置 `tc_is_primary` PreCheck，
        要求 exec_ip 必须是当前集群中控 (tdb-ctl) 的真实 primary。然而上层子流程在编排
        时往往是一次性算好 ctl_primary 并写入 ExecActuatorKwargs.exec_ip / component_kwargs；
        如果在该 act 真正执行前发生中控切换 (TDBCTL ENABLE/DISABLE PRIMARY 等)，编排
        阶段算好的 primary 就会与运行时真实 primary 不一致，导致 db-actuator 子命令失败。

    本节点继承自 ExecuteDBActuatorScriptService，覆写 _execute：
        1. 通过 kwargs["component_kwargs"]["cluster_id"] 取出 Cluster 元数据；
        2. 调用 cluster.tendbcluster_ctl_primary_address() 实时探测最新 ctl primary；
        3. 与上层缓存的 (kwargs["exec_ip"], kwargs["component_kwargs"]["ctl_primary_port"]) 对比；
        4. 若不一致，则用最新 primary 的 ip / port 改写 kwargs：
              - kwargs["exec_ip"]                                  = latest_ip
              - kwargs["component_kwargs"]["ctl_primary_port"]     = latest_port
           保证父类基于刷新后的 kwargs 在真实 primary 上拼装并执行 db-actuator；
        5. 调用 super()._execute(data, parent_data) 走原有 db-actuator 执行链路。

    使用约定 (component_kwargs 必填):
        cluster_id:        集群 id, 用于实时探测 ctl primary
        ctl_primary_port:  上层缓存的中控 primary 端口 (运行时会被刷新)
        add_port:          被加入节点的端口 (spider.port 或 spider.admin_port)
        add_spiders:       待加入的 spider 节点列表
        add_spider_role:   被加入节点的 spider 角色
        spider_pwd:        spider 内置账号密码

    注意：
        - kwargs["exec_ip"] 由调用方按"上层缓存 primary"传入；本节点会按需覆盖。
        - get_mysql_payload_func 必须设为 MysqlActPayload.get_add_spider_routing_payload 的方法名,
          payload 拼装时基于 ip=exec_ips[0] (即刷新后的最新 primary) 与 component_kwargs 完成。
    """

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        component_kwargs = kwargs.get("component_kwargs") or {}

        cluster_id = component_kwargs.get("cluster_id")
        if not cluster_id:
            self.log_error(_("component_kwargs 缺少 cluster_id, 无法探测最新 ctl primary"))
            return False

        cluster = Cluster.objects.get(id=cluster_id)

        # 上层编排时缓存的 ctl primary
        cached_ip = kwargs.get("exec_ip")
        cached_port = component_kwargs.get("ctl_primary_port")
        cached_primary = f"{cached_ip}{IP_PORT_DIVIDER}{cached_port}"

        # 运行时实时探测最新 ctl primary
        latest_primary = cluster.tendbcluster_ctl_primary_address()
        self.log_info(
            _("[{}] 上层缓存的 ctl primary 为: {}, 实时探测的 ctl primary 为: {}").format(
                cluster.immute_domain, cached_primary, latest_primary
            )
        )

        if cached_primary != latest_primary:
            latest_ip, latest_port_str = latest_primary.split(IP_PORT_DIVIDER)
            latest_port = int(latest_port_str)
            self.log_warning(
                _("[{}] ctl primary 已发生漂移, 改用最新 primary 执行 db-actuator: {} -> {}").format(
                    cluster.immute_domain, cached_primary, latest_primary
                )
            )

            # 改写 kwargs:
            #   1) exec_ip 改为最新 primary ip, 让 db-actuator 在新 primary 上执行;
            #   2) component_kwargs.ctl_primary_port 改为最新 primary port, 让 payload
            #      的 extend.host/port 与 read_ctl_pass_from_ctl_primary 都指向最新 primary。
            kwargs["exec_ip"] = latest_ip
            component_kwargs["ctl_primary_port"] = latest_port
            kwargs["component_kwargs"] = component_kwargs

            # 写回 data, 兼容部分 pipeline 实现下 get_one_of_inputs 返回的不是同一引用的情况
            data.get_one_of_inputs("kwargs")["exec_ip"] = latest_ip
            data.get_one_of_inputs("kwargs")["component_kwargs"] = component_kwargs
        else:
            self.log_info(_("[{}] ctl primary 未发生漂移, 沿用上层编排时的 primary").format(cluster.immute_domain))

        # 走父类原有 db-actuator 执行链路
        return super()._execute(data, parent_data)


class AddSpiderRoutingByViaDbactorComponent(Component):
    """
    Pipeline 组件注册类: 将 AddSpiderRoutingByViaDbactorService 注册为可在流程编排
    中使用的组件, 用于在执行 db-actuator `spider-ctl add-spider-routing` 之前刷新
    ctl primary, 规避中控切换导致 PreCheck 失败的问题。
    """

    name = __name__
    code = "spider_add_routing_by_via_db_actuator"
    bound_service = AddSpiderRoutingByViaDbactorService
