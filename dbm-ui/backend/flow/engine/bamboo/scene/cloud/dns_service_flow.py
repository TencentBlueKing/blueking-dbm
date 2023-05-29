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
from typing import Dict, List, Union

from bamboo_engine.builder import SubProcess
from django.utils.translation import ugettext as _

from backend.flow.engine.bamboo.scene.cloud.base_service_flow import CloudBaseServiceFlow
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.plugins.components.collections.cloud.exec_service_script import ExecCloudScriptComponent
from backend.flow.utils.cloud.cloud_act_payload import CloudServiceActPayload
from backend.flow.utils.cloud.cloud_context_dataclass import CloudDNSFlushActKwargs, CloudServiceActKwargs
from backend.flow.utils.cloud.cloud_db_proxy import CloudDBProxy
from backend.flow.utils.cloud.script_template import dns_flush_templace, stop_dns_server_template

logger = logging.getLogger("flow")


class CloudDNSServiceFlow(CloudBaseServiceFlow):
    """云区域部署dns服务流程"""

    def _get_inventory_hosts(self):
        """TODO: 获取存量机器的信息, 需要后续DNS配置产品化才实现"""
        inventory_hosts = []
        inventory_hosts.extend(self.data["drs"]["host_infos"])
        return inventory_hosts

    def build_dns_apply_flow(
        self, dns_pipeline: Union[Builder, SubBuilder], grayscale: bool = False
    ) -> Union[Builder, SubBuilder]:
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

    def add_dns_flush_act(self, dns_pipeline: Union[Builder, SubBuilder], host_infos: Dict, flush_type: str):
        """添加权限刷新节点"""
        # 刷新存量机器和DRS的nameserver
        inventory_hosts = self._get_inventory_hosts()
        act_kwargs = CloudServiceActKwargs(
            bk_cloud_id=self.data["bk_cloud_id"],
            exec_ip=inventory_hosts,
            get_payload_func=CloudServiceActPayload.get_dns_flush_payload.__name__,
            script_tpl=dns_flush_templace,
        )
        dns_flush_kwargs = CloudDNSFlushActKwargs(dns_ips=self._get_access_hosts(host_infos), flush_type=flush_type)
        dns_pipeline.add_act(
            act_name=_("对存量机器的nameserver刷新"),
            act_component_code=ExecCloudScriptComponent.code,
            kwargs={**asdict(act_kwargs), **asdict(dns_flush_kwargs)},
        )
        return dns_pipeline

    def service_apply_flow(self):
        """
        云区域dns服务的部署流程执行
        """
        dns_pipeline = Builder(root_id=self.root_id, data=self.data)

        # 部署dns
        dns_pipeline = self.build_dns_apply_flow(dns_pipeline)

        # 更新dbproxy信息
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
        # 重启/重装等同于重新部署，不影响其他组件
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

        # 更新dbproxy信息
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

        # nameserver刷新
        dns_pipeline = self.add_dns_flush_act(dns_pipeline, reduce_dns_host_infos, flush_type="delete")

        # 裁撤旧drs服务
        dns_pipeline = self.add_reduce_act(
            pipeline=dns_pipeline,
            host_infos=reduce_dns_host_infos,
            payload_func_name=CloudServiceActPayload.get_dns_reduce_payload.__name__,
            script_tpl=stop_dns_server_template,
        )

        # 更新proxy机器
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
        new_drs_host_infos = self.data["dns"]["host_infos"]
        old_drs_host_infos = self.data["old_dns"]["host_infos"]

        # 部署新的dns流程
        deploy_dns_pipeline = SubBuilder(data=self.data, root_id=self.root_id)
        deploy_dns_pipeline = self.build_dns_apply_flow(deploy_dns_pipeline)
        deploy_dns_pipeline = self.add_dns_flush_act(deploy_dns_pipeline, new_drs_host_infos, flush_type="add")
        dns_pipeline.add_sub_pipeline(deploy_dns_pipeline.build_sub_process(sub_name=_("部署新dns服务流程")))

        # 更新dbproxy信息
        dns_pipeline = self.add_dbproxy_act(
            pipeline=dns_pipeline,
            host_infos=new_drs_host_infos,
            proxy_func_name=CloudDBProxy.cloud_dns_replace.__name__,
            extra_kwargs={"old_dns": old_drs_host_infos},
        )

        # 裁撤旧的dns流程
        reduce_dns_pipeline = SubBuilder(data=self.data, root_id=self.root_id)
        reduce_dns_pipeline = self.add_dns_flush_act(reduce_dns_pipeline, old_drs_host_infos, flush_type="delete")
        reduce_dns_pipeline = self.add_reduce_act(
            pipeline=reduce_dns_pipeline,
            host_infos=old_drs_host_infos,
            payload_func_name=CloudServiceActPayload.get_dns_reduce_payload.__name__,
            script_tpl=stop_dns_server_template,
        )
        dns_pipeline.add_sub_pipeline(reduce_dns_pipeline.build_sub_process(sub_name=_("裁撤旧dns服务流程")))

        dns_pipeline.run_pipeline()
