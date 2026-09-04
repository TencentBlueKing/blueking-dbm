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
from typing import Dict, Optional

from django.utils.translation import gettext as _

from backend.components import DBConfigApi
from backend.components.dbconfig.constants import ConfType, FormatType, LevelName
from backend.configuration.constants import DBType
from backend.flow.consts import (
    ES_DEFAULT_INSTANCE_NUM,
    ManagerDefaultPort,
    ManagerOpType,
    ManagerServiceType,
    NameSpaceEnum,
)
from backend.flow.engine.bamboo.scene.common.bigdata_common_sub_flow import new_machine_common_sub_flow
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.es.atom_jobs.access_manager import get_access_manager_atom_job
from backend.flow.engine.bamboo.scene.es.es_flow import (
    EsFlow,
    get_all_node_ips_in_ticket,
    get_node_in_ticket_preferred_hot,
)
from backend.flow.plugins.components.collections.common.bigdata_manager_service import BigdataManagerComponent
from backend.flow.plugins.components.collections.es.es_apply_summary import add_es_apply_summary_output_act
from backend.flow.plugins.components.collections.es.es_db_meta import EsMetaComponent
from backend.flow.plugins.components.collections.es.exec_es_actuator_script import ExecuteEsActuatorScriptComponent
from backend.flow.plugins.components.collections.es.get_es_payload import GetEsActPayloadComponent
from backend.flow.plugins.components.collections.es.get_es_resource import GetEsResourceComponent
from backend.flow.plugins.components.collections.es.rewrite_es_config import WriteBackEsConfigComponent
from backend.flow.plugins.components.collections.es.trans_files import TransFileComponent
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent as MySQLTransFileComponent
from backend.flow.plugins.components.collections.name_service.es_name_service import (
    EsExecNameServiceOperationComponent,
)
from backend.flow.utils.es.es_act_payload import EsActPayload
from backend.flow.utils.es.es_context_dataclass import EsActKwargs, EsApplyContext
from backend.flow.utils.extension_manage import BigdataManagerKwargs
from backend.flow.utils.mysql.mysql_act_dataclass import P2PFileKwargs
from backend.flow.utils.name_service.name_service_dataclass import ActKwargs, TransDataKwargs

logger = logging.getLogger("flow")


