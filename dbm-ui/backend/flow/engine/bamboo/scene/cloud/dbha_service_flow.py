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
from dataclasses import asdict
from typing import Dict, List, Tuple, Union

from bamboo_engine.builder import SubProcess
from django.utils.translation import ugettext as _

from backend import env
from backend.flow.consts import CloudDBHATypeEnum, CloudServiceName
from backend.flow.engine.bamboo.scene.cloud.base_service_flow import CloudBaseServiceFlow
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.utils.cloud.cloud_act_payload import CloudServiceActPayload
from backend.flow.utils.cloud.cloud_context_dataclass import CloudDBHAKwargs
from backend.flow.utils.cloud.cloud_db_proxy import CloudDBProxy
from backend.flow.utils.cloud.script_template import dbha_stop_script_template


class CloudDBHAServiceFlow(CloudBaseServiceFlow):
    """云区域部署dbha服务流程"""

    def _build_gm_apply_flow(self, gm_pipeline: SubBuilder, super_account: Dict) -> Tuple[SubBuilder, CloudDBHAKwargs]:
        """构建gm部署流程"""
        nginx_internal_domain = self.data["nginx"]["host_infos"][0]["ip"]
        dbha_kwargs = CloudDBHAKwargs(
            dbha_type=CloudDBHATypeEnum.GM,
            nginx_internal_domain=nginx_internal_domain,
            name_service_domain=env.NAMESERVICE_APIGW_DOMAIN,
            **super_account
        )
        sub_gm_pipeline_list: List[SubProcess] = []
        for host_info in self.data["dbha"]["gm"]:
            sub_gm_pipeline = SubBuilder(root_id=self.root_id, data=self.data)
            sub_gm_pipeline = self.deploy_gm_service_pipeline(host_info, dbha_kwargs, sub_gm_pipeline)
            sub_gm_pipeline_list.append(
                sub_gm_pipeline.build_sub_process(sub_name=_("主机{}部署gm服务").format(host_info["ip"]))
            )

        gm_pipeline.add_parallel_sub_pipeline(sub_gm_pipeline_list)
        return gm_pipeline, dbha_kwargs

    def _build_agent_apply_flow(
        self, agent_pipeline: SubBuilder, super_account: Dict
    ) -> Tuple[SubBuilder, CloudDBHAKwargs]:
        """构建agent部署流程"""
        nginx_internal_domain = self.data["nginx"]["host_infos"][0]["ip"]
        dbha_kwargs = CloudDBHAKwargs(
            dbha_type=CloudDBHATypeEnum.AGENT.value,
            nginx_internal_domain=nginx_internal_domain,
            name_service_domain=env.NAMESERVICE_APIGW_DOMAIN,
            **super_account
        )
        sub_agent_pipeline_list: List[SubProcess] = []
        for host_info in self.data["dbha"]["agent"]:
            sub_agent_pipeline = SubBuilder(root_id=self.root_id, data=self.data)
            sub_agent_pipeline = self.deploy_agent_service_pipeline(host_info, dbha_kwargs, sub_agent_pipeline)
            sub_agent_pipeline_list.append(
                sub_agent_pipeline.build_sub_process(sub_name=_("主机{}部署agent服务").format(host_info["ip"]))
            )

        agent_pipeline.add_parallel_sub_pipeline(sub_agent_pipeline_list)
        return agent_pipeline, dbha_kwargs

    def build_dbha_apply_flow(
        self, dbha_pipeline: Union[Builder, SubBuilder]
    ) -> Tuple[Union[Builder, SubBuilder], CloudDBHAKwargs]:
        """dbha的部署逻辑，这里抽象是为了后面其他组件操作的通用使用"""

        # 获得dbha专属账号
        super_account = self._get_or_generate_usr_pwd(CloudServiceName.DBHA)
        # 构建gm部署流程
        if self.data["dbha"]["gm"]:
            gm_pipeline = SubBuilder(self.root_id, data=self.data)
            gm_pipeline, dbha_kwargs = self._build_gm_apply_flow(gm_pipeline, super_account)
            dbha_pipeline.add_sub_pipeline(gm_pipeline.build_sub_process(sub_name=_("部署dbha-gm服务")))

        # 构建agent部署
        if self.data["dbha"]["agent"]:
            agent_pipeline = SubBuilder(self.root_id, data=self.data)
            agent_pipeline, dbha_kwargs = self._build_agent_apply_flow(agent_pipeline, super_account)
            dbha_pipeline.add_sub_pipeline(agent_pipeline.build_sub_process(sub_name=_("部署dbha-agent服务")))

        return dbha_pipeline, dbha_kwargs

    def build_dbha_reduce_acts(
        self, dbha_pipeline: Union[Builder, SubBuilder], old_gm: Dict = None, old_agent: Dict = None
    ) -> Union[Builder, SubBuilder]:
        # 裁撤gm服务
        if old_gm:
            dbha_pipeline = self.add_reduce_act(
                pipeline=dbha_pipeline,
                host_infos=old_gm,
                payload_func_name=CloudServiceActPayload.get_dbha_gm_reduce_payload.__name__,
                script_tpl=dbha_stop_script_template,
            )

        # 裁撤agent服务
        if old_agent:
            dbha_pipeline = self.add_reduce_act(
                pipeline=dbha_pipeline,
                host_infos=old_agent,
                payload_func_name=CloudServiceActPayload.get_dbha_agent_reduce_payload.__name__,
                script_tpl=dbha_stop_script_template,
            )

        return dbha_pipeline

    def service_apply_flow(self):
        # 部署gm/agent流程
        dbha_pipeline = Builder(root_id=self.root_id, data=self.data)
        dbha_pipeline, dbha_kwargs = self.build_dbha_apply_flow(dbha_pipeline)

        # 写入gm/agent的proxy信息
        dbha_pipeline = self.add_dbproxy_act(
            pipeline=dbha_pipeline,
            proxy_func_name=CloudDBProxy.cloud_dbha_apply.__name__,
            host_infos=[*self.data["dbha"]["agent"], *self.data["dbha"]["gm"]],
            host_kwargs={"user": dbha_kwargs.user, "pwd": dbha_kwargs.pwd},
        )

        dbha_pipeline.run_pipeline()

    def service_reload_flow(self):
        # dbha的重启/重装 等于获取原来部署参数重新部署一遍
        dbha_pipeline = Builder(root_id=self.root_id, data=self.data)
        dbha_pipeline, __ = self.build_dbha_apply_flow(dbha_pipeline)
        dbha_pipeline.run_pipeline()

    def service_add_flow(self):
        dbha_pipeline = Builder(root_id=self.root_id, data=self.data)
        gm_add_host_infos = self.data["dbha"]["gm"]
        agent_add_host_infos = self.data["dbha"]["agent"]

        # 部署新增的dbha服务
        dbha_pipeline, dbha_kwargs = self.build_dbha_apply_flow(dbha_pipeline)

        # 权限刷新
        dbha_pipeline = self.add_privilege_act(
            pipeline=dbha_pipeline, host_infos=gm_add_host_infos, user=dbha_kwargs.user, pwd=dbha_kwargs.pwd
        )

        # 写入gm/agent的proxy信息
        dbha_pipeline = self.add_dbproxy_act(
            pipeline=dbha_pipeline,
            proxy_func_name=CloudDBProxy.cloud_dbha_apply.__name__,
            host_infos=[*agent_add_host_infos, *gm_add_host_infos],
            host_kwargs={"user": dbha_kwargs.user, "pwd": dbha_kwargs.pwd},
        )

        dbha_pipeline.run_pipeline()

    def service_reduce_flow(self):
        dbha_pipeline = Builder(root_id=self.root_id, data=self.data)
        gm_reduce_host_infos = self.data["dbha"]["gm"]
        agent_reduce_host_infos = self.data["dbha"]["agent"]

        # 裁撤旧dbha的服务
        dbha_pipeline = self.build_dbha_reduce_acts(dbha_pipeline, gm_reduce_host_infos, agent_reduce_host_infos)

        # 权限刷新
        super_account = self._get_or_generate_usr_pwd(CloudServiceName.DBHA)
        dbha_pipeline = self.add_privilege_act(
            pipeline=dbha_pipeline,
            host_infos=gm_reduce_host_infos,
            user=super_account["user"],
            pwd=super_account["pwd"],
        )

        # 写入gm/agent的proxy信息
        dbha_pipeline = self.add_dbproxy_act(
            pipeline=dbha_pipeline,
            proxy_func_name=CloudDBProxy.cloud_dbha_reduce.__name__,
            host_infos=[*gm_reduce_host_infos, *agent_reduce_host_infos],
        )

        dbha_pipeline.run_pipeline()

    def service_replace_flow(self):
        dbha_pipeline = Builder(root_id=self.root_id, data=self.data)

        # 部署新的dbha组件
        dbha_pipeline, dbha_kwargs = self.build_dbha_apply_flow(dbha_pipeline)

        # 权限刷新
        super_account = self._get_or_generate_usr_pwd(CloudServiceName.DBHA)
        dbha_pipeline = self.add_privilege_act(
            pipeline=dbha_pipeline,
            host_infos=self.data["dbha"]["gm"],
            user=super_account["user"],
            pwd=super_account["pwd"],
        )

        # 写入gm/agent的proxy信息
        dbha_pipeline = self.add_dbproxy_act(
            pipeline=dbha_pipeline,
            proxy_func_name=CloudDBProxy.cloud_dbha_replace.__name__,
            host_infos=[*self.data["dbha"]["agent"], *self.data["dbha"]["gm"]],
            host_kwargs={"user": dbha_kwargs.user, "pwd": dbha_kwargs.pwd},
            extra_kwargs={
                "old_gm": self.data["old_gm"]["host_infos"],
                "old_agent": self.data["old_agent"]["host_infos"],
            },
        )

        # 裁撤旧dbha组件
        dbha_pipeline = self.build_dbha_reduce_acts(
            dbha_pipeline, self.data["old_gm"]["host_infos"], self.data["old_agent"]["host_infos"]
        )

        dbha_pipeline.run_pipeline()
