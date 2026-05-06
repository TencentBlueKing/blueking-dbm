"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""

from dataclasses import dataclass
from typing import Dict, List

from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component

from backend.flow.engine.bamboo.scene.common.machine_os_init import RecycleOutputContext
from backend.flow.plugins.components.collections.mysql.revoke.check_tendb_single_is_normal import (
    CheckTenDBSingleIsNormalService,
)
from backend.flow.utils.base.flow_output import FlowOutputHandler


@dataclass()
class CheckTenDBClusterIsNormalKwargs:
    check_spider_hosts: List[Dict]
    check_remote_hosts: List[Dict]
    spider_port: int
    inst_num: int
    immute_domain: str
    start_mysql_port: int = 20000


class CheckTenDBClusterIsNormalService(CheckTenDBSingleIsNormalService):
    """
    定义检查TenDBCluster集群是否进入DBM平台 ，并可以提供访问的过程
    这里检查节点，只针对集群部署单据终止后，进行检查的场景， 其他场景未必适合，请慎重使用
    判断添加：
    1：判断spider实例连接是否正常
    2：判断remote实例链接是否正常
    3：判断实例对应的域名关系是否提供
    4：判断集群元数据是否有写入（由于多实例部署单据，写入元数据的绑定一个原子任务，
    如果检查到其中一个元数据没有写入，则可以认为机器所在集群信息没有写入
    ）
    判断逻辑：
    如果上面条件其中一个不满足，在机器都进入退回回收过程。
    """

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        global_data = data.get_one_of_inputs("global_data")
        check_db_meta_result = True
        check_dns_result = True
        check_spider_instance_result = True
        check_remote_instance_result = True

        # 发起机器维度的元数据检查
        self.log_info("checking db_meta ...")
        for check_host in kwargs["check_spider_hosts"] + kwargs["check_remote_hosts"]:
            if not self.check_db_meta_by_machine(ip=check_host["ip"], bk_cloud_id=check_host["bk_cloud_id"]):
                check_db_meta_result = False

        # 发起对dns和spider之间的映射关系已经存在的检查
        self.log_info("checking dns ...")
        for spider_host in kwargs["check_spider_hosts"]:
            if not self.check_dns(
                ip=spider_host["ip"],
                bk_cloud_id=spider_host["bk_cloud_id"],
                bk_biz_id=global_data["bk_biz_id"],
                domain=kwargs["immute_domain"],
            ):
                check_dns_result = False

        # 对proxy实例的连接性进行检查
        self.log_info("checking spider instance ...")
        for spider_host in kwargs["check_spider_hosts"]:
            if not self.check_instances_by_rds(
                ip=spider_host["ip"],
                bk_cloud_id=spider_host["bk_cloud_id"],
                ports=[kwargs["spider_port"]],
            ):
                check_spider_instance_result = False

        # 对backend实例的连接性进行检查
        self.log_info("checking remote instance ...")
        for remote_host in kwargs["check_remote_hosts"]:
            if not self.check_instances_by_rds(
                ip=remote_host["ip"],
                bk_cloud_id=remote_host["bk_cloud_id"],
                ports=[i + kwargs["start_mysql_port"] for i in range(kwargs["inst_num"])],
            ):
                check_remote_instance_result = False

        self.log_info(_("本次的机器元数据检查结果为:{}".format(check_db_meta_result)))
        self.log_info(_("本次的域名映射存在性检查结果为:{}".format(check_dns_result)))
        self.log_info(_("本次的spider实例启动状态检查结果为:{}".format(check_spider_instance_result)))
        self.log_info(_("本次的remote实例启动状态检查结果为:{}".format(check_remote_instance_result)))

        # 判断，如果其中一个条件不符合，则进入退回条件。
        if (
            not check_db_meta_result
            or not check_dns_result
            or not check_spider_instance_result
            or not check_remote_instance_result
        ):
            self.log_info(
                _(
                    "本次检测到这批主机不符合预期，故进入到退回主机流程列表，准备重新清理再录入资源池:{}".format(
                        kwargs["check_spider_hosts"] + kwargs["check_remote_hosts"]
                    )
                )
            )
            # 加入到退回主机列表
            FlowOutputHandler(RecycleOutputContext.ToResourceSerializer).insert_data(
                global_data["job_root_id"], kwargs["check_spider_hosts"] + kwargs["check_remote_hosts"]
            )
            # 记录这次节点结果，传递给流程下个阶段
            data.outputs.check_result = False
        else:
            data.outputs.check_result = True

        return True


class CheckTenDBClusterIsNormalComponent(Component):
    name = __name__
    code = "check_tendb_cluster_is_normal"
    bound_service = CheckTenDBClusterIsNormalService
    kwargs = CheckTenDBClusterIsNormalKwargs
