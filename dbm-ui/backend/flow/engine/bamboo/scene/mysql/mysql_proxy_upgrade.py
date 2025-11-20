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
from typing import Dict, List, Optional

from django.utils.translation import gettext as _

from backend.configuration.constants import DBType
from backend.db_meta.enums import InstanceStatus
from backend.db_meta.enums.instance_phase import InstancePhase
from backend.db_meta.models import Cluster, ProxyInstance
from backend.db_package.models import Package
from backend.flow.consts import DnsOpType
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.entrys_manager import BuildEntrysManageSubflow
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.mysql.common.common_sub_flow import check_sub_flow
from backend.flow.plugins.components.collections.common.pause import PauseComponent
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.mysql_db_meta import MySQLDBMetaComponent
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.utils.mysql.mysql_act_dataclass import DBMetaOPKwargs, DownloadMediaKwargs, ExecActuatorKwargs
from backend.flow.utils.mysql.mysql_db_meta import MySQLDBMeta
from backend.flow.utils.mysql.mysql_version_parse import get_sub_version_by_pkg_name
from backend.flow.utils.mysql.proxy_act_payload import ProxyActPayload

logger = logging.getLogger("flow")


class MySQLProxyLocalUpgradeFlow(object):
    """
    mysql proxy 本地升级场景
    {
        bk_biz_id: 0,
        bk_cloud_id: 0,
        infos:[
            {
                cluster_ids:[],
                new_proxy_version:""
            }
        ]
    }
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递参数
        """
        self.root_id = root_id
        self.data = data
        self.uid = data["uid"]
        self.upgrade_cluster_list = data["infos"]
        self.force_upgrade = data.get("force", True)
        self.is_check_process = data.get("is_check_process", True)

    def upgrade_mysql_proxy_flow(self):
        proxy_upgrade_pipeline = Builder(root_id=self.root_id, data=self.data)
        sub_pipelines = []
        # 统一下发文件
        # 声明子流程
        for upgrade_info in self.upgrade_cluster_list:
            # Ensure deterministic order of cluster processing
            cluster_ids = sorted(upgrade_info["cluster_ids"])
            pkg_id = upgrade_info["pkg_id"]
            proxy_pkg = Package.objects.get(id=pkg_id)
            logger.info("param pkg_id:{}, get the pkg name: {}".format(pkg_id, proxy_pkg.name))
            clusters = Cluster.objects.filter(id__in=cluster_ids)
            sub_process_name = _("{} 升级").format(",".join([c.immute_domain for c in clusters]))
            proxies = ProxyInstance.objects.filter(cluster__in=clusters)
            bk_cloud_id = clusters[0].bk_cloud_id
            sub_flow_context = copy.deepcopy(self.data)
            sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(sub_flow_context))
            proxy_ips = []
            # 收集proxy实例的端口和IP信息
            for proxy_instance in proxies:
                proxy_ips.append(proxy_instance.machine.ip)
            proxy_ips = list(set(proxy_ips))
            # 切换前做预检测
            check_db_connect_sub_flow_list = []
            for cluster_id in cluster_ids:
                cluster_obj = Cluster.objects.get(id=cluster_id)
                ps = ProxyInstance.objects.filter(cluster=cluster_obj)
                proxy_ins = []
                for p in ps:
                    admin_port = p.port + 1000
                    proxy_ins.append(f"{p.machine.ip}:{admin_port}")
                sub_build = check_sub_flow(
                    uid=self.uid,
                    root_id=self.root_id,
                    cluster=cluster_obj,
                    is_check_client_conn=self.is_check_process,
                    is_proxy=True,
                    check_client_conn_inst=proxy_ins,
                )
                if sub_build:
                    check_db_connect_sub_flow_list.append(sub_build)
            if len(check_db_connect_sub_flow_list) > 0:
                sub_pipeline.add_parallel_sub_pipeline(check_db_connect_sub_flow_list)
            # 提前下发文件
            sub_pipeline.add_act(
                act_name=_("下发升级的安装包"),
                act_component_code=TransFileComponent.code,
                kwargs=asdict(
                    DownloadMediaKwargs(
                        bk_cloud_id=bk_cloud_id,
                        exec_ip=proxy_ips,
                        file_list=GetFileList(db_type=DBType.MySQL).mysql_proxy_upgrade_package(pkg_id=pkg_id),
                    )
                ),
            )
            for index, proxy_ip in enumerate(proxy_ips):
                sub_pipeline.add_sub_pipeline(
                    sub_flow=self.upgrade_mysql_proxy_subflow(
                        bk_cloud_id=bk_cloud_id,
                        ip=proxy_ip,
                        pkg_id=pkg_id,
                        proxy_version=get_sub_version_by_pkg_name(proxy_pkg.name),
                        cluster_ids=cluster_ids,
                        force_upgrade=True,
                    )
                )
                # 最后一个节点无需再确认
                if index < len(proxy_ips) - 1:
                    sub_pipeline.add_act(act_name=_("人工确认"), act_component_code=PauseComponent.code, kwargs={})

            sub_pipelines.append(sub_pipeline.build_sub_process(sub_name=sub_process_name))
        proxy_upgrade_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        proxy_upgrade_pipeline.run_pipeline()
        return

    def upgrade_mysql_proxy_subflow(
        self,
        ip: str,
        bk_cloud_id: int,
        pkg_id: int,
        proxy_version: str,
        cluster_ids: List[int] = None,
        force_upgrade: bool = True,
    ):
        """
        定义upgrade mysql proxy 的flow
        """
        sub_pipeline = SubBuilder(root_id=self.root_id, data=self.data)

        sub_pipeline.add_act(
            act_name=_("更新proxy instance status -> upgrade"),
            act_component_code=MySQLDBMetaComponent.code,
            kwargs=asdict(
                DBMetaOPKwargs(
                    db_meta_class_func=MySQLDBMeta.update_proxy_instance_status.__name__,
                    cluster={"proxy_ip": ip, "phase": InstancePhase.UPGRADING, "status": InstanceStatus.UPGRADING},
                )
            ),
        )
        # 解压介质，更新软连接
        exec_act_kwargs = ExecActuatorKwargs(
            cluster={
                "proxy_ports": [0, 1, 2],
                "pkg_id": pkg_id,
            },
            bk_cloud_id=bk_cloud_id,
        )

        exec_act_kwargs.exec_ip = ip
        exec_act_kwargs.get_mysql_payload_func = ProxyActPayload.get_proxy_upgrade_relink_payload.__name__
        sub_pipeline.add_act(
            act_name=_("[整机行为]替换介质软链"),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(exec_act_kwargs),
        )
        # 实例执行本地升级
        proxy_ins_sub_pipelines = []
        proxy_ports = []
        for cluster_id in cluster_ids:
            cluster = Cluster.objects.get(id=cluster_id)
            proxy_ins = ProxyInstance.objects.get(cluster=cluster, machine__ip=ip, machine__bk_cloud_id=bk_cloud_id)
            proxy_ports.append(proxy_ins.port)
            proxy_ins_sub_pipeline = SubBuilder(root_id=self.root_id, data=self.data)
            disable_entry_process = BuildEntrysManageSubflow(
                root_id=self.root_id,
                ticket_data=self.data,
                op_type=DnsOpType.DISABLE,
                param={
                    "cluster_id": cluster_id,
                    "port": proxy_ins.port,
                    "del_ips": [ip],
                },
            )
            enable_entry_process = BuildEntrysManageSubflow(
                root_id=self.root_id,
                ticket_data=self.data,
                op_type=DnsOpType.ENABLE,
                param={
                    "cluster_id": cluster_id,
                    "port": proxy_ins.port,
                    "add_ips": [ip],
                },
            )
            proxy_ins_sub_pipeline.add_sub_pipeline(sub_flow=disable_entry_process)
            exec_act_kwargs = ExecActuatorKwargs(
                cluster={"proxy_ports": [proxy_ins.port], "pkg_id": pkg_id, "force_upgrade": force_upgrade},
                bk_cloud_id=bk_cloud_id,
            )
            exec_act_kwargs.exec_ip = ip
            exec_act_kwargs.get_mysql_payload_func = ProxyActPayload.get_proxy_upgrade_payload.__name__
            proxy_ins_sub_pipeline.add_act(
                act_name=_("[{}:{}] 重启proxy,refresh backend").format(ip, proxy_ins.port),
                act_component_code=ExecuteDBActuatorScriptComponent.code,
                kwargs=asdict(exec_act_kwargs),
            )

            proxy_ins_sub_pipeline.add_act(
                act_name=_("更新proxy version meta信息"),
                act_component_code=MySQLDBMetaComponent.code,
                kwargs=asdict(
                    DBMetaOPKwargs(
                        db_meta_class_func=MySQLDBMeta.update_proxy_instance_version.__name__,
                        cluster={"proxy_ip": ip, "version": proxy_version, "port": proxy_ins.port},
                    )
                ),
            )
            proxy_ins_sub_pipeline.add_sub_pipeline(sub_flow=enable_entry_process)
            proxy_ins_sub_pipeline.add_act(
                act_name=_("更新proxy instance status -> online"),
                act_component_code=MySQLDBMetaComponent.code,
                kwargs=asdict(
                    DBMetaOPKwargs(
                        db_meta_class_func=MySQLDBMeta.update_proxy_instance_status.__name__,
                        cluster={
                            "proxy_ip": ip,
                            "phase": InstancePhase.ONLINE,
                            "status": InstanceStatus.RUNNING,
                            "port": proxy_ins.port,
                        },
                    )
                ),
            )
            proxy_ins_sub_pipelines.append(
                proxy_ins_sub_pipeline.build_sub_process(sub_name=_("{}:{}实例升级").format(ip, proxy_ins.port))
            )
        sub_pipeline.add_parallel_sub_pipeline(proxy_ins_sub_pipelines)
        return sub_pipeline.build_sub_process(
            sub_name=_("{}:[{}]proxy实例升级").format(ip, ",".join(map(str, proxy_ports)))
        )
