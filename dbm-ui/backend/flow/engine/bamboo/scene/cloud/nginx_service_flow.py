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

from django.utils.translation import ugettext as _

from backend.flow.engine.bamboo.scene.cloud.base_service_flow import CloudBaseServiceFlow
from backend.flow.engine.bamboo.scene.cloud.dbha_service_flow import CloudDBHAServiceFlow
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.utils.cloud.cloud_act_payload import CloudServiceActPayload
from backend.flow.utils.cloud.cloud_db_proxy import CloudDBProxy
from backend.flow.utils.cloud.script_template import nginx_stop_template

logger = logging.getLogger("flow")


class CloudNginxServiceFlow(CloudBaseServiceFlow):
    """云区域部署nginx服务流程"""

    def service_apply_flow(self):
        """
        云区域nginx服务的部署流程执行
        """
        nginx_pipeline = Builder(root_id=self.root_id, data=self.data)
        # 部署nginx，目前认为nginx只部署一台
        nginx_pipeline = self.deploy_nginx_service_pipeline(self.data["nginx"]["host_infos"][0], nginx_pipeline)

        # 写入proxy信息
        nginx_pipeline = self.add_dbproxy_act(
            pipeline=nginx_pipeline,
            proxy_func_name=CloudDBProxy.cloud_nginx_apply.__name__,
            host_infos=self.data["nginx"]["host_infos"],
            host_kwargs=None,
            extra_kwargs=None,
        )

        nginx_pipeline.run_pipeline()

    def service_reload_flow(self):
        """
        云区域nginx服务的重装流程执行
        """
        nginx_pipeline = Builder(root_id=self.root_id, data=self.data)
        # nginx重装等价于用原来的参数重新部署一次
        nginx_pipeline = self.deploy_nginx_service_pipeline(self.data["nginx"]["host_infos"][0], nginx_pipeline)
        nginx_pipeline.run_pipeline()

    def service_replace_flow(self):
        """
        云区域nginx服务的替换流程执行
        """
        # 首先部署新nginx
        nginx_pipeline = Builder(root_id=self.root_id, data=self.data)
        nginx_pipeline = self.deploy_nginx_service_pipeline(self.data["nginx"]["host_infos"][0], nginx_pipeline)

        # 重新部署DNS组件(串行化部署)
        dns_pipeline = SubBuilder(root_id=self.root_id, data=self.data)
        for dns_host in self.data["dns"]["host_infos"]:
            dns_deploy_pipeline = SubBuilder(self.root_id, data=self.data)
            dns_deploy_pipeline = self.deploy_dns_service_pipeline(dns_host, dns_deploy_pipeline)
            dns_pipeline.add_sub_pipeline(
                dns_deploy_pipeline.build_sub_process(sub_name=_("主机{}部署dns服务").format(dns_host["ip"]))
            )

        # 重新部署DBHA组件
        dbha_pipeline = SubBuilder(root_id=self.root_id, data=self.data)
        dbha_pipeline, __ = CloudDBHAServiceFlow(self.root_id, self.data).build_dbha_apply_flow(dbha_pipeline)

        nginx_pipeline.add_parallel_sub_pipeline(
            sub_flow_list=[
                dns_pipeline.build_sub_process(sub_name=_("串行化部署DNS服务")),
                dbha_pipeline.build_sub_process(sub_name=_("部署DBHA服务")),
            ]
        )

        # 裁撤旧nginx机器
        nginx_pipeline = self.add_reduce_act(
            pipeline=nginx_pipeline,
            host_infos=self.data["old_nginx"]["host_infos"],
            payload_func_name=CloudServiceActPayload.get_nginx_reduce_payload.__name__,
            script_tpl=nginx_stop_template,
        )

        # 更新proxy信息
        nginx_pipeline = self.add_dbproxy_act(
            pipeline=nginx_pipeline,
            proxy_func_name=CloudDBProxy.cloud_nginx_replace.__name__,
            host_infos=self.data["nginx"]["host_infos"],
            host_kwargs=None,
            extra_kwargs={"old_nginx": self.data["old_nginx"]["host_infos"]},
        )

        nginx_pipeline.run_pipeline()
