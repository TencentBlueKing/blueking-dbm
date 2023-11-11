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
import logging
from collections import defaultdict
from dataclasses import asdict
from typing import Dict, Optional

from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.db_meta.enums import ClusterType
from backend.flow.consts import DBA_ROOT_USER
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.common.pause import PauseComponent
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.mysql_ha_import_metadata import MySQLHAImportMetadataComponent
from backend.flow.plugins.components.collections.mysql.mysql_ha_modify_cluster_phase import (
    MySQLHAModifyClusterPhaseComponent,
)
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.utils.mysql.mysql_act_dataclass import DownloadMediaKwargs, ExecActuatorKwargs
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload
from backend.flow.utils.mysql.mysql_context_dataclass import MySQLHAImportMetadataContext

logger = logging.getLogger("flow")


class TenDBHAMetadataImportFlow(object):
    def __init__(self, root_id: str, data: Optional[Dict]):
        self.root_id = root_id
        self.data = data

    def import_meta(self):
        """
        很多检查都前置了, 能走到这里可以认为基本没啥问题
        尝试无脑导入
        """
        import_pipe = Builder(root_id=self.root_id, data=self.data)

        import_pipe_sub = SubBuilder(root_id=self.root_id, data=self.data)

        import_pipe_sub.add_act(
            act_name=_("写入元数据"),
            act_component_code=MySQLHAImportMetadataComponent.code,
            kwargs={**copy.deepcopy(self.data)},
        )

        proxy_machines = []
        for cluster_json in self.data["json_content"]:
            proxy_machines += [ele["ip"] for ele in cluster_json["proxies"]]

        import_pipe_sub.add_act(act_name=_("人工确认"), act_component_code=PauseComponent.code, kwargs={})

        import_pipe_sub.add_act(
            act_name=_("修改集群状态"), act_component_code=MySQLHAModifyClusterPhaseComponent.code, kwargs={}
        )

        storage_machine_ports = defaultdict(list)
        version = ""
        for cluster_json in self.data["json_content"]:
            version = cluster_json["version"]  # 取了多次问题不大, 这个单据的前置检查要求版本一致
            storage_machine_ports[cluster_json["master"]["ip"]].append(cluster_json["master"]["port"])
            for slave in cluster_json["slaves"]:
                storage_machine_ports[slave["ip"]].append(slave["port"])

        version = "MySQL-" + ".".join(version.split(".")[:2])  # 改写成配置系统的形式

        adopt_pipes = []
        for ip, ports in storage_machine_ports.items():
            adopt_storage_pipe = SubBuilder(root_id=self.root_id, data=self.data)

            adopt_storage_pipe.add_act(
                act_name=_("下发actuator介质"),
                act_component_code=TransFileComponent.code,
                kwargs=asdict(
                    DownloadMediaKwargs(
                        bk_cloud_id=0,
                        exec_ip=ip,
                        file_list=GetFileList(db_type=DBType.MySQL).get_db_actuator_package(),
                    )
                ),
            )

            adopt_storage_pipe.add_act(
                act_name=_("接管存储层 {}".format(ip)),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(
                    ExecActuatorKwargs(
                        exec_ip=ip,
                        run_as_system_user=DBA_ROOT_USER,
                        cluster_type=ClusterType.TenDBHA.value,
                        cluster={"ports": ports, "version": version},
                        bk_cloud_id=0,  # 国内迁移写死
                        get_mysql_payload_func=MysqlActPayload.get_adopt_tendbha_storage_payload.__name__,
                    )
                ),
            )

            adopt_pipes.append(adopt_storage_pipe.build_sub_process(sub_name=_("接管存储层 {}".format(ip))))

        # import_pipe_sub.add_parallel_sub_pipeline(adopt_pipes)

        # adopt_proxy_pipes = []
        for ip in proxy_machines:
            adopt_proxy_pipe = SubBuilder(root_id=self.root_id, data=self.data)

            adopt_proxy_pipe.add_act(
                act_name=_("下发actuator介质"),
                act_component_code=TransFileComponent.code,
                kwargs=asdict(
                    DownloadMediaKwargs(
                        bk_cloud_id=0,
                        exec_ip=ip,
                        file_list=GetFileList(db_type=DBType.MySQL).get_db_actuator_package(),
                    )
                ),
            )

            adopt_proxy_pipe.add_act(
                act_name=_("接管接入层 {}".format(ip)),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(
                    ExecActuatorKwargs(
                        exec_ip=ip,
                        run_as_system_user=DBA_ROOT_USER,
                        bk_cloud_id=0,
                        get_mysql_payload_func=MysqlActPayload.get_adopt_tendbha_proxy_payload.__name__,
                    )
                ),
            )

            adopt_pipes.append(adopt_proxy_pipe.build_sub_process(sub_name=_("接管接入层 {}".format(ip))))

        import_pipe_sub.add_parallel_sub_pipeline(adopt_pipes)

        import_pipe.add_sub_pipeline(sub_flow=import_pipe_sub.build_sub_process(sub_name=_("TenDBHA 元数据导入")))

        logger.info(_("构建TenDBHA元数据导入流程成功"))
        import_pipe.run_pipeline(init_trans_data_class=MySQLHAImportMetadataContext())
