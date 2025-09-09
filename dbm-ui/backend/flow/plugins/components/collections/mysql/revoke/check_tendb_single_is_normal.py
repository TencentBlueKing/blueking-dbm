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
from typing import List

from pipeline.component_framework.component import Component

from backend.components import DRSApi
from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.models import Machine
from backend.flow.engine.bamboo.scene.common.machine_os_init import RecycleOutputContext
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.base.flow_output import FlowOutputHandler
from backend.flow.utils.dns_manage import DnsManage


@dataclass()
class CheckTenDBSingleIsNormalKwargs:
    check_host: dict
    start_mysql_port: int
    inst_num: int
    immute_domain_list: List[str]


class CheckTenDBSingleIsNormalService(BaseService):
    """
    定义检查mysql单节点集群是否进入大DBM平台 ，并可以提供访问的过程
    判断添加：
    1：判断实例连接是否正常
    2：判断实例对应的域名关系是否提供
    3：判断集群元数据是否有写入（由于多实例部署单据，写入元数据的绑定一个原子任务，
    如果检查到其中一个元数据没有写入，则可以认为机器所在集群信息没有写入
    ）
    判断逻辑：
    如果上面1、2、3条件不满足，在机器都进入退回回收过程。
    """

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        global_data = data.get_one_of_inputs("global_data")
        # 发起检查
        self.log_info("checking db_meta ...")
        check_db_meta_result = self.check_db_meta_by_machine(
            ip=kwargs["check_host"]["ip"], bk_cloud_id=kwargs["check_host"]["bk_cloud_id"]
        )
        self.log_info("checking dns ...")
        check_dns_result = True
        for immute_domain in kwargs["immute_domain_list"]:
            if not self.check_dns(
                ip=kwargs["check_host"]["ip"],
                bk_cloud_id=kwargs["check_host"]["bk_cloud_id"],
                bk_biz_id=global_data["bk_biz_id"],
                domain=immute_domain,
            ):
                check_dns_result = False
                break

        self.log_info("checking instance ...")
        check_instance_result = self.check_instances_by_rds(
            ip=kwargs["check_host"]["ip"],
            bk_cloud_id=kwargs["check_host"]["bk_cloud_id"],
            ports=[i + kwargs["start_mysql_port"] for i in range(kwargs["inst_num"])],
        )

        self.log_info(f"check_db_meta_result:{check_db_meta_result}")
        self.log_info(f"check_dns_result:{check_dns_result}")
        self.log_info(f"check_instance_result:{check_instance_result}")
        # 判断
        if not check_instance_result or not check_dns_result or not check_db_meta_result:
            self.log_info(f"{kwargs['check_host']['ip']} join the recycling queue because it fails the test")
            FlowOutputHandler(RecycleOutputContext.ToResourceSerializer).insert_data(
                global_data["job_root_id"], [kwargs["check_host"]]
            )
            data.outputs.check_result = False
        else:
            data.outputs.check_result = True

        return True

    def _select_1_for_rds(self, ip: str, bk_cloud_id: int, port: int):
        """
        通过rds执行select 1指令
        @param ip: 执行ip
        @param bk_cloud_id: ip所在云区域
        @param port: 端口号
        """
        res = DRSApi.rpc(
            {
                "addresses": [f"{ip}{IP_PORT_DIVIDER}{port}"],
                "cmds": ["select 1;"],
                "force": False,
                "bk_cloud_id": bk_cloud_id,
            }
        )

        if res[0]["error_msg"]:
            # 执行失败
            self.log_error(f"check instance[{ip}{IP_PORT_DIVIDER}{port}] error:[{res[0]['error_msg']}]")
            return False

        self.log_info(f"check instance[{ip}{IP_PORT_DIVIDER}{port}] successfully")
        return True

    def check_db_meta_by_machine(self, ip: str, bk_cloud_id: int):
        """
        通过机器（ip,bk_cloud_id），判断machine是否有写入元数据，如果没有数据，则认为没有写入成功
        @param ip: 测试机器ip
        @param bk_cloud_id: 测试云区域
        """
        if not Machine.objects.filter(ip=ip, bk_cloud_id=bk_cloud_id).exists():
            self.log_info(f"machine[{ip}] is not add in db_meta")
            return False

        self.log_info(f"machine[{ip}] already add in db_meta")
        return True

    def check_instances_by_rds(self, ip: str, bk_cloud_id: int, ports: List[int]):
        """
        通过rds服务，判断这次安装的实例进程，是否连接正常
        每个实例检查2次，如果达到2次都连接失败，则认为实例访问失败，
        """
        for port in ports:
            if not self._select_1_for_rds(ip=ip, bk_cloud_id=bk_cloud_id, port=port):
                # 如果第一次访问实例不成功，则尝试停止3s, 重新测试一次，如果还是访问失败，则返回异常
                # 如果是多实例，如果发生一个进程连接不上，则抛异常
                time.sleep(3)
                self.log_info("check connect again...")
                if not self._select_1_for_rds(ip=ip, bk_cloud_id=bk_cloud_id, port=port):
                    # 再次访问失败
                    return False
        return True

    def check_dns(self, ip: str, bk_cloud_id: int, domain: str, bk_biz_id: int):
        """
        检查dns域名是否有解析
        """
        dns_manage = DnsManage(bk_biz_id=bk_biz_id, bk_cloud_id=bk_cloud_id)
        dns_results = dns_manage.get_domain(domain_name=domain)
        if not dns_results:
            # 没有记录返回，则返回异常
            self.log_info(f"[{domain}] is not exists in DNS-server")
            return False

        for row in dns_results:
            if not row["ip"] == ip:
                self.log_info(f"{ip} DNS resolution already exists[{domain}]")
                return True

        self.log_error(f"{ip} DNS resolution is not exists[{domain}]")
        return False


class CheckTenDBSingleIsNormalComponent(Component):
    name = __name__
    code = "check_tendb_single_is_normal"
    bound_service = CheckTenDBSingleIsNormalService
    kwargs = CheckTenDBSingleIsNormalKwargs
