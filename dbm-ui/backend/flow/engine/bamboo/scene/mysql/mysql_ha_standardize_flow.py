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
from typing import Dict, List, Optional

from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.db_meta.exceptions import DBMetaException
from backend.db_meta.models import Cluster
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder, SubProcess
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.mysql.cluster_standardize_trans_module import (
    ClusterStandardizeTransModuleComponent,
)
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.utils.mysql.mysql_act_dataclass import DownloadMediaKwargs, ExecActuatorKwargs
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload

logger = logging.getLogger("flow")


class MySQLHAStandardizeFlow(object):
    def __init__(self, root_id: str, data: Optional[Dict]):
        self.root_id = root_id
        self.data = data

    def standardize(self):
        """
        self.data = {
            "uid": "20230830",
            "created_by": "xxx",
            "bk_biz_id": "11",
            "ticket_type": "MYSQL_HA_STANDARDIZE",
            "infos": {
                "cluster_ids": [1, 2, 3],
            }
        }
        增加单据临时ADMIN账号的添加和删除逻辑
        """
        cluster_objects = Cluster.objects.filter(pk__in=self.data["infos"]["cluster_ids"])
        if cluster_objects.count() != len(self.data["infos"]["cluster_ids"]):
            raise DBMetaException(
                message="input {} clusters, but found {}".format(
                    len(self.data["infos"]["cluster_ids"]), cluster_objects.count()
                )
            )

        standardize_pipe = Builder(
            root_id=self.root_id,
            data=self.data,
            need_random_pass_cluster_ids=list(set(self.data["infos"]["cluster_ids"])),
        )
        standardize_pipe.add_sub_pipeline(self._build_trans_module_sub(clusters=cluster_objects))

        standardize_pipe.add_parallel_sub_pipeline(
            sub_flow_list=[
                self._build_proxy_sub(clusters=cluster_objects),
                self._build_storage_sub(clusters=cluster_objects),
            ]
        )
        logger.info(_("构建TenDBHA集群标准化流程成功"))
        standardize_pipe.run_pipeline(is_drop_random_user=True)

    def _build_trans_module_sub(self, clusters: List[Cluster]) -> SubProcess:
        pipes = []
        for cluster in clusters:
            cluster_pipe = SubBuilder(
                root_id=self.root_id, data={**copy.deepcopy(self.data), "cluster_id": cluster.id}
            )
            cluster_pipe.add_act(
                act_name=_("模块标准化"), act_component_code=ClusterStandardizeTransModuleComponent.code, kwargs={}
            )

            pipes.append(cluster_pipe.build_sub_process(sub_name=_("{} CC 模块标准化".format(cluster.immute_domain))))

        p = SubBuilder(root_id=self.root_id, data=self.data)
        p.add_parallel_sub_pipeline(sub_flow_list=pipes)
        return p.build_sub_process(sub_name=_("CC标准化"))

    def _build_proxy_sub(self, clusters: List[Cluster]) -> SubProcess:
        ip_cluster_map = defaultdict(list)
        for cluster in clusters:
            for ins in cluster.proxyinstance_set.all():
                # 集群的 N 个接入层实例肯定在不同的 N 台机器上
                # 一个实例肯定只是一个集群的接入层
                # 所以这个列表不会有重复值
                ip_cluster_map[ins.machine.ip].append(cluster)

        pipes = []
        for ip, relate_clusters in ip_cluster_map.items():
            bk_cloud_id = relate_clusters[0].bk_cloud_id
            cluster_type = relate_clusters[0].cluster_type
            pipe = SubBuilder(root_id=self.root_id, data=self.data)

            pipe.add_act(
                act_name=_("下发MySQL周边程序介质"),
                act_component_code=TransFileComponent.code,
                kwargs=asdict(
                    DownloadMediaKwargs(
                        bk_cloud_id=bk_cloud_id,
                        exec_ip=ip,
                        file_list=GetFileList(db_type=DBType.MySQL).get_mysql_surrounding_apps_package(),
                    )
                ),
            )

            pipe.add_act(
                act_name=_("下发actuator介质"),
                act_component_code=TransFileComponent.code,
                kwargs=asdict(
                    DownloadMediaKwargs(
                        bk_cloud_id=bk_cloud_id,
                        exec_ip=ip,
                        file_list=GetFileList(db_type=DBType.MySQL).get_db_actuator_package(),
                    )
                ),
            )

            pipe.add_act(
                act_name=_("部署mysql-crond"),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(
                    ExecActuatorKwargs(
                        exec_ip=ip,
                        bk_cloud_id=bk_cloud_id,
                        get_mysql_payload_func=MysqlActPayload.get_deploy_mysql_crond_payload.__name__,
                        cluster_type=cluster_type,
                    )
                ),
            )

            pipe.add_act(
                act_name=_("部署监控程序"),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(
                    ExecActuatorKwargs(
                        exec_ip=ip,
                        bk_cloud_id=bk_cloud_id,
                        get_mysql_payload_func=MysqlActPayload.get_deploy_mysql_monitor_payload.__name__,
                        cluster_type=cluster_type,
                    )
                ),
            )

            pipes.append(
                pipe.build_sub_process(
                    sub_name=_("{} 部署dba工具".format("\n".join([ele.immute_domain for ele in relate_clusters])))
                )
            )

        p = SubBuilder(root_id=self.root_id, data=self.data)
        p.add_parallel_sub_pipeline(sub_flow_list=pipes)

        return p.build_sub_process(sub_name=_("接入层标准化"))

    def _build_storage_sub(self, clusters: List[Cluster]) -> SubProcess:
        ip_cluster_map = defaultdict(list)
        for cluster in clusters:
            for ins in cluster.storageinstance_set.all():
                ip_cluster_map[ins.machine.ip].append(cluster)

        pipes = []
        for ip, relate_clusters in ip_cluster_map.items():
            bk_cloud_id = relate_clusters[0].bk_cloud_id
            cluster_type = relate_clusters[0].cluster_type
            pipe = SubBuilder(root_id=self.root_id, data=self.data)

            pipe.add_act(
                act_name=_("下发MySQL周边程序介质"),
                act_component_code=TransFileComponent.code,
                kwargs=asdict(
                    DownloadMediaKwargs(
                        bk_cloud_id=bk_cloud_id,
                        exec_ip=ip,
                        file_list=GetFileList(db_type=DBType.MySQL).get_mysql_surrounding_apps_package(),
                    )
                ),
            )

            pipe.add_act(
                act_name=_("下发actuator介质"),
                act_component_code=TransFileComponent.code,
                kwargs=asdict(
                    DownloadMediaKwargs(
                        bk_cloud_id=bk_cloud_id,
                        exec_ip=ip,
                        file_list=GetFileList(db_type=DBType.MySQL).get_db_actuator_package(),
                    )
                ),
            )

            pipe.add_act(
                act_name=_("部署mysql-crond"),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(
                    ExecActuatorKwargs(
                        exec_ip=ip,
                        bk_cloud_id=bk_cloud_id,
                        get_mysql_payload_func=MysqlActPayload.get_deploy_mysql_crond_payload.__name__,
                        cluster_type=cluster_type,
                    )
                ),
            )

            pipe.add_act(
                act_name=_("部署监控程序"),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(
                    ExecActuatorKwargs(
                        exec_ip=ip,
                        bk_cloud_id=bk_cloud_id,
                        get_mysql_payload_func=MysqlActPayload.get_deploy_mysql_monitor_payload.__name__,
                        cluster_type=cluster_type,
                    )
                ),
            )

            pipe.add_act(
                act_name=_("部署备份程序"),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(
                    ExecActuatorKwargs(
                        exec_ip=ip,
                        bk_cloud_id=bk_cloud_id,
                        get_mysql_payload_func=MysqlActPayload.get_install_db_backup_payload.__name__,
                        cluster_type=cluster_type,
                    )
                ),
            )

            pipe.add_act(
                act_name=_("部署rotate binlog"),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(
                    ExecActuatorKwargs(
                        exec_ip=ip,
                        bk_cloud_id=bk_cloud_id,
                        get_mysql_payload_func=MysqlActPayload.get_install_mysql_rotatebinlog_payload.__name__,
                        cluster_type=cluster_type,
                    )
                ),
            )

            pipe.add_act(
                act_name=_("部署数据校验程序"),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(
                    ExecActuatorKwargs(
                        exec_ip=ip,
                        bk_cloud_id=bk_cloud_id,
                        get_mysql_payload_func=MysqlActPayload.get_install_mysql_checksum_payload.__name__,
                        cluster_type=cluster_type,
                    )
                ),
            )

            pipe.add_act(
                act_name=_("部署DBA工具箱"),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(
                    ExecActuatorKwargs(
                        bk_cloud_id=bk_cloud_id,
                        exec_ip=ip,
                        get_mysql_payload_func=MysqlActPayload.get_install_dba_toolkit_payload.__name__,
                        cluster_type=cluster_type,
                    )
                ),
            )

            pipes.append(
                pipe.build_sub_process(
                    sub_name=_("{} 部署dba工具".format("\n".join([ele.immute_domain for ele in relate_clusters])))
                )
            )

        p = SubBuilder(root_id=self.root_id, data=self.data)
        p.add_parallel_sub_pipeline(sub_flow_list=pipes)
        return p.build_sub_process(sub_name=_("存储层标准化"))
