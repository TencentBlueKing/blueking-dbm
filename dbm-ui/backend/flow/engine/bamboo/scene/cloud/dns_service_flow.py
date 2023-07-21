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
from dataclasses import asdict
from itertools import groupby
from typing import Dict, List, Union

from bamboo_engine.builder import SubProcess
from django.utils.translation import ugettext as _

from backend.db_proxy.constants import MachineOsType
from backend.db_proxy.models import DnsManage
from backend.db_services.ipchooser.handlers.host_handler import HostHandler
from backend.flow.engine.bamboo.scene.cloud.base_service_flow import CloudBaseServiceFlow
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.plugins.components.collections.cloud.exec_service_script import ExecCloudScriptComponent
from backend.flow.plugins.components.collections.common.pause import PauseComponent
from backend.flow.utils.cloud.cloud_act_payload import CloudServiceActPayload
from backend.flow.utils.cloud.cloud_context_dataclass import CloudDNSFlushActKwargs, CloudServiceActKwargs
from backend.flow.utils.cloud.cloud_db_proxy import CloudDBProxy
from backend.flow.utils.cloud.script_template import (
    dns_flush_linux_template,
    dns_flush_windows_template,
    stop_dns_server_template,
)

logger = logging.getLogger("flow")


class CloudDNSServiceFlow(CloudBaseServiceFlow):
    """云区域部署dns服务流程"""

    OS_TYPE__FLUSH_TEMPLATES = {
        MachineOsType.Windows.value: dns_flush_windows_template,
        MachineOsType.Linux.value: dns_flush_linux_template,
    }

    def _get_inventory_hosts(self, dns_ids):
        """根据操作系统类型聚合代刷新dns的主机信息"""

        # 获取dns纳管的主机
        hosts = list(DnsManage.objects.filter(dns__id__in=dns_ids).values_list("ip", "bk_host_id", "bk_cloud_id"))
        # 包含drs的机器信息
        hosts.extend(self.data["drs"]["host_infos"])
        # 根据操作系统类型获取聚合机器
        host_list = [{"host_id": host["bk_host_id"]} for host in hosts]
        host_infos = HostHandler.details(scope_list=[{"bk_biz_id": self.data["bk_biz_id"]}], host_list=host_list)
        os_type__hosts = {
            int(os_type): list(host_list) for os_type, host_list in groupby(host_infos, key=lambda x: x["os_type"])
        }
        return os_type__hosts

    def build_dns_apply_flow(
        self, dns_pipeline: Union[Builder, SubBuilder], grayscale: bool = False
    ) -> Union[Builder, SubBuilder]:
        """部署dns的通用流程"""

        sub_dns_pipeline_list: List[SubProcess] = []
        # 构造dns部署子流程
        for host_info in self.data["dns"]["host_infos"]:
            dns_deploy_pipeline = SubBuilder(self.root_id, data=self.data)
            dns_deploy_pipeline = self.deploy_dns_service_pipeline(host_info, dns_deploy_pipeline)
            sub_dns_pipeline_list.append(
                dns_deploy_pipeline.build_sub_process(sub_name=_("主机{}部署dns服务").format(host_info["ip"]))
            )
        # 灰度部署的场景在重装会用到，每次按1/2的数量进行重启
        ratio = 2 if grayscale else 1
        dns_pipeline = self.deploy_batch_service_flow(
            sub_pipeline_list=sub_dns_pipeline_list, pipeline=dns_pipeline, name=_("部署dns服务"), ratio=ratio
        )
        return dns_pipeline

    def add_dns_flush_act(
        self,
        dns_pipeline: Union[Builder, SubBuilder],
        old_dns_infos: Dict,
        new_dns_infos: Dict = None,
        force: bool = False,
    ):
        """添加存量机器的dns配置刷新节点"""

        flush_pipeline = SubBuilder(self.root_id, data=self.data)
        flush_act_list: List[Dict] = []
        # 获取待裁撤的dns节点
        old_dns_ids = [info["id"] for info in old_dns_infos]
        os_type__hosts = self._get_inventory_hosts(old_dns_ids)
        if not os_type__hosts:
            logger.info(_("当前裁撤的dns服务器并没有任何主机使用，跳过nameserver刷新节点"))
            return dns_pipeline
        # 获取替换的dns ip和上新的dns ip
        new_dns_infos = new_dns_infos or DnsManage.match_dns(old_dns_ids, self.data["bk_cloud_id"], len(old_dns_ids))
        old_dns_ips = [info["ip"] for info in old_dns_infos]
        new_dns_ips = [info["ip"] for info in new_dns_infos]
        # 根据操作系统类型对存量机器执行nameserver替换脚本
        for os_type, flush_script_template in self.OS_TYPE__FLUSH_TEMPLATES.items():
            if os_type not in os_type__hosts:
                continue

            act_kwargs = CloudServiceActKwargs(
                bk_cloud_id=self.data["bk_cloud_id"],
                exec_ip=os_type__hosts[os_type],
                get_payload_func=CloudServiceActPayload.get_dns_flush_payload.__name__,
                script_tpl=flush_script_template,
            )
            dns_flush_kwargs = CloudDNSFlushActKwargs(
                os_type=os_type, new_dns_ips=new_dns_ips, old_dns_ips=old_dns_ips, force=force
            )
            flush_act_list.append(
                {
                    "act_name": _("【{}】存量机器nameserver刷新").format(MachineOsType.get_choice_label(os_type)),
                    "act_component_code": ExecCloudScriptComponent.code,
                    "kwargs": {**asdict(act_kwargs), **asdict(dns_flush_kwargs)},
                }
            )

        flush_pipeline.add_parallel_acts(flush_act_list)
        dns_pipeline.add_sub_pipeline(flush_pipeline.build_sub_process(sub_name=_("存量机器的nameserver刷新")))

        return dns_pipeline

    def service_apply_flow(self):
        """
        云区域dns服务的部署流程执行
        """
        dns_pipeline = Builder(root_id=self.root_id, data=self.data)

        # 部署dns
        dns_pipeline = self.build_dns_apply_flow(dns_pipeline)

        # 更新db proxy的元信息
        dns_pipeline = self.add_dbproxy_act(
            pipeline=dns_pipeline,
            host_infos=self.data["dns"]["host_infos"],
            proxy_func_name=CloudDBProxy.cloud_dns_apply.__name__,
        )
        dns_pipeline.run_pipeline()

    def service_reload_flow(self):
        """
        云区域dns服务的重启/重装流程执行
        """
        # 重启/重装等同于重新部署，不影响其他组件. 注：采用灰度重启/重装
        dns_pipeline = Builder(root_id=self.root_id, data=self.data)
        dns_pipeline = self.build_dns_apply_flow(dns_pipeline, grayscale=True)
        dns_pipeline.run_pipeline()

    def service_add_flow(self):
        """
        云区域dns服务的增加流程执行
        """
        dns_pipeline = Builder(root_id=self.root_id, data=self.data)

        # 部署新增的dns(新增操作不需要对存量机器进行dns刷新)
        dns_pipeline = self.build_dns_apply_flow(dns_pipeline)

        # 更新db proxy信息
        dns_pipeline = self.add_dbproxy_act(
            pipeline=dns_pipeline,
            host_infos=self.data["dns"]["host_infos"],
            proxy_func_name=CloudDBProxy.cloud_dns_apply.__name__,
        )
        dns_pipeline.run_pipeline()

    def service_reduce_flow(self):
        """
        云区域dns服务的下架流程执行
        """
        dns_pipeline = Builder(root_id=self.root_id, data=self.data)
        reduce_dns_host_infos = self.data["dns"]["host_infos"]

        # 存量机器的nameserver刷新
        dns_pipeline = self.add_dns_flush_act(dns_pipeline=dns_pipeline, old_dns_infos=reduce_dns_host_infos)

        # 添加人工确认节点
        dns_pipeline.add_act(act_name=_("人工确认"), act_component_code=PauseComponent.code, kwargs={})

        # 裁撤旧drs服务
        dns_pipeline = self.add_reduce_act(
            pipeline=dns_pipeline,
            host_infos=reduce_dns_host_infos,
            payload_func_name=CloudServiceActPayload.get_dns_reduce_payload.__name__,
            script_tpl=stop_dns_server_template,
        )

        # 更新proxy信息
        dns_pipeline = self.add_dbproxy_act(
            pipeline=dns_pipeline,
            host_infos=reduce_dns_host_infos,
            proxy_func_name=CloudDBProxy.cloud_dns_reduce.__name__,
        )

        dns_pipeline.run_pipeline()

    def service_replace_flow(self):
        """
        云区域dns服务的替换流程执行
        """

        dns_pipeline = Builder(root_id=self.root_id, data=self.data)
        new_dns_host_infos = self.data["dns"]["host_infos"]
        old_dns_host_infos = self.data["old_dns"]["host_infos"]

        # 部署新的dns流程
        dns_pipeline = self.build_dns_apply_flow(dns_pipeline)

        # 存量机器的nameserver刷新
        dns_pipeline = self.add_dns_flush_act(
            dns_pipeline=dns_pipeline, old_dns_infos=old_dns_host_infos, new_dns_infos=new_dns_host_infos
        )

        # 添加人工确认节点
        dns_pipeline.add_act(act_name=_("人工确认"), act_component_code=PauseComponent.code, kwargs={})

        # 更新db proxy信息
        dns_pipeline = self.add_dbproxy_act(
            pipeline=dns_pipeline,
            host_infos=new_dns_host_infos,
            proxy_func_name=CloudDBProxy.cloud_dns_replace.__name__,
            extra_kwargs={"old_dns": old_dns_host_infos},
        )

        # 裁撤旧的dns流程
        dns_pipeline = self.add_reduce_act(
            pipeline=dns_pipeline,
            host_infos=old_dns_host_infos,
            payload_func_name=CloudServiceActPayload.get_dns_reduce_payload.__name__,
            script_tpl=stop_dns_server_template,
        )

        dns_pipeline.run_pipeline()
