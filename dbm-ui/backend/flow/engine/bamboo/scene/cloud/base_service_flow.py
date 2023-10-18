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
from typing import Any, Dict, List, Optional, Union

from django.utils.crypto import get_random_string
from django.utils.translation import ugettext as _

from backend.core.encrypt.constants import AsymmetricCipherConfigType
from backend.core.encrypt.handlers import AsymmetricHandler
from backend.flow.consts import CloudServiceConfFileEnum, CloudServiceName
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.cloud.exec_service_script import ExecCloudScriptComponent
from backend.flow.plugins.components.collections.cloud.push_config_file import PushConfigFiletComponent
from backend.flow.plugins.components.collections.cloud.service_proxy import CloudProxyComponent
from backend.flow.plugins.components.collections.cloud.trans_files import CloudTransFileComponent
from backend.flow.utils.cloud.cloud_act_payload import CloudServiceActPayload
from backend.flow.utils.cloud.cloud_context_dataclass import (
    CloudConfKwargs,
    CloudDBHAKwargs,
    CloudDRSKwargs,
    CloudPrivilegeFlushActKwargs,
    CloudProxyKwargs,
    CloudServiceActKwargs,
)
from backend.flow.utils.cloud.script_template import (
    dbha_start_script_template,
    dns_pull_crond_conf_template,
    drs_env_template,
    ha_agent_conf_template,
    ha_gm_conf_template,
    start_dns_service_template,
    start_drs_service_template,
    start_nginx_template,
    start_redis_dts_server_template,
)
from backend.flow.utils.script_template import privilege_flush_template

logger = logging.getLogger("flow")


