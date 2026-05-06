"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""

import time
from dataclasses import dataclass
from typing import Dict, List

from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component

from backend.components import DRSApi
from backend.constants import IP_PORT_DIVIDER
from backend.flow.engine.bamboo.scene.common.machine_os_init import RecycleOutputContext
from backend.flow.plugins.components.collections.mysql.revoke.check_tendb_single_is_normal import (
    CheckTenDBSingleIsNormalService,
)
from backend.flow.utils.base.flow_output import FlowOutputHandler


@dataclass()
class CheckTenDBHAIsNormalKwargs:
    check_proxy_hosts: List[Dict]
    check_mysql_hosts: List[Dict]
    start_proxy_port: int
    start_mysql_port: int
    inst_num: int
    immute_domain_list: List[str]


class CheckTenDBHAIsNormalService(CheckTenDBSingleIsNormalService):
    """
    定义检查mysql主从集群是否进入DBM平台 ，并可以提供访问的过程
    这里检查节点，只针对集群部署单据终止后，进行检查的场景， 其他场景未必适合，请慎重使用
    判断添加：
    1：判断proxy实例连接是否正常
    2：判断mysql实例链接是否正常
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
        check_proxy_instance_result = True
        check_backend_instance_result = True

        # 发起机器维度的元数据检查
        self.log_info("checking db_meta ...")
        for check_host in kwargs["check_proxy_hosts"] + kwargs["check_mysql_hosts"]:
            if not self.check_db_meta_by_machine(ip=check_host["ip"], bk_cloud_id=check_host["bk_cloud_id"]):
                check_db_meta_result = False

        # 发起对dns和proxy之间的映射关系已经存在的检查
        self.log_info("checking dns ...")
        for immute_domain in kwargs["immute_domain_list"]:
            for proxy_host in kwargs["check_proxy_hosts"]:
                if not self.check_dns(
                    ip=proxy_host["ip"],
                    bk_cloud_id=proxy_host["bk_cloud_id"],
                    bk_biz_id=global_data["bk_biz_id"],
                    domain=immute_domain,
                ):
                    check_dns_result = False

        # 对proxy实例的连接性进行检查
        self.log_info("checking proxy instance ...")
        for proxy_host in kwargs["check_proxy_hosts"]:
            if not self.check_proxy_instances_by_rds(
                ip=proxy_host["ip"],
                bk_cloud_id=proxy_host["bk_cloud_id"],
                ports=[i + kwargs["start_proxy_port"] for i in range(kwargs["inst_num"])],
            ):
                check_proxy_instance_result = False

        # 对backend实例的连接性进行检查
        self.log_info("checking backend instance ...")
        for backend_host in kwargs["check_mysql_hosts"]:
            if not self.check_instances_by_rds(
                ip=backend_host["ip"],
                bk_cloud_id=backend_host["bk_cloud_id"],
                ports=[i + kwargs["start_mysql_port"] for i in range(kwargs["inst_num"])],
            ):
                check_backend_instance_result = False

        self.log_info(_("本次的机器元数据检查结果为:{}".format(check_db_meta_result)))
        self.log_info(_("本次的域名映射存在性检查结果为:{}".format(check_dns_result)))
        self.log_info(_("本次的proxy实例启动状态检查结果为:{}".format(check_proxy_instance_result)))
        self.log_info(_("本次的backend实例启动状态检查结果为:{}".format(check_backend_instance_result)))

        # 判断，如果其中一个条件不符合，则进入退回条件。
        if (
            not check_db_meta_result
            or not check_dns_result
            or not check_proxy_instance_result
            or not check_backend_instance_result
        ):
            self.log_info(
                _(
                    "本次检测到这批主机不符合预期，故进入到退回主机流程列表，准备重新清理再录入资源池:{}".format(
                        kwargs["check_proxy_hosts"] + kwargs["check_mysql_hosts"]
                    )
                )
            )
            # 加入到退回主机列表
            FlowOutputHandler(RecycleOutputContext.ToResourceSerializer).insert_data(
                global_data["job_root_id"], kwargs["check_proxy_hosts"] + kwargs["check_mysql_hosts"]
            )
            # 记录这次节点结果，传递给流程下个阶段
            data.outputs.check_result = False
        else:
            data.outputs.check_result = True

        return True

    def check_proxy_instances_by_rds(self, ip: str, bk_cloud_id: int, ports: List[int]):
        """
        通过rds服务，判断这次安装的实例进程，是否连接正常
        每个实例检查2次，如果达到2次都连接失败，则认为实例访问失败，
        """
        for port in ports:
            admin_port = port + 1000
            if not self._check_proxy_for_rds(ip=ip, bk_cloud_id=bk_cloud_id, port=admin_port):
                # 如果第一次访问实例不成功，则尝试停止3s, 重新测试一次，如果还是访问失败，则返回异常
                # 如果是多实例，如果发生一个进程连接不上，则抛异常
                time.sleep(3)
                self.log_info("check connect again...")
                if not self._check_proxy_for_rds(ip=ip, bk_cloud_id=bk_cloud_id, port=admin_port):
                    # 再次访问失败
                    return False
        return True

    def _check_proxy_for_rds(self, ip: str, bk_cloud_id: int, port: int):
        """
        通过proxy rds执行select 1指令， 验证proxy是否可访问
        @param ip: 执行ip
        @param bk_cloud_id: ip所在云区域
        @param port: 端口号
        """
        res = DRSApi.proxyrpc(
            {
                "addresses": [f"{ip}{IP_PORT_DIVIDER}{port}"],
                "cmds": ["select version;"],
                "force": False,
                "bk_cloud_id": bk_cloud_id,
            }
        )

        if res[0]["error_msg"]:
            # 执行失败
            self.log_error(f"check proxy instance[{ip}{IP_PORT_DIVIDER}{port}] error:[{res[0]['error_msg']}]")
            return False

        self.log_info(f"check proxy instance[{ip}{IP_PORT_DIVIDER}{port}] successfully")
        return True


class CheckTenDBHAIsNormalComponent(Component):
    name = __name__
    code = "check_tendb_ha_is_normal"
    bound_service = CheckTenDBHAIsNormalService
    kwargs = CheckTenDBHAIsNormalKwargs
