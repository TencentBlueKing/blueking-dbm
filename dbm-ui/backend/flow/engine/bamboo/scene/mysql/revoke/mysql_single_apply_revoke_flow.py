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
from typing import List

from bamboo_engine.builder import SubProcess
from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.db_services.ipchooser.constants import BkOsTypeCode
from backend.flow.engine.bamboo.scene.common.builder import Builder, Conditions, SubBuilder
from backend.flow.engine.revoke.base import RevokeFlowBase
from backend.flow.plugins.components.collections.common.exec_clear_machine import ClearMachineScriptComponent
from backend.flow.plugins.components.collections.mysql.dns_manage import MySQLDnsManageComponent
from backend.flow.plugins.components.collections.mysql.mysql_db_meta import MySQLDBMetaComponent
from backend.flow.plugins.components.collections.mysql.revoke.check_tendb_single_is_normal import (
    CheckTenDBSingleIsNormalComponent,
)
from backend.flow.utils.mysql.mysql_act_dataclass import DBMetaOPKwargs, RecycleDnsRecordKwargs
from backend.flow.utils.mysql.mysql_db_meta import MySQLDBMeta


class MySQLSingleApplyRevokeFlow(RevokeFlowBase):
    """
    构建mysql单节点部署对应的主机退回流程，单节点部署流程：MySQLSingleApplyFlow().deploy_flow()
    触发时机：单据点击终止后
    处理流程，计算哪个机器可以回收，哪些不可以
    判断进程是否正常起来
    判断域名是否加上
    判断元数据是否加上
    """

    # 声明类变量，定义条件分支的结果判断的输出名称
    conditions_var_name = "check_result"

    def __call__(self):
        revoke_pipeline = Builder(root_id=self.root_id, data=self.data)
        sub_flow_list = []
        for info in self.data["apply_infos"]:
            sub_flow_list.append(self.single_apply_revoke_sub_flow(info))
        revoke_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_flow_list)
        revoke_pipeline.run_pipeline()

    def single_apply_revoke_sub_flow(self, info: dict) -> SubProcess:
        """
        退回主机子流程,
        @param info：协议每一行的输入参数结构体
        """
        global_data = {
            "uid": self.data["uid"],
            "bk_biz_id": int(self.data["bk_biz_id"]),
        }

        sub_pipeline = SubBuilder(root_id=self.root_id, data=global_data)

        source_act = sub_pipeline.add_act(
            act_name=_("计算退回主机"),
            act_component_code=CheckTenDBSingleIsNormalComponent.code,
            kwargs=asdict(
                CheckTenDBSingleIsNormalComponent.kwargs(
                    check_host=info["new_ip"],
                    start_mysql_port=self.data["start_mysql_port"],
                    inst_num=self.data["inst_num"],
                    immute_domain_list=[i["master"] for i in info["clusters"]],
                )
            ),
            extend=False,
        )
        # 检查到CheckTenDBSingleIsNormalComponent节点的conditions_var_name输出结果，走哪个分支
        conditions = [
            Conditions(
                act_object=self.clean_mysql_machine_sub_flow(
                    domain_list=[i["master"] for i in info["clusters"]],
                    host=info["new_ip"],
                    ports=[i + self.data["start_mysql_port"] for i in range(self.data["inst_num"])],
                ),
                express="==False",
            )
        ]

        sub_pipeline.add_conditional_subs(
            source_act=source_act,
            conditions=conditions,
            name=_("判断是否回收主机"),
            conditions_param=self.conditions_var_name,
        )

        return sub_pipeline.build_sub_process(sub_name=_("计算回收主机ip[{}]").format(info["new_ip"]["ip"]))

    def clean_mysql_machine_sub_flow(self, domain_list: List[str], host: dict, ports: List[int]) -> SubProcess:
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
            "clear_hosts": [host],
        }

        sub_pipeline = SubBuilder(root_id=self.root_id, data=global_data)

        recycle_dns_acts_list = []
        for port in ports:
            recycle_dns_acts_list.append(
                {
                    "act_name": _("回收域名映射"),
                    "act_component_code": MySQLDnsManageComponent.code,
                    "kwargs": asdict(
                        RecycleDnsRecordKwargs(
                            dns_op_exec_port=port,
                            exec_ip=host["ip"],
                            bk_cloud_id=host["bk_cloud_id"],
                        )
                    ),
                }
            )
        sub_pipeline.add_parallel_acts(acts_list=recycle_dns_acts_list)

        clean_db_meta_acts_list = []
        for domain in domain_list:
            clean_db_meta_acts_list.append(
                {
                    "act_name": _("清理集群元信息[{}]".format(domain)),
                    "act_component_code": MySQLDBMetaComponent.code,
                    "kwargs": asdict(
                        DBMetaOPKwargs(
                            db_meta_class_func=MySQLDBMeta.mysql_single_destroy_for_revoke.__name__,
                            cluster={"domain": domain, "bk_biz_id": int(self.data["bk_biz_id"])},
                        )
                    ),
                }
            )
        sub_pipeline.add_parallel_acts(acts_list=clean_db_meta_acts_list)

        sub_pipeline.add_act(
            act_name=_("清理机器[{}]的元信息".format(host["ip"])),
            act_component_code=MySQLDBMetaComponent.code,
            kwargs=asdict(
                DBMetaOPKwargs(
                    db_meta_class_func=MySQLDBMeta.clear_machines.__name__,
                )
            ),
        )

        sub_pipeline.add_act(
            act_name=_("清理机器[{}]".format(host["ip"])),
            act_component_code=ClearMachineScriptComponent.code,
            kwargs={"exec_ips": [host]},
        )

        return sub_pipeline.build_sub_process(sub_name=_("回收机器和集群相关信息"))
