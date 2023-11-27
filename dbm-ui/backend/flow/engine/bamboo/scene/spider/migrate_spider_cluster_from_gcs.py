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

from django.core.exceptions import ObjectDoesNotExist
from django.utils.crypto import get_random_string
from django.utils.translation import ugettext as _

from backend import env
from backend.configuration.constants import DBType
from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.enums import ClusterType, TenDBClusterSpiderRole
from backend.db_meta.exceptions import ClusterNotExistException
from backend.db_meta.models import Cluster, StorageInstanceTuple
from backend.flow.consts import TDBCTL_USER
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.mysql.common.common_sub_flow import (
    build_repl_by_manual_input_sub_flow,
    build_surrounding_apps_sub_flow,
)
from backend.flow.engine.bamboo.scene.spider.common.common_sub_flow import (
    build_apps_for_spider_sub_flow,
    build_ctl_replication_with_gtid,
)
from backend.flow.plugins.components.collections.mysql.dns_manage import MySQLDnsManageComponent
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptComponent
from backend.flow.plugins.components.collections.mysql.mysql_os_init import MySQLOsInitComponent, SysInitComponent
from backend.flow.plugins.components.collections.mysql.trans_flies import TransFileComponent
from backend.flow.plugins.components.collections.spider.add_system_user_in_cluster import (
    AddSystemUserInClusterComponent,
)
from backend.flow.plugins.components.collections.spider.spider_db_meta import SpiderDBMetaComponent
from backend.flow.utils.mysql.mysql_act_dataclass import (
    AddSpiderSystemUserKwargs,
    CreateDnsKwargs,
    DBMetaOPKwargs,
    DownloadMediaKwargs,
    ExecActuatorKwargs,
)
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload
from backend.flow.utils.mysql.mysql_context_dataclass import SpiderApplyManualContext
from backend.flow.utils.spider.spider_act_dataclass import InstanceTuple, ShardInfo
from backend.flow.utils.spider.spider_db_meta import SpiderDBMeta


class MigrateClusterFromGcsFlow(object):
    """
    migrate cluster from gcs
    1、追加部署中控
    2、授权
    3、导入表结构
    4、检查表结构一致性
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递参数
        {
            "bk_cloud_id": <bk_cloud_id>,
            "infos":[
                {
                     "cluster_id": cluster_id
                }
            ]
        }
        """
        self.root_id = root_id
        self.data = data
        self.cluster_type = ClusterType.TenDBCluster
        self.bk_cloud_id = 0
        if self.data.get("bk_cloud_id"):
            self.bk_cloud_id = self.data["bk_cloud_id"]

        # 一个单据自动生成同一份随机密码, 中控实例需要，不需要内部来维护,每次部署随机生成一次
        self.tdbctl_pass = get_random_string(length=10)

    def run(self):
        # 初始化流程
        pipeline = Builder(root_id=self.root_id, data=self.data)
        migrate_pipeline = SubBuilder(root_id=self.root_id, data=self.data)
        # 拼接执行原子任务活动节点需要的通用的私有参数结构体, 减少代码重复率，但引用时注意内部参数值传递的问题
        exec_act_kwargs = ExecActuatorKwargs(
            bk_cloud_id=int(self.data["bk_cloud_id"]),
            cluster_type=ClusterType.TenDBCluster,
        )

        for job in self.data["infos"]:
            try:
                cluster_obj = Cluster.objects.get(
                    pk=job["cluster_id"], bk_biz_id=self.data["bk_biz_id"], cluster_type=self.cluster_type
                )
            except ObjectDoesNotExist:
                raise ClusterNotExistException(cluster_type=self.cluster_type, cluster_id=job["cluster_id"])

            ctl_objs = cluster_obj.proxyinstance_set.all()
            master_spider_ips = [c.machine.ip for c in ctl_objs]
            logging.info("master_spider_ips: %s" % [c.machine.ip for c in ctl_objs])
            if len(master_spider_ips) < 2:
                raise Exception(_("至少需要2个以上的spider节点"))
            ctl_master = master_spider_ips[0]
            ctl_slaves = master_spider_ips[1:]
            ctl_port = ctl_objs[0].port + 1000
            # 给spider节点下发tdbctl 介质 0
            migrate_pipeline.add_act(
                act_name=_("下发tdbCtl介质包"),
                act_component_code=TransFileComponent.code,
                kwargs=asdict(
                    DownloadMediaKwargs(
                        bk_cloud_id=self.bk_cloud_id,
                        exec_ip=master_spider_ips,
                        file_list=GetFileList(db_type=DBType.MySQL).tdbctl_install_package(),
                    )
                ),
            )

            acts_list = []
            # 这里中控实例安装和spider机器复用的
            for ctl_ip in master_spider_ips:
                exec_act_kwargs.exec_ip = ctl_ip
                exec_act_kwargs.cluster = {
                    "immutable_domain": cluster_obj.immute_domain,
                    "ctl_port": ctl_port,
                    "ctl_charset": job["ctl_charset"],
                }
                exec_act_kwargs.get_mysql_payload_func = MysqlActPayload.get_append_deploy_ctl_payload.__name__
                acts_list.append(
                    {
                        "act_name": _("安装Tdbctl集群中控实例"),
                        "act_component_code": ExecuteDBActuatorScriptComponent.code,
                        "kwargs": asdict(exec_act_kwargs),
                    }
                )

            migrate_pipeline.add_parallel_acts(acts_list=acts_list)
            # 构建spider中控集群
            migrate_pipeline.add_sub_pipeline(
                sub_flow=build_ctl_replication_with_gtid(
                    root_id=self.root_id,
                    parent_global_data=self.data,
                    bk_cloud_id=int(self.data["bk_cloud_id"]),
                    ctl_primary=f"{ctl_master}{IP_PORT_DIVIDER}{ctl_port}",
                    ctl_secondary_list=[{"ip": value} for value in ctl_slaves],
                )
            )
            # 内部集群节点之间授权
            migrate_pipeline.add_act(
                act_name=_("集群内部节点间授权"),
                act_component_code=AddSystemUserInClusterComponent.code,
                kwargs=asdict(
                    AddSpiderSystemUserKwargs(ctl_master_ip=ctl_master, user=TDBCTL_USER, passwd=self.tdbctl_pass)
                ),
            )

        # 运行流程
        pipeline.add_sub_pipeline(
            sub_flow=migrate_pipeline.build_sub_process(sub_name=_("{}集群中控追加部署").format(cluster_obj.name))
        )
        pipeline.run_pipeline()