class CloudBaseServiceFlow(object):
    """云区域部署第三方服务流程类"""

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        传入参数
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递过来的参数列表，是dict格式
        """
        self.root_id = root_id
        self.data = data

    def _get_or_generate_usr_pwd(self, service: str, host_infos: Dict = None, force: bool = False):
        """获取drs和dbha的超级账户"""
        rsa_cloud_name = AsymmetricCipherConfigType.get_cipher_cloud_name(self.data["bk_cloud_id"])

        if host_infos:
            host = host_infos[0]
        else:
            host_infos = self.data[service]
            if service == CloudServiceName.DBHA:
                # 认为gm和agent存储的密码都是一样的
                host = host_infos["gm"][0] if host_infos["gm"] else host_infos["agent"][0]
            else:
                host = host_infos["host_infos"][0]

        # 若任意一台主机信息包含用户/密码，则沿用直接返回解密原始账户或密码，否则生成
        if "user" in host and not force:
            user, pwd = host["user"], host["pwd"]
            plain_user = AsymmetricHandler.decrypt(name=rsa_cloud_name, content=user)
            plain_pwd = AsymmetricHandler.decrypt(name=rsa_cloud_name, content=pwd)
        else:
            plain_user, plain_pwd = get_random_string(8), get_random_string(16)
            user = AsymmetricHandler.encrypt(name=rsa_cloud_name, content=plain_user)
            pwd = AsymmetricHandler.encrypt(name=rsa_cloud_name, content=plain_pwd)

        return {"user": user, "pwd": pwd, "plain_user": plain_user, "plain_pwd": plain_pwd}

    def _get_access_hosts(self, host_infos):
        return [host["ip"] for host in host_infos]

    def deploy_service_flow(
        self,
        pipeline: Union[Builder, SubBuilder],
        bk_cloud_id: int,
        service_name: str,
        host_info: Dict[str, str],
        get_file_func: str,
        script_template: str,
        get_script_payload: str,
        extra_params: Dict[Union[str, int], Any] = None,
    ) -> Union[Builder, SubBuilder]:
        """
        部署二进制脚本服务的通用流程
        分为四个步骤：下发二进制文件/压缩包 ---> 渲染脚本文件并下发到机器执行 ---> 写入meta信息
        @param pipeline: 流程
        @param bk_cloud_id: 云区域ID
        @param service_name: 服务名称
        @param host_info: 部署的机器信息
        @param get_file_func: 获取二进制/压缩包文件函数名
        @param script_template: 部署的脚本模板
        @param get_script_payload: 脚本渲染函数名称
        @param extra_params: 额外参数，填充到act的kwagrs中，默认为空
        """

        extra_params = extra_params or {}

        # 下发服务二进制文件/压缩包
        act_kwargs = CloudServiceActKwargs(
            bk_cloud_id=bk_cloud_id,
            file_list=getattr(GetFileList, get_file_func)(),
            exec_ip=host_info,
            ticket_data=self.data,
        )
        pipeline.add_act(
            act_name=_("下发{}可执行文件包").format(service_name),
            act_component_code=CloudTransFileComponent.code,
            kwargs={**asdict(act_kwargs), **extra_params},
        )

        # 下发服务脚本，运行服务进程
        act_kwargs.script_tpl = script_template
        act_kwargs.get_payload_func = get_script_payload
        pipeline.add_act(
            act_name=_("部署{}服务进程").format(service_name),
            act_component_code=ExecCloudScriptComponent.code,
            kwargs={**asdict(act_kwargs), **extra_params},
        )

        return pipeline

    def deploy_conf_service_flow(
        self,
        pipeline: Union[Builder, SubBuilder],
        bk_cloud_id: int,
        service_name: str,
        host_info: Dict[str, str],
        conf_template: str,
        get_conf_payload: str,
        conf_file_name: str,
        get_file_func: str,
        script_template: str,
        get_script_payload: str,
        extra_params: Dict[Union[str, int], Any] = None,
    ) -> Union[Builder, SubBuilder]:
        """
        部署带有conf脚本服务的通用流程
        分为四个步骤：渲染conf文件并下发到机器 ---> 下发二进制文件/压缩包 ---> 渲染脚本文件并下发到机器执行 ---> 写入meta信息
        @param pipeline: 流程
        @param bk_cloud_id: 云区域ID
        @param service_name: 服务名称
        @param host_info: 部署的机器信息
        @param conf_template: 配置文件模板
        @param get_conf_payload: 配置文件渲染函数名称
        @param conf_file_name: 配置文件名
        @param get_file_func: 获取二进制/压缩包文件函数名
        @param script_template: 部署的脚本模板
        @param get_script_payload: 脚本渲染函数名称
        @param extra_params: 额外参数，填充到act的kwagrs中，默认为空
        """

        extra_params = extra_params or {}

        # 下发服务配置文件
        act_kwargs = CloudConfKwargs(
            bk_cloud_id=bk_cloud_id,
            exec_ip=host_info,
            ticket_data=self.data,
            script_tpl=conf_template,
            get_payload_func=get_conf_payload,
            conf_file_name=conf_file_name,
        )
        pipeline.add_act(
            act_name=_("下发{}配置文件").format(conf_file_name),
            act_component_code=PushConfigFiletComponent.code,
            kwargs={**asdict(act_kwargs), **extra_params},
        )

        pipeline = self.deploy_service_flow(
            pipeline=pipeline,
            bk_cloud_id=bk_cloud_id,
            service_name=service_name,
            host_info=host_info,
            get_file_func=get_file_func,
            script_template=script_template,
            get_script_payload=get_script_payload,
            extra_params={**extra_params, "conf_file_name": conf_file_name},
        )

        return pipeline

    def deploy_nginx_service_pipeline(self, nginx_host_info: Dict, pipeline: Union[Builder, SubBuilder]):
        """nginx的部署流程抽象"""
        pipeline = self.deploy_service_flow(
            pipeline=pipeline,
            bk_cloud_id=self.data["bk_cloud_id"],
            service_name=CloudServiceName.Nginx,
            host_info=nginx_host_info,
            get_file_func=GetFileList.nginx_apply.__name__,
            script_template=start_nginx_template,
            get_script_payload=CloudServiceActPayload.get_nginx_apply_payload.__name__,
        )
        return pipeline

    def deploy_drs_service_pipeline(
        self, drs_kwargs: CloudDRSKwargs, drs_host_info: Dict, pipeline: Union[Builder, SubBuilder]
    ):
        """drs的部署流程抽象"""
        pipeline = self.deploy_conf_service_flow(
            pipeline=pipeline,
            bk_cloud_id=self.data["bk_cloud_id"],
            service_name=CloudServiceName.DRS,
            host_info=drs_host_info,
            conf_template=drs_env_template,
            get_conf_payload=CloudServiceActPayload.get_drs_env_conf_payload.__name__,
            conf_file_name=CloudServiceConfFileEnum.DRS_ENV.value,
            get_file_func=GetFileList.drs_apply.__name__,
            script_template=start_drs_service_template,
            get_script_payload=CloudServiceActPayload.get_drs_apply_paylaod.__name__,
            extra_params=asdict(drs_kwargs),
        )
        return pipeline

    def deploy_dns_service_pipeline(self, dns_host_info: Dict, pipeline: Union[Builder, SubBuilder]):
        """dns的部署流程抽象"""
        pipeline = self.deploy_conf_service_flow(
            pipeline=pipeline,
            bk_cloud_id=self.data["bk_cloud_id"],
            service_name=CloudServiceName.DNS,
            host_info=dns_host_info,
            conf_template=dns_pull_crond_conf_template,
            get_conf_payload=CloudServiceActPayload.get_dns_pull_crond_conf_payload.__name__,
            conf_file_name=CloudServiceConfFileEnum.PullCrond.value,
            get_file_func=GetFileList.dns_apply.__name__,
            script_template=start_dns_service_template,
            get_script_payload=CloudServiceActPayload.get_dns_apply_payload.__name__,
        )
        return pipeline

    def deploy_gm_service_pipeline(
        self, gm_host_info: Dict, dbha_kwargs: CloudDBHAKwargs, pipeline: Union[Builder, SubBuilder]
    ):
        """dbha-gm的部署流程抽象"""
        pipeline = self.deploy_conf_service_flow(
            pipeline=pipeline,
            bk_cloud_id=self.data["bk_cloud_id"],
            service_name=f"{CloudServiceName.DBHA}-gm",
            host_info=gm_host_info,
            conf_template=ha_gm_conf_template,
            get_conf_payload=CloudServiceActPayload.get_dbha_conf_payload.__name__,
            conf_file_name=CloudServiceConfFileEnum.HA_GM.value,
            get_file_func=GetFileList.dbha_apply.__name__,
            script_template=dbha_start_script_template,
            get_script_payload=CloudServiceActPayload.get_dbha_apply_payload.__name__,
            extra_params=asdict(dbha_kwargs),
        )
        return pipeline

    def deploy_agent_service_pipeline(
        self, agent_host_info: Dict, dbha_kwargs: CloudDBHAKwargs, pipeline: Union[Builder, SubBuilder]
    ):
        """dbha-agent的部署流程抽象"""
        pipeline = self.deploy_conf_service_flow(
            pipeline=pipeline,
            bk_cloud_id=self.data["bk_cloud_id"],
            service_name=f"{CloudServiceName.DBHA}-agent",
            host_info=agent_host_info,
            conf_template=ha_agent_conf_template,
            get_conf_payload=CloudServiceActPayload.get_dbha_conf_payload.__name__,
            conf_file_name=CloudServiceConfFileEnum.HA_AGENT.value,
            get_file_func=GetFileList.dbha_apply.__name__,
            script_template=dbha_start_script_template,
            get_script_payload=CloudServiceActPayload.get_dbha_apply_payload.__name__,
            extra_params=asdict(dbha_kwargs),
        )
        return pipeline

    def deploy_redis_dts_server_service_pipeline(
        self, dts_server_host_info: Dict, pipeline: Union[Builder, SubBuilder]
    ):
        """redis dts_server的部署流程抽象"""
        pipeline = self.deploy_service_flow(
            pipeline=pipeline,
            bk_cloud_id=self.data["bk_cloud_id"],
            service_name=CloudServiceName.RedisDTS,
            host_info=dts_server_host_info,
            get_file_func=GetFileList.redis_add_dts_server.__name__,
            script_template=start_redis_dts_server_template,
            get_script_payload=CloudServiceActPayload.get_redis_dts_server_apply_payload.__name__,
        )
        return pipeline

    def add_privilege_act(self, pipeline: Union[Builder, SubBuilder], host_infos: Dict, user: str, pwd: str):
        """
        增加权限刷新的act
        @param pipeline: 流水线
        @param host_infos: 部署的机器信息
        @param user: 用户名
        @param pwd: 密码
        """

        if not host_infos:
            return pipeline

        act_kwargs = CloudServiceActKwargs(
            bk_cloud_id=self.data["bk_cloud_id"],
            exec_ip=host_infos,
            get_payload_func=CloudServiceActPayload.privilege_flush_payload.__name__,
            script_tpl=privilege_flush_template,
        )
        privilege_flush_kwargs = CloudPrivilegeFlushActKwargs(
            access_hosts=self._get_access_hosts(host_infos), user=user, pwd=pwd, type="add"
        )
        pipeline.add_act(
            act_name=_("存量集群的权限更新"),
            act_component_code=ExecCloudScriptComponent.code,
            kwargs={**asdict(act_kwargs), **asdict(privilege_flush_kwargs)},
        )
        return pipeline

    def add_dbproxy_act(
        self,
        pipeline: Union[Builder, SubBuilder],
        proxy_func_name: str,
        host_infos: List[Dict],
        host_kwargs: Dict = None,
        extra_kwargs: Dict = None,
    ):
        """
        增加dbproxyy元数据更新操作
        @param pipeline: 流水线
        @param proxy_func_name: 元数据更新函数名
        @param host_infos: 部署的机器信息
        @param host_kwargs: 更新的机器信息
        @param extra_kwargs: 对于CloudProxyKwargs额外的参数
        """

        host_kwargs = host_kwargs or []
        for host in host_infos:
            host.update(host_kwargs)

        pipeline.add_act(
            act_name=_("更新服务元信息"),
            act_component_code=CloudProxyComponent.code,
            kwargs=asdict(
                CloudProxyKwargs(
                    bk_cloud_id=self.data["bk_cloud_id"],
                    host_infos=host_infos,
                    proxy_func_name=proxy_func_name,
                    details=extra_kwargs,
                )
            ),
        )
        return pipeline

    def add_reduce_act(
        self, pipeline: Union[Builder, SubBuilder], host_infos: Dict, payload_func_name: str, script_tpl: str
    ):
        """
        为流程增加裁撤节点
        @param pipeline: 流水线
        @param host_infos: 裁撤的机器信息
        @param payload_func_name: 裁撤脚本参数填充函数名
        @param script_tpl: 裁撤脚本
        """
        reduce_ips = self._get_access_hosts(host_infos)
        pipeline.add_act(
            act_name=_("裁撤{}的服务").format(reduce_ips),
            act_component_code=ExecCloudScriptComponent.code,
            kwargs=asdict(
                CloudServiceActKwargs(
                    bk_cloud_id=self.data["bk_cloud_id"],
                    exec_ip=host_infos,
                    get_payload_func=payload_func_name,
                    script_tpl=script_tpl,
                )
            ),
        )
        return pipeline

    def add_nginx_reload_sub_pipeline(self, pipeline: Union[Builder, SubBuilder]):
        """
        为流程增加nginx重启的子流程
        @param pipeline: 流水线
        """

        nginx_reload_pipeline = SubBuilder(data=self.data, root_id=self.root_id)
        nginx_reload_pipeline = self.deploy_nginx_service_pipeline(
            self.data["nginx"]["host_infos"][0], nginx_reload_pipeline
        )
        pipeline.add_sub_pipeline(nginx_reload_pipeline.build_sub_process(sub_name=_("重启nginx服务")))
        return pipeline

    def service_apply_flow(self):
        """「必须」组件部署的流程"""
        raise NotImplementedError()

    def service_add_flow(self):
        """「非必须」组件新增的流程"""
        pass

    def service_reduce_flow(self):
        """「非必须」组件裁撤的流程"""
        pass

    def service_replace_flow(self):
        """「非必须」组件替换的流程，注：现在暂且只支持单个替换"""
        pass
