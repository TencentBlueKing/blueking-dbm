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
import copy
import logging.config
from dataclasses import asdict
from typing import Dict, Optional

from django.utils.translation import ugettext as _

from backend.components import DBConfigApi
from backend.components.dbconfig.constants import ConfType, FormatType, LevelName, ReqType
from backend.configuration.constants import DBType
from backend.flow.consts import DBA_ROOT_USER, DEPENDENCIES_PLUGINS, NameSpaceEnum
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.common.install_nodeman_plugin import (
    InstallNodemanPluginServiceComponent,
)
from backend.flow.plugins.components.collections.riak.exec_actuator_script import ExecuteRiakActuatorScriptComponent
from backend.flow.plugins.components.collections.riak.get_riak_resource import GetRiakResourceComponent
from backend.flow.plugins.components.collections.riak.riak_db_meta import RiakDBMetaComponent
from backend.flow.plugins.components.collections.riak.trans_files import TransFileComponent
from backend.flow.utils.common_act_dataclass import InstallNodemanPluginKwargs
from backend.flow.utils.riak.riak_act_dataclass import DBMetaFuncKwargs, DownloadMediaKwargs
from backend.flow.utils.riak.riak_act_payload import RiakActPayload
from backend.flow.utils.riak.riak_context_dataclass import ApplyManualContext, RiakActKwargs
from backend.flow.utils.riak.riak_db_meta import RiakDBMeta

logger = logging.getLogger("flow")


class RiakClusterMigrateFlow(object):
    """
    构建Riak集群申请流程的抽象类
    {
    "uid": "2022111212001000",
    "root_id": 123,
    "created_by": "admin",
    "bk_biz_id": 0,
    "ticket_type": "RIAK_CLUSTER_MIGRATE",
    "bk_app_abbr": "testtest",
    "ip_source": "manual_input",
    "major_version": "0-0",
    "cluster_alias": "测试集群",
    "bk_cloud_id": 0,
    "nodes": [
        {
            "ip": "127.0.0.1",
            "bk_host_id": 0
        }
    ]
    }
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递过来的参数列表，是dict格式
        """
        self.root_id = root_id
        self.data = data

    def migrate_riak_cluster_flow(self):
        """
        迁移Riak集群
        """
        riak_pipeline = Builder(root_id=self.root_id, data=self.data)
        sub_pipelines = []
        bk_cloud_id = self.data["bk_cloud_id"]
        for cluster in self.data["clusters"]:
            sub_data = copy.deepcopy(self.data)
            sub_data.pop("clusters")
            sub_pipeline = SubBuilder(root_id=self.root_id, data={**sub_data, **cluster})
            # 获取机器资源
            sub_pipeline.add_act(act_name=_("获取机器信息"), act_component_code=GetRiakResourceComponent.code, kwargs={})
            ips = [node["ip"] for node in cluster["nodes"]]
            acts_list = []
            for plugin_name in DEPENDENCIES_PLUGINS:
                acts_list.append(
                    {
                        "act_name": _("安装[{}]插件".format(plugin_name)),
                        "act_component_code": InstallNodemanPluginServiceComponent.code,
                        "kwargs": asdict(
                            InstallNodemanPluginKwargs(ips=ips, plugin_name=plugin_name, bk_cloud_id=bk_cloud_id)
                        ),
                    }
                )
            sub_pipeline.add_parallel_acts(acts_list=acts_list)

            sub_pipeline.add_act(
                act_name=_("下发actuator以及riak介质"),
                act_component_code=TransFileComponent.code,
                kwargs=asdict(
                    DownloadMediaKwargs(
                        bk_cloud_id=bk_cloud_id,
                        exec_ip=ips,
                        file_list=GetFileList(db_type=DBType.Riak).riak_install_package(self.data["db_version"]),
                    )
                ),
            )

            self._get_riak_config(cluster["domain"])

            sub_pipeline.add_act(
                act_name=_("riak修改元数据"),
                act_component_code=RiakDBMetaComponent.code,
                kwargs=asdict(
                    DBMetaFuncKwargs(
                        db_meta_class_func=RiakDBMeta.riak_cluster_apply.__name__,
                        is_update_trans_data=True,
                    )
                ),
            )

            acts_list = []
            for ip in ips:
                monitor_kwargs = RiakActKwargs(
                    exec_ip=ip,
                    bk_cloud_id=bk_cloud_id,
                    run_as_system_user=DBA_ROOT_USER,
                    get_riak_payload_func=RiakActPayload.get_install_monitor_payload.__name__,
                )
                act_info = dict()
                act_info["act_name"] = _("actuator_{}部署定时任务和riak监控".format(ip))
                act_info["act_component_code"] = ExecuteRiakActuatorScriptComponent.code
                act_info["kwargs"] = asdict(monitor_kwargs)
                acts_list.append(act_info)
            sub_pipeline.add_parallel_acts(acts_list=acts_list)
            sub_pipelines.append(sub_pipeline.build_sub_process(sub_name=_("集群[{}]的迁移任务").format(cluster["domain"])))
        riak_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        logger.info(_("构建riak集群迁移流程成功"))
        riak_pipeline.run_pipeline(init_trans_data_class=ApplyManualContext())

    def _get_riak_config(self, domain):
        # 从dbconfig获取配置信息
        version = self.data["db_version"].replace(".", "")
        DBConfigApi.get_or_generate_instance_config(
            {
                "bk_biz_id": str(self.data["bk_biz_id"]),
                "level_name": LevelName.CLUSTER,
                "level_value": domain,
                "level_info": {"module": self.data["db_module_name"]},
                "conf_file": "riak-{}".format(version),
                "conf_type": ConfType.DBCONF,
                "namespace": NameSpaceEnum.Riak,
                "format": FormatType.MAP_LEVEL,
                "method": ReqType.GENERATE_AND_PUBLISH,
            }
        )
        return
