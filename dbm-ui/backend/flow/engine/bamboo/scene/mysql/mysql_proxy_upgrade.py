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

from backend.configuration.constants import DBType
from backend.db_meta.exceptions import DBMetaException
from backend.db_meta.models import Cluster, ProxyInstance
from backend.db_package.models import Package
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.common.pause import PauseComponent
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.mysql_db_meta import MySQLDBMetaComponent
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.utils.mysql.mysql_act_dataclass import DBMetaOPKwargs, DownloadMediaKwargs, ExecActuatorKwargs
from backend.flow.utils.mysql.mysql_db_meta import MySQLDBMeta
from backend.flow.utils.mysql.mysql_version_parse import get_sub_version_by_pkg_name, proxy_version_parse
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
                new_proxy_version:"",
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
        self.bk_cloud_id = data["bk_cloud_id"]
        self.upgrade_cluster_list = data["infos"]

    def upgrade_mysql_proxy_flow(self):
        proxy_upgrade_pipeline = Builder(root_id=self.root_id, data=self.data)
        sub_pipelines = []
        # 声明子流程
        for upgrade_info in self.upgrade_cluster_list:
            cluster_ids = upgrade_info["cluster_ids"]
            pkg_id = upgrade_info["pkg_id"]
            proxy_pkg = Package.objects.get(id=pkg_id)
            logger.info("param pkg_id:{},get the pkg name: {}".format(pkg_id, proxy_pkg.name))
            new_proxy_version_num = proxy_version_parse(proxy_pkg.name)
            clusters = Cluster.objects.filter(id__in=cluster_ids)
            proxies = ProxyInstance.objects.filter(cluster__in=clusters)
            if len(proxies) <= 0:
                raise DBMetaException(message=_("根据cluster ids:{}法找到对应的proxy实例").format(cluster_ids))

            sub_flow_context = copy.deepcopy(self.data)
            sub_pipeline = SubBuilder(root_id=self.root_id, data=copy.deepcopy(sub_flow_context))
            proxy_ports = []
            proxy_ip_list = []

            for proxy_instance in proxies:
                current_version = proxy_version_parse(proxy_instance.version)
                if current_version >= new_proxy_version_num:
                    logger.error(
                        "the upgrade version {} needs to be larger than the current verion {}".format(
                            new_proxy_version_num, current_version
                        )
                    )
                    raise DBMetaException(message=_("待升级版本大于等于新版本，请确认升级的版本"))
                proxy_ports.append(proxy_instance.port)
                proxy_ip_list.append(proxy_instance.machine.ip)

            for proxy_ip in proxy_ip_list:
                sub_pipeline.add_sub_pipeline(
                    sub_flow=self.upgrade_mysql_proxy_subflow(
                        bk_cloud_id=self.bk_cloud_id,
                        ip=proxy_ip,
                        pkg_id=pkg_id,
                        proxy_version=get_sub_version_by_pkg_name(proxy_pkg.name),
                        proxy_ports=proxy_ports,
                    )
                )
                sub_pipeline.add_act(act_name=_("人工确认"), act_component_code=PauseComponent.code, kwargs={})

            sub_pipelines.append(sub_pipeline.build_sub_process(sub_name=_("本地升级proxy版本")))
        proxy_upgrade_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        proxy_upgrade_pipeline.run_pipeline()
        return

    def upgrade_mysql_proxy_subflow(
        self,
        ip: str,
        bk_cloud_id: int,
        pkg_id: int,
        proxy_version: str,
        proxy_ports: list = None,
    ):
        """
        定义upgrade mysql proxy 的flow
        """
        sub_pipeline = SubBuilder(root_id=self.root_id, data=self.data)

        sub_pipeline.add_act(
            act_name=_("下发升级的安装包"),
            act_component_code=TransFileComponent.code,
            kwargs=asdict(
                DownloadMediaKwargs(
                    bk_cloud_id=bk_cloud_id,
                    exec_ip=ip,
                    file_list=GetFileList(db_type=DBType.MySQL).mysql_proxy_upgrade_package(pkg_id=pkg_id),
                )
            ),
        )

        cluster = {"proxy_ports": proxy_ports, "pkg_id": pkg_id}
        exec_act_kwargs = ExecActuatorKwargs(cluster=cluster, bk_cloud_id=bk_cloud_id)
        exec_act_kwargs.exec_ip = ip
        exec_act_kwargs.get_mysql_payload_func = ProxyActPayload.get_proxy_upgrade_payload.__name__
        # 执行本地升级
        sub_pipeline.add_act(
            act_name=_("执行本地升级"),
            act_component_code=ExecuteDBActuatorScriptComponent.code,
            kwargs=asdict(exec_act_kwargs),
        )
        # 更新proxy instance version 信息
        sub_pipeline.add_act(
            act_name=_("更新proxy version meta信息"),
            act_component_code=MySQLDBMetaComponent.code,
            kwargs=asdict(
                DBMetaOPKwargs(
                    db_meta_class_func=MySQLDBMeta.update_proxy_instance_version.__name__,
                    cluster={"proxy_ip": ip, "version": proxy_version},
                )
            ),
        )
        return sub_pipeline.build_sub_process(sub_name=_("proxy实例升级"))
