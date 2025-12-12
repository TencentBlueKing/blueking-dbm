"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from dataclasses import asdict
from typing import Dict, List

from bamboo_engine.builder import SubProcess
from django.utils.translation import gettext as _

from backend.configuration.constants import DBType
from backend.db_services.ipchooser.constants import BkOsTypeCode
from backend.flow.engine.bamboo.scene.common.builder import Builder, Conditions, SubBuilder
from backend.flow.engine.revoke.base import RevokeFlowBase
from backend.flow.plugins.components.collections.common.exec_clear_machine import ClearMachineScriptComponent
from backend.flow.plugins.components.collections.common.pause import PauseComponent
from backend.flow.plugins.components.collections.mysql.dns_manage import MySQLDnsManageComponent
from backend.flow.plugins.components.collections.mysql.mysql_db_meta import MySQLDBMetaComponent
from backend.flow.plugins.components.collections.mysql.revoke.check_tendb_cluster_is_normal import (
    CheckTenDBClusterIsNormalComponent,
)
from backend.flow.plugins.components.collections.spider.spider_db_meta import SpiderDBMetaComponent
from backend.flow.utils.mysql.mysql_act_dataclass import DBMetaOPKwargs, RecycleDnsRecordKwargs
from backend.flow.utils.mysql.mysql_db_meta import MySQLDBMeta
from backend.flow.utils.spider.spider_db_meta import SpiderDBMeta


class TenDBClusterApplyRevokeFlow(RevokeFlowBase):
    """
    构建mysql主从部署对应的主机退回流程，单节点部署流程：TenDBClusterApplyFlow().deploy_flow()
    触发时机：单据点击终止后
    处理流程，计算哪个机器可以回收，哪些不可以
    判断进程是否正常起来（这里只判断proxy进程和mysqld进程）
    判断域名是否加上
    判断元数据是否加上
    """

    # 声明类变量，定义条件分支的结果判断的输出名称
    conditions_var_name = "check_result"
    start_mysql_port = 20000

    def revoke_flow(self):
        # 获取所有的remote ip
        mysql_ip_list = []
        for i in self.data["remote_group"]:
            mysql_ip_list.append(i["master"])
            if i["slave"]:
                # 异形架构会不传
                mysql_ip_list.append(i["slave"])

        revoke_pipeline = Builder(root_id=self.root_id, data=self.data)

        source_act = revoke_pipeline.add_act(
            act_name=_("计算退回主机"),
            act_component_code=CheckTenDBClusterIsNormalComponent.code,
            kwargs=asdict(
                CheckTenDBClusterIsNormalComponent.kwargs(
                    check_spider_hosts=self.data["spider_ip_list"],
                    check_remote_hosts=mysql_ip_list,
                    spider_port=self.data["spider_port"],
                    inst_num=self.data["remote_shard_num"],
                    immute_domain=self.data["immutable_domain"],
                )
            ),
            extend=False,
        )
        # 检查到CheckTenDBClusterIsNormalComponent节点的conditions_var_name输出结果，走哪个分支
        conditions = [
            Conditions(
                act_object=self.clean_machine_sub_flow(
                    domain_name=self.data["immutable_domain"],
                    spider_hosts=self.data["spider_ip_list"],
                    mysql_hosts=mysql_ip_list,
                    spider_port=self.data["spider_port"],
                    bk_cloud_id=mysql_ip_list[0]["bk_cloud_id"],
                ),
                express="==False",
            )
        ]

        revoke_pipeline.add_conditional_subs(
            source_act=source_act,
            conditions=conditions,
            name=_("判断是否回收主机"),
            conditions_param=self.conditions_var_name,
        )

        revoke_pipeline.run_pipeline()

    def clean_machine_sub_flow(
        self, domain_name: str, spider_hosts: List[Dict], spider_port: int, mysql_hosts: List[Dict], bk_cloud_id: int
    ) -> SubProcess:
        """
        做回收主机的子流程
        1: 尝试清理机器和集群所有的元数据
        2: 清理域名信息
        3：清理机器的相关mysql信息
        @param domain_list:
        @param host: 这次部署的主机信息结构体，结构体包括 ip、bk_cloud_id 等等
        @param ports: 这次部署的端口号
        """

        global_data = {
            "uid": self.data["uid"],
            "bk_biz_id": int(self.data["bk_biz_id"]),
            "db_type": DBType.MySQL.value,
            "os_type": BkOsTypeCode.LINUX.value,
            "clear_hosts": spider_hosts + mysql_hosts,
        }

        sub_pipeline = SubBuilder(root_id=self.root_id, data=global_data)

        sub_pipeline.add_act(act_name=_("人工确认"), act_component_code=PauseComponent.code, kwargs={})

        sub_pipeline.add_act(
            act_name=_("回收域名映射"),
            act_component_code=MySQLDnsManageComponent.code,
            kwargs=asdict(
                RecycleDnsRecordKwargs(
                    dns_op_exec_port=spider_port,
                    exec_ip=[h["ip"] for h in spider_hosts],
                    bk_cloud_id=bk_cloud_id,
                )
            ),
        )

        sub_pipeline.add_act(
            act_name=_("清理集群元信息[{}]".format(domain_name)),
            act_component_code=SpiderDBMetaComponent.code,
            kwargs=asdict(
                DBMetaOPKwargs(
                    db_meta_class_func=SpiderDBMeta.cluster_destroy_for_revoke.__name__,
                    cluster={"domain": domain_name, "bk_biz_id": int(self.data["bk_biz_id"])},
                )
            ),
        )

        clear_machine_db_meta_acts_list = []
        for host in spider_hosts + mysql_hosts:
            clear_machine_db_meta_acts_list.append(
                {
                    "act_name": _("清理机器[{}]的元信息".format(host["ip"])),
                    "act_component_code": MySQLDBMetaComponent.code,
                    "kwargs": asdict(
                        DBMetaOPKwargs(
                            db_meta_class_func=MySQLDBMeta.clear_machines.__name__,
                        )
                    ),
                }
            )
        sub_pipeline.add_parallel_acts(acts_list=clear_machine_db_meta_acts_list)

        sub_pipeline.add_act(
            act_name=_("清理机器相关的安装信息"),
            act_component_code=ClearMachineScriptComponent.code,
            kwargs={"exec_ips": spider_hosts + mysql_hosts},
        )

        return sub_pipeline.build_sub_process(sub_name=_("回收机器和集群相关信息"))
