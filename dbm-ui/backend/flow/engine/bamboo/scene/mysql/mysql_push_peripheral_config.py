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

import collections
import logging
from dataclasses import asdict
from typing import Dict, Optional

from django.db.models import Q
from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.db_meta.enums import AccessLayer, ClusterType
from backend.db_meta.exceptions import DBMetaException
from backend.db_meta.models import Cluster, Machine
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.utils.mysql.mysql_act_dataclass import DownloadMediaKwargs, ExecActuatorKwargs
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload

logger = logging.getLogger("flow")


class MySQLPushPeripheralConfigFlow(object):
    def __init__(self, root_id: str, data: Optional[Dict]):
        self.root_id = root_id
        self.data = data

    def push_config(self):
        """
        self.data = {
            "uid": 12345,
            "created_by": "xxx",
            "bk_biz_id": 12345,
            "ticket_type": "MYSQL_PUSH_PERIPHERAL_CONFIG",
            "cluster_ids": [1, 2, 3],
        }
        """
        cluster_ids = list(set(self.data["cluster_ids"]))
        bk_biz_id = self.data["bk_biz_id"]

        cluster_objects = Cluster.objects.filter(
            pk__in=cluster_ids,
            bk_biz_id=bk_biz_id,
            cluster_type__in=[ClusterType.TenDBSingle, ClusterType.TenDBHA, ClusterType.TenDBCluster],
        )
        if cluster_objects.count() != len(cluster_ids):
            raise DBMetaException(
                message="input {} clusters, but found {}".format(len(cluster_ids), cluster_objects.count())
            )

        mysql_ips_by_cloud = collections.defaultdict(list)
        ips_by_cloud = collections.defaultdict(list)
        for cluster_object in cluster_objects:
            ips_by_cloud[cluster_object.bk_cloud_id].extend(
                list(cluster_object.storageinstance_set.values_list("machine__ip", flat=True))
            )
            ips_by_cloud[cluster_object.bk_cloud_id].extend(
                list(cluster_object.proxyinstance_set.values_list("machine__ip", flat=True))
            )

            mysql_ips_by_cloud[cluster_object.bk_cloud_id].extend(
                list(cluster_object.storageinstance_set.values_list("machine__ip", flat=True))
            )
            if cluster_object.cluster_type == ClusterType.TenDBCluster:
                # tendbcluster 接入层按存储处理
                mysql_ips_by_cloud[cluster_object.bk_cloud_id].extend(
                    list(cluster_object.proxyinstance_set.values_list("machine__ip", flat=True))
                )

        trans_file_acts = []
        push_mysql_crond_config_acts = []
        for k, v in ips_by_cloud.items():
            trans_file_acts.append(
                {
                    "act_name": _("下发actuator介质 云区域ID: {}".format(k)),
                    "act_component_code": TransFileComponent.code,
                    "kwargs": asdict(
                        DownloadMediaKwargs(
                            bk_cloud_id=k,
                            exec_ip=list(set(v)),
                            file_list=GetFileList(db_type=DBType.MySQL).get_db_actuator_package(),
                        )
                    ),
                }
            )
            trans_file_acts.append(
                {
                    "act_name": _("下发MySQL周边程序介质"),
                    "act_component_code": TransFileComponent.code,
                    "kwargs": asdict(
                        DownloadMediaKwargs(
                            bk_cloud_id=k,
                            exec_ip=list(set(v)),
                            file_list=GetFileList(db_type=DBType.MySQL).get_mysql_surrounding_apps_package(),
                        )
                    ),
                }
            )

            for ip in list(set(v)):
                push_mysql_crond_config_acts.append(
                    {
                        "act_name": _("下发mysql-crond配置 {}".format(ip)),
                        "act_component_code": ExecuteDBActuatorScriptComponent.code,
                        "kwargs": asdict(
                            ExecActuatorKwargs(
                                bk_cloud_id=k,
                                exec_ip=ip,
                                get_mysql_payload_func=MysqlActPayload.push_mysql_crond_config_payload.__name__,
                            )
                        ),
                    }
                )

        push_mysql_rotatebinlog_config_acts = []
        for k, v in mysql_ips_by_cloud.items():
            for ip in list(set(v)):
                push_mysql_rotatebinlog_config_acts.append(
                    {
                        "act_name": _("下发MySQL rotatebinlog配置"),
                        "act_component_code": ExecuteDBActuatorScriptComponent.code,
                        "kwargs": asdict(
                            ExecActuatorKwargs(
                                bk_cloud_id=k,
                                exec_ip=ip,
                                cluster_type=Cluster.objects.filter(
                                    Q(storageinstance__machine__ip=ip) | Q(proxyinstance__machine__ip=ip)
                                )
                                .first()
                                .cluster_type,
                                get_mysql_payload_func=MysqlActPayload.push_mysql_rotatebinlog_config_payload.__name__,
                            )
                        ),
                    }
                )

        pipeline = Builder(root_id=self.root_id, data=self.data, need_random_pass_cluster_ids=cluster_ids)
        push_config_pipeline = SubBuilder(root_id=self.root_id, data=self.data)

        push_config_pipeline.add_parallel_acts(acts_list=trans_file_acts)
        push_config_pipeline.add_parallel_acts(acts_list=push_mysql_crond_config_acts)
        push_config_pipeline.add_parallel_acts(acts_list=push_mysql_rotatebinlog_config_acts)

        cluster_pipes = []
        for cluster_obj in cluster_objects:
            cluster_pipe = self.__foo(cluster_obj)
            cluster_pipes.append(cluster_pipe)

        push_config_pipeline.add_parallel_sub_pipeline(sub_flow_list=cluster_pipes)
        pipeline.add_sub_pipeline(sub_flow=push_config_pipeline.build_sub_process(sub_name=_("配置推送")))
        logger.info(_("构建配置推送流程完成"))
        pipeline.run_pipeline(is_drop_random_user=True)

    def __foo(self, cluster_obj: Cluster):
        proxy_ip_ports = collections.defaultdict(list)
        backend_ip_ports = collections.defaultdict(list)

        for ins in cluster_obj.proxyinstance_set.all():
            proxy_ip_ports[ins.machine.ip].append(ins.port)

        for ins in cluster_obj.storageinstance_set.all():
            backend_ip_ports[ins.machine.ip].append(ins.port)

        push_mysql_monitor_config_acts = []
        push_mysql_checksum_config_acts = []
        push_dbbackup_config_acts = []

        for ip, ports in proxy_ip_ports.items():
            push_mysql_monitor_config_acts.append(
                {
                    "act_name": _("{}下发mysql-monitor配置".format(ip)),
                    "act_component_code": ExecuteDBActuatorScriptComponent.code,
                    "kwargs": asdict(
                        ExecActuatorKwargs(
                            bk_cloud_id=cluster_obj.bk_cloud_id,
                            exec_ip=ip,
                            cluster={
                                "ports": ports,
                                "access_layer": AccessLayer.PROXY.value,
                                "machine_type": Machine.objects.get(ip=ip).machine_type,
                                "cluster_id": cluster_obj.id,
                                "immute_domain": cluster_obj.immute_domain,
                                "db_module_id": cluster_obj.db_module_id,
                            },
                            get_mysql_payload_func=MysqlActPayload.push_mysql_monitor_config_payload.__name__,
                        )
                    ),
                }
            )
            if cluster_obj.cluster_type == ClusterType.TenDBCluster.value:
                push_dbbackup_config_acts.append(
                    {
                        "act_name": _("{}下发备份配置".format(ip)),
                        "act_component_code": ExecuteDBActuatorScriptComponent.code,
                        "kwargs": asdict(
                            ExecActuatorKwargs(
                                bk_cloud_id=cluster_obj.bk_cloud_id,
                                exec_ip=ip,
                                cluster={
                                    "ports": ports,
                                    "machine_type": Machine.objects.get(ip=ip).machine_type,
                                    "cluster_id": cluster_obj.id,
                                    "immute_domain": cluster_obj.immute_domain,
                                    "db_module_id": cluster_obj.db_module_id,
                                    "cluster_type": cluster_obj.cluster_type,
                                },
                                get_mysql_payload_func=MysqlActPayload.push_dbbackup_config_payload.__name__,
                            )
                        ),
                    }
                )

        for ip, ports in backend_ip_ports.items():
            push_mysql_checksum_config_acts.append(
                {
                    "act_name": _("{}下发mysql-monitor配置".format(ip)),
                    "act_component_code": ExecuteDBActuatorScriptComponent.code,
                    "kwargs": asdict(
                        ExecActuatorKwargs(
                            bk_cloud_id=cluster_obj.bk_cloud_id,
                            exec_ip=ip,
                            cluster={
                                "ports": ports,
                                "access_layer": AccessLayer.STORAGE.value,
                                "machine_type": Machine.objects.get(ip=ip).machine_type,
                                "cluster_id": cluster_obj.id,
                                "immute_domain": cluster_obj.immute_domain,
                                "db_module_id": cluster_obj.db_module_id,
                            },
                            get_mysql_payload_func=MysqlActPayload.push_mysql_monitor_config_payload.__name__,
                        )
                    ),
                }
            )
            push_mysql_checksum_config_acts.append(
                {
                    "act_name": _("{}下发mysql-table-checksum配置".format(ip)),
                    "act_component_code": ExecuteDBActuatorScriptComponent.code,
                    "kwargs": asdict(
                        ExecActuatorKwargs(
                            bk_cloud_id=cluster_obj.bk_cloud_id,
                            exec_ip=ip,
                            cluster={
                                "ports": ports,
                                # "access_layer": AccessLayer.STORAGE.value,
                                "machine_type": Machine.objects.get(ip=ip).machine_type,
                                "cluster_id": cluster_obj.id,
                                "immute_domain": cluster_obj.immute_domain,
                                "db_module_id": cluster_obj.db_module_id,
                            },
                            get_mysql_payload_func=MysqlActPayload.push_mysql_checksum_config_payload.__name__,
                        )
                    ),
                }
            )
            push_dbbackup_config_acts.append(
                {
                    "act_name": _("{}下发备份配置".format(ip)),
                    "act_component_code": ExecuteDBActuatorScriptComponent.code,
                    "kwargs": asdict(
                        ExecActuatorKwargs(
                            bk_cloud_id=cluster_obj.bk_cloud_id,
                            exec_ip=ip,
                            cluster={
                                "ports": ports,
                                "machine_type": Machine.objects.get(ip=ip).machine_type,
                                "cluster_id": cluster_obj.id,
                                "immute_domain": cluster_obj.immute_domain,
                                "db_module_id": cluster_obj.db_module_id,
                                "cluster_type": cluster_obj.cluster_type,
                            },
                            get_mysql_payload_func=MysqlActPayload.push_dbbackup_config_payload.__name__,
                        )
                    ),
                }
            )

        p = SubBuilder(root_id=self.root_id, data=self.data)
        p.add_parallel_acts(acts_list=push_mysql_monitor_config_acts)
        p.add_parallel_acts(acts_list=push_mysql_checksum_config_acts)
        p.add_parallel_acts(acts_list=push_dbbackup_config_acts)

        return p.build_sub_process(sub_name=_("{} 推送周边配置".format(cluster_obj.immute_domain)))