class EsApplyFlow(EsFlow):
    """
    构建ES申请流程
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        :param root_id: 任务流程定义的root_id
        :param data: 单据传递过来的参数列表，字典格式
        """
        super().__init__(root_id, data)
        self.cluster_alias = data.get("cluster_alias")

        # 是否在集群部署成功后创建CLB/北极星，默认False
        self.apply_clb = data.get("apply_clb", False)
        self.apply_polaris = data.get("apply_polaris", False)
        if not isinstance(self.apply_clb, bool) or not isinstance(self.apply_polaris, bool):
            raise ValueError(_("apply_clb/apply_polaris 参数必须为bool类型"))

        # 定义证书文件分发的目标路径
        self.cer_target_path = "/data/install/"
        self.file_list = ["/tmp/es_cerfiles.tar.gz"]

        # 从dbconfig获取安装的插件列表
        try:
            plugin_list = DBConfigApi.query_conf_item(
                {
                    "bk_biz_id": str(self.bk_biz_id),
                    "level_name": LevelName.APP,
                    "level_value": str(self.bk_biz_id),
                    "conf_file": self.db_version,
                    "conf_type": ConfType.DEPLOY,
                    "namespace": NameSpaceEnum.Es,
                    "format": FormatType.MAP,
                }
            )
            # 检查返回结果是否有效
            if plugin_list and "content" in plugin_list:
                for plugin_name, flag in plugin_list["content"].items():
                    if plugin_name and flag == "ON":
                        self.plugin_list.append(plugin_name)
            else:
                logger.warning(_("dbconfig查询返回空结果或格式不正确，使用默认插件列表"))
        except Exception as e:
            logger.warning(f"dbconfig exception: {e}")

    def __get_flow_data(self) -> dict:
        flow_data = self.get_flow_base_data()
        flow_data["cluster_alias"] = self.cluster_alias
        flow_data["nodes"] = self.nodes
        return flow_data

    def deploy_es_flow(self):
        """
        定义部署ES集群
        :return:
        """

        es_deploy_data = self.__get_flow_data()
        es_pipeline = Builder(root_id=self.root_id, data=es_deploy_data)

        trans_files = GetFileList(db_type=DBType.Es)

        act_kwargs = EsActKwargs(bk_cloud_id=self.bk_cloud_id)
        act_kwargs.set_trans_data_dataclass = EsApplyContext.__name__
        act_kwargs.file_list = trans_files.es_apply(db_version=self.db_version, install_plugin_list=self.plugin_list)
        es_pipeline.add_act(
            act_name=_("获取集群部署配置"), act_component_code=GetEsActPayloadComponent.code, kwargs=asdict(act_kwargs)
        )

        # 获取机器资源
        es_pipeline.add_act(
            act_name=_("获取机器信息"), act_component_code=GetEsResourceComponent.code, kwargs=asdict(act_kwargs)
        )

        # 增加机器初始化子流程
        all_new_ips = get_all_node_ips_in_ticket(data=es_deploy_data)
        common_sub_flow = new_machine_common_sub_flow(
            uid=self.uid, root_id=self.root_id, bk_cloud_id=self.bk_cloud_id, new_ips=all_new_ips
        )
        if common_sub_flow:
            es_pipeline.add_sub_pipeline(sub_flow=common_sub_flow)

        act_kwargs.exec_ip = get_all_node_ips_in_ticket(data=es_deploy_data)
        es_pipeline.add_act(
            act_name=_("下发ES介质"), act_component_code=TransFileComponent.code, kwargs=asdict(act_kwargs)
        )

        # 生成证书
        cer_ip = get_node_in_ticket_preferred_hot(data=es_deploy_data)
        act_kwargs.exec_ip = cer_ip
        act_kwargs.get_es_payload_func = EsActPayload.get_gen_certificate_payload.__name__
        es_pipeline.add_act(
            act_name=_("生成证书"), act_component_code=ExecuteEsActuatorScriptComponent.code, kwargs=asdict(act_kwargs)
        )

        # 分发证书
        es_pipeline.add_act(
            act_name=_("分发证书"),
            act_component_code=MySQLTransFileComponent.code,
            kwargs=asdict(
                P2PFileKwargs(
                    bk_cloud_id=self.bk_cloud_id,
                    file_list=self.file_list,
                    file_target_path=self.cer_target_path,
                    source_ip_list=[cer_ip],
                    exec_ip=get_all_node_ips_in_ticket(data=es_deploy_data),
                )
            ),
        )

        sub_pipelines = []
        for role, role_nodes in self.nodes.items():
            for node in role_nodes:
                sub_pipeline = SubBuilder(root_id=self.root_id, data=self.__get_flow_data())
                ip = node["ip"]
                instance_num = node.get("instance_num", ES_DEFAULT_INSTANCE_NUM)
                # 节点初始化
                act_kwargs.get_es_payload_func = EsActPayload.get_sys_init_payload.__name__
                act_kwargs.exec_ip = ip
                sub_pipeline.add_act(
                    act_name=_("节点初始化-{}").format(node["ip"]),
                    act_component_code=ExecuteEsActuatorScriptComponent.code,
                    kwargs=asdict(act_kwargs),
                )

                # 解压缩
                act_kwargs.get_es_payload_func = EsActPayload.get_decompress_es_pkg_payload.__name__
                act_kwargs.exec_ip = ip
                sub_pipeline.add_act(
                    act_name=_("解压缩介质包-{}").format(ip),
                    act_component_code=ExecuteEsActuatorScriptComponent.code,
                    kwargs=asdict(act_kwargs),
                )

                # 安装supervisor
                act_kwargs.get_es_payload_func = EsActPayload.get_install_supervisor_payload.__name__
                act_kwargs.exec_ip = ip
                sub_pipeline.add_act(
                    act_name=_("安装supervisor-{}").format(ip),
                    act_component_code=ExecuteEsActuatorScriptComponent.code,
                    kwargs=asdict(act_kwargs),
                )

                # 安装ElasticSearch
                act_kwargs.get_es_payload_func = EsActPayload.get_install_es_payload.__name__
                act_kwargs.exec_ip = ip
                act_kwargs.es_role = role
                act_kwargs.instance_num = instance_num
                # 写入亲合度相关信息，目前为园区、机房、机架三个维度
                act_kwargs.sub_zone_id = node.get("sub_zone_id") or ""
                act_kwargs.idc_id = node.get("idc_id") or 0
                act_kwargs.rack_id = node.get("rack_id") or ""
                # 安装插件列表
                act_kwargs.plugin_list = self.plugin_list

                sub_pipeline.add_act(
                    act_name=_("安装ES {}-{}节点").format(role, ip),
                    act_component_code=ExecuteEsActuatorScriptComponent.code,
                    kwargs=asdict(act_kwargs),
                )

                sub_pipelines.append(sub_pipeline.build_sub_process(sub_name=_("安装ES {}-{}子流程").format(role, ip)))
        # 并发执行所有子流程
        es_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)

        # 初始化鉴权插件
        act_kwargs.get_es_payload_func = EsActPayload.get_init_grant_payload.__name__
        act_kwargs.exec_ip = get_node_in_ticket_preferred_hot(data=es_deploy_data)
        es_pipeline.add_act(
            act_name=_("初始化鉴权插件"), act_component_code=ExecuteEsActuatorScriptComponent.code, kwargs=asdict(act_kwargs)
        )

        # 安装kibana
        kibana_ip = get_node_in_ticket_preferred_hot(data=es_deploy_data)
        act_kwargs.get_es_payload_func = EsActPayload.get_install_kibana_payload.__name__
        act_kwargs.exec_ip = kibana_ip
        es_pipeline.add_act(
            act_name=_("安装kibana"), act_component_code=ExecuteEsActuatorScriptComponent.code, kwargs=asdict(act_kwargs)
        )

        # 插入kibana实例信息
        manager_kwargs = BigdataManagerKwargs(
            manager_op_type=ManagerOpType.CREATE,
            db_type=DBType.Es,
            service_type=ManagerServiceType.KIBANA,
            manager_ip=kibana_ip,
            manager_port=ManagerDefaultPort.KIBANA,
        )
        es_pipeline.add_act(
            act_name=_("插入kibana实例信息"),
            act_component_code=BigdataManagerComponent.code,
            kwargs={**asdict(act_kwargs), **asdict(manager_kwargs)},
        )

        # 回写DBConfig
        es_pipeline.add_act(
            act_name=_("回写集群配置信息"), act_component_code=WriteBackEsConfigComponent.code, kwargs=asdict(act_kwargs)
        )

        sub_pipeline_access = get_access_manager_atom_job(root_id=self.root_id, ticket_data=es_deploy_data)
        if sub_pipeline_access:
            es_pipeline.add_sub_pipeline(sub_pipeline_access)

        # 添加到DBMeta并转模块
        es_pipeline.add_act(
            act_name=_("添加到DBMeta"), act_component_code=EsMetaComponent.code, kwargs=asdict(act_kwargs)
        )

        # 集群元数据落库后，根据单据传参决定是否创建CLB/北极星。
        # 此处不在编排构建阶段查询cluster_id，而是通过bk_biz_id+domain_name在节点执行态实时解析
        clb_polaris_sub_pipelines = []
        if self.apply_clb or self.apply_polaris:
            ns_kwargs = ActKwargs()
            ns_kwargs.set_trans_data_dataclass = TransDataKwargs.__name__
            ns_kwargs.bk_biz_id = self.bk_biz_id
            ns_kwargs.domain_name = self.domain
            ns_kwargs.creator = self.created_by

        if self.apply_clb:
            clb_sub_pipeline = SubBuilder(root_id=self.root_id, data=es_deploy_data)
            ns_kwargs.name_service_operation_type = "create_clb"
            clb_sub_pipeline.add_act(
                act_name=_("创建clb"),
                act_component_code=EsExecNameServiceOperationComponent.code,
                kwargs=asdict(ns_kwargs),
            )
            ns_kwargs.name_service_operation_type = "add_clb_info_to_meta"
            clb_sub_pipeline.add_act(
                act_name=_("clb信息写入meta"),
                act_component_code=EsExecNameServiceOperationComponent.code,
                kwargs=asdict(ns_kwargs),
            )
            ns_kwargs.name_service_operation_type = "add_clb_domain_to_dns"
            clb_sub_pipeline.add_act(
                act_name=_("clb域名添加到dns，clb域名信息写入meta"),
                act_component_code=EsExecNameServiceOperationComponent.code,
                kwargs=asdict(ns_kwargs),
            )
            clb_polaris_sub_pipelines.append(clb_sub_pipeline.build_sub_process(sub_name=_("创建clb")))

        if self.apply_polaris:
            polaris_sub_pipeline = SubBuilder(root_id=self.root_id, data=es_deploy_data)
            ns_kwargs.name_service_operation_type = "create_polaris"
            polaris_sub_pipeline.add_act(
                act_name=_("创建polaris"),
                act_component_code=EsExecNameServiceOperationComponent.code,
                kwargs=asdict(ns_kwargs),
            )
            ns_kwargs.name_service_operation_type = "add_polaris_info_to_meta"
            polaris_sub_pipeline.add_act(
                act_name=_("polaris信息写入meta"),
                act_component_code=EsExecNameServiceOperationComponent.code,
                kwargs=asdict(ns_kwargs),
            )
            clb_polaris_sub_pipelines.append(polaris_sub_pipeline.build_sub_process(sub_name=_("创建北极星")))

        if clb_polaris_sub_pipelines:
            es_pipeline.add_parallel_sub_pipeline(sub_flow_list=clb_polaris_sub_pipelines)

        # 写入集群信息摘要，供前端"执行摘要"展示
        add_es_apply_summary_output_act(
            es_pipeline=es_pipeline,
            bk_biz_id=self.bk_biz_id,
            domain_name=self.domain,
            region=self.city_code,
            version=self.db_version,
            http_port=self.http_port,
            apply_clb=self.apply_clb,
            apply_polaris=self.apply_polaris,
        )

        es_pipeline.run_pipeline()
