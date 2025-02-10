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
from backend.db_meta.enums import ClusterType
from backend.db_meta.exceptions import DBMetaException
from backend.db_meta.models import Cluster, StorageInstance
from backend.db_package.models import Package
from backend.flow.consts import DBA_ROOT_USER, DEPENDENCIES_PLUGINS, MediumEnum
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder, SubProcess
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.common.download_backup_client import DownloadBackupClientComponent
from backend.flow.plugins.components.collections.common.install_nodeman_plugin import (
    InstallNodemanPluginServiceComponent,
)
from backend.flow.plugins.components.collections.mysql.cluster_standardize_trans_module import (
    ClusterStandardizeTransModuleComponent,
)
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.mysql_cluster_instantiate_config import (
    MySQLClusterInstantiateConfigComponent,
)
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.utils.common_act_dataclass import DownloadBackupClientKwargs, InstallNodemanPluginKwargs
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
        cluster_ids = self.data["infos"]["cluster_ids"]
        bk_biz_id = self.data["bk_biz_id"]

        cluster_objects = Cluster.objects.filter(
            pk__in=cluster_ids, bk_biz_id=bk_biz_id, cluster_type=ClusterType.TenDBHA.value
        ).prefetch_related(
            "proxyinstance_set", "storageinstance_set", "proxyinstance_set__machine", "storageinstance_set__machine"
        )
        if cluster_objects.count() != len(cluster_ids):
            raise DBMetaException(
                message="input {} clusters, but found {}".format(len(cluster_ids), cluster_objects.count())
            )

        standardize_pipe = Builder(
            root_id=self.root_id,
            data=self.data,
            need_random_pass_cluster_ids=list(set(self.data["infos"]["cluster_ids"])),
        )

        standardize_pipe.add_sub_pipeline(self._build_trans_module_sub(clusters=cluster_objects))

        standardize_pipe.add_sub_pipeline(self._build_instantiate_mysql_config_sub(clusters=cluster_objects))

        # 为了代码方便这里稍微特殊点
        # 这两个字典的 key 是 ip 地址
        # value 是 bk cloud id
        # 省得要搞字典去重
        proxy_ips = {}
        storage_ips = {}
        # 为了方便下发文件, ip 还要按 bk_cloud_id 分组
        ip_group_by_cloud = defaultdict(list)
        for cluster_obj in cluster_objects:
            for ins in cluster_obj.proxyinstance_set.all():
                ip = ins.machine.ip
                bk_cloud_id = ins.machine.bk_cloud_id
                proxy_ips[ip] = bk_cloud_id
                ip_group_by_cloud[bk_cloud_id].append(ip)

            for ins in cluster_obj.storageinstance_set.all():
                ip = ins.machine.ip
                bk_cloud_id = ins.machine.bk_cloud_id
                storage_ips[ip] = bk_cloud_id
                ip_group_by_cloud[bk_cloud_id].append(ip)

        # 按 bk_cloud_id 批量下发文件
        standardize_pipe.add_sub_pipeline(self._trans_file(ips_group=ip_group_by_cloud))

        standardize_pipe.add_parallel_sub_pipeline(
            sub_flow_list=[
                self._build_proxy_sub(ips=proxy_ips),
                self._build_storage_sub(ips=storage_ips),
            ]
        )

        logger.info(_("构建TenDBHA集群标准化流程成功"))
        standardize_pipe.run_pipeline(is_drop_random_user=True)

    def _trans_file(self, ips_group: Dict) -> SubProcess:
        trans_file_pipes = []
        for bk_cloud_id, ips in ips_group.items():
            unique_ips = list(set(ips))

            cloud_trans_file_pipe = SubBuilder(root_id=self.root_id, data=self.data)

            cloud_trans_file_pipe.add_act(
                act_name=_("下发MySQL周边程序介质"),
                act_component_code=TransFileComponent.code,
                kwargs=asdict(
                    DownloadMediaKwargs(
                        bk_cloud_id=bk_cloud_id,
                        exec_ip=unique_ips,
                        file_list=GetFileList(db_type=DBType.MySQL).get_mysql_surrounding_apps_package(),
                    )
                ),
            )
            cloud_trans_file_pipe.add_act(
                act_name=_("下发db-actuator介质"),
                act_component_code=TransFileComponent.code,
                kwargs=asdict(
                    DownloadMediaKwargs(
                        bk_cloud_id=bk_cloud_id,
                        exec_ip=unique_ips,
                        file_list=GetFileList(db_type=DBType.MySQL).get_db_actuator_package(),
                    )
                ),
            )

            for plugin_name in DEPENDENCIES_PLUGINS:
                cloud_trans_file_pipe.add_act(
                    act_name=_("安装{}插件".format(plugin_name)),
                    act_component_code=InstallNodemanPluginServiceComponent.code,
                    kwargs=asdict(
                        InstallNodemanPluginKwargs(ips=unique_ips, plugin_name=plugin_name, bk_cloud_id=bk_cloud_id)
                    ),
                )

            cloud_trans_file_pipe.add_act(
                act_name=_("安装backup-client工具"),
                act_component_code=DownloadBackupClientComponent.code,
                kwargs=asdict(
                    DownloadBackupClientKwargs(
                        bk_cloud_id=bk_cloud_id,
                        bk_biz_id=self.data["bk_biz_id"],
                        download_host_list=unique_ips,
                    )
                ),
            )

            trans_file_pipes.append(
                cloud_trans_file_pipe.build_sub_process(sub_name=_("cloud {} 下发文件".format(bk_cloud_id)))
            )

        p = SubBuilder(root_id=self.root_id, data=self.data)
        p.add_parallel_sub_pipeline(sub_flow_list=trans_file_pipes)
        return p.build_sub_process(sub_name=_("下发文件"))

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

    def _build_instantiate_mysql_config_sub(self, clusters: List[Cluster]) -> SubProcess:
        pipes = []
        for cluster in clusters:
            cluster_pipe = SubBuilder(
                root_id=self.root_id, data={**copy.deepcopy(self.data), "cluster_id": cluster.id}
            )
            cluster_pipe.add_act(
                act_name=_("实例化配置"), act_component_code=MySQLClusterInstantiateConfigComponent.code, kwargs={}
            )
            pipes.append(cluster_pipe.build_sub_process(sub_name=_("实例化 {} 配置".format(cluster.immute_domain))))

        p = SubBuilder(root_id=self.root_id, data=self.data)
        p.add_parallel_sub_pipeline(sub_flow_list=pipes)
        return p.build_sub_process(sub_name=_("实例化集群配置"))

    def _build_proxy_sub(self, ips: Dict) -> SubProcess:
        pipes = []
        for ip, bk_cloud_id in ips.items():
            single_pipe = SubBuilder(root_id=self.root_id, data=self.data)

            single_pipe.add_act(
                act_name=_("标准化proxy"),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(
                    ExecActuatorKwargs(
                        exec_ip=ip,
                        run_as_system_user=DBA_ROOT_USER,
                        get_mysql_payload_func=MysqlActPayload.get_standardize_tendbha_proxy_payload.__name__,
                        bk_cloud_id=bk_cloud_id,
                    )
                ),
            )

            single_pipe.add_act(
                act_name=_("部署mysql-crond"),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(
                    ExecActuatorKwargs(
                        exec_ip=ip,
                        bk_cloud_id=bk_cloud_id,
                        get_mysql_payload_func=MysqlActPayload.get_deploy_mysql_crond_payload.__name__,
                        cluster_type=ClusterType.TenDBHA.value,
                    )
                ),
            )

            single_pipe.add_act(
                act_name=_("部署监控程序"),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(
                    ExecActuatorKwargs(
                        exec_ip=ip,
                        bk_cloud_id=bk_cloud_id,
                        get_mysql_payload_func=MysqlActPayload.get_deploy_mysql_monitor_payload.__name__,
                        cluster={"cluster_ids": self.data["infos"]["cluster_ids"]},
                        cluster_type=ClusterType.TenDBHA.value,
                    )
                ),
            )

            pipes.append(single_pipe.build_sub_process(sub_name=_("{} 部署dba工具".format(ip))))

        p = SubBuilder(root_id=self.root_id, data=self.data)
        p.add_parallel_sub_pipeline(sub_flow_list=pipes)

        return p.build_sub_process(sub_name=_("接入层标准化"))

    def _build_storage_sub(self, ips: Dict) -> SubProcess:
        pipes = []
        for ip, bk_cloud_id in ips.items():
            single_pipe = SubBuilder(root_id=self.root_id, data=self.data)

            # 同一机器所有集群的 major version 应该是一样的
            major_version = Cluster.objects.filter(storageinstance__machine__ip=ip).first().major_version
            mysql_pkg = Package.get_latest_package(version=major_version, pkg_type=MediumEnum.MySQL)

            ports = StorageInstance.objects.filter(machine__ip=ip, bk_biz_id=self.data["bk_biz_id"]).values_list(
                "port", flat=True
            )

            single_pipe.add_act(
                act_name=_("实例标准化"),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(
                    ExecActuatorKwargs(
                        exec_ip=ip,
                        run_as_system_user=DBA_ROOT_USER,
                        cluster_type=ClusterType.TenDBHA.value,
                        cluster={
                            "ports": list(ports),
                            "mysql_pkg": {"name": mysql_pkg.name, "md5": mysql_pkg.md5},
                            "version": major_version,
                        },
                        bk_cloud_id=bk_cloud_id,
                        get_mysql_payload_func=MysqlActPayload.get_standardize_mysql_instance_payload.__name__,
                    )
                ),
            )

            single_pipe.add_act(
                act_name=_("部署mysql-crond"),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(
                    ExecActuatorKwargs(
                        exec_ip=ip,
                        bk_cloud_id=bk_cloud_id,
                        get_mysql_payload_func=MysqlActPayload.get_deploy_mysql_crond_payload.__name__,
                        cluster_type=ClusterType.TenDBHA.value,
                    )
                ),
            )

            single_pipe.add_act(
                act_name=_("部署监控程序"),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(
                    ExecActuatorKwargs(
                        exec_ip=ip,
                        bk_cloud_id=bk_cloud_id,
                        get_mysql_payload_func=MysqlActPayload.get_deploy_mysql_monitor_payload.__name__,
                        cluster={"cluster_ids": self.data["infos"]["cluster_ids"]},
                        cluster_type=ClusterType.TenDBHA.value,
                    )
                ),
            )

            single_pipe.add_act(
                act_name=_("部署备份程序"),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(
                    ExecActuatorKwargs(
                        exec_ip=ip,
                        bk_cloud_id=bk_cloud_id,
                        get_mysql_payload_func=MysqlActPayload.get_install_db_backup_payload.__name__,
                        cluster_type=ClusterType.TenDBHA.value,
                    )
                ),
            )

            single_pipe.add_act(
                act_name=_("部署rotate binlog"),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(
                    ExecActuatorKwargs(
                        exec_ip=ip,
                        bk_cloud_id=bk_cloud_id,
                        get_mysql_payload_func=MysqlActPayload.get_install_mysql_rotatebinlog_payload.__name__,
                        cluster_type=ClusterType.TenDBHA.value,
                    )
                ),
            )

            single_pipe.add_act(
                act_name=_("部署数据校验程序"),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(
                    ExecActuatorKwargs(
                        exec_ip=ip,
                        bk_cloud_id=bk_cloud_id,
                        get_mysql_payload_func=MysqlActPayload.get_install_mysql_checksum_payload.__name__,
                        cluster_type=ClusterType.TenDBHA.value,
                    )
                ),
            )

            single_pipe.add_act(
                act_name=_("部署DBA工具箱"),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(
                    ExecActuatorKwargs(
                        bk_cloud_id=bk_cloud_id,
                        exec_ip=ip,
                        get_mysql_payload_func=MysqlActPayload.get_install_dba_toolkit_payload.__name__,
                        cluster_type=ClusterType.TenDBHA.value,
                    )
                ),
            )

            pipes.append(single_pipe.build_sub_process(sub_name=_("{} 标准化".format(ip))))

        p = SubBuilder(root_id=self.root_id, data=self.data)
        p.add_parallel_sub_pipeline(sub_flow_list=pipes)
        return p.build_sub_process(sub_name=_("存储层标准化"))
