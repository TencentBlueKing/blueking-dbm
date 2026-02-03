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
from time import sleep
from typing import List

from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component

from backend.components import DRSApi
from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.enums import InstanceStatus, TenDBClusterSpiderRole
from backend.db_meta.models import Cluster, ProxyInstance
from backend.flow.consts import TDBCTL_USER
from backend.flow.engine.bamboo.scene.spider.common.exceptions import CtlSwitchToSlaveFailedException
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.plugins.components.collections.mysql.sync_master import SyncMasterService
from backend.flow.utils.base.payload_handler import PayloadHandler
from backend.flow.utils.spider.spider_db_function import get_flush_routing_sql_for_server


class CtlSwitchToSlaveService(BaseService):
    """
    定义spider(tenDB cluster)集群的中控集群提升新主节点，适用于spider-master裁撤场合调用
    这里暂时不考虑主从互切场景，仅仅做提升主节点场景，因为互切暂时没有需求
    幂等操作内容包括: 预检测、断开同步、选择新的主节点、重新同步新主节点
    私有变量的主要结构体kwargs：
    {
        “cluster_id”: id,  待关联的集群id
        "reduce_ctl_primary": 传入的待删除的中控primary实例，格式“ip:port”
        "new_ctl_primary": 传入的待提升primary的中控实例，格式“ip:port”
    }
    """

    def _double_check_new_primary_sync(self, cluster: Cluster, reduce_ctl_primary: str, new_ctl_primary: str) -> bool:
        """
        # 再次判断新primary是否完全同步当前的primary, 如果不完全同步，循环等待60s， 直到完全同步
        """
        self.log_info(_("等待新primary[{}]完全同步当前primary[{}]".format(new_ctl_primary, reduce_ctl_primary)))
        for i in range(11):
            err_list = self._pre_sync_health_check(
                cluster=cluster,
                current_primary=reduce_ctl_primary,
                check_nodes=[new_ctl_primary],
                is_wait_sync=True,
            )
            if not err_list:
                self.log_info(_("新primary[{}]同步完成".format(new_ctl_primary)))
                return True

            self.log_warning(_("执行第{}次，数据不完全同步，等待5s后重试：{}").format(i + 1, "\n".join(err_list)))
            time.sleep(5)

        return False

    def _pre_sync_health_check(
        self, cluster: Cluster, current_primary: str, check_nodes: List[str], is_wait_sync: bool = False
    ) -> List[str]:
        """
        检查传入的节点同步关系是否健康，如果不健康则抛出异常
        @param cluster: 集群元数据
        @param current_primary: 集群的primary节点，格式ip:port
        @param check_nodes: 待检查的节点列表，格式ip:port
        @param is_wait_sync: 是否要判断到完成同步，默认不判断。
        """
        err_list = []
        self.log_info("start pre-sync-health-check")
        res = DRSApi.rpc(
            {
                "addresses": check_nodes,
                "cmds": ["show slave status"],
                "force": False,
                "bk_cloud_id": cluster.bk_cloud_id,
            }
        )
        for check_info in res:
            # 遍历检查结果，如果有异常收集，后续统一抛出异常
            if check_info["error_msg"]:
                # 如果执行命令时出现失败，退出本次检查，后续会继续执行
                err_list.append(f"check node error: {check_info['error_msg']}")
                continue

            if len(check_info["cmd_results"][0]["table_data"]) == 0:
                # 表示命令返回结果为空，则认为是同步异常
                err_list.append(f"check node error: {check_info['address']} is not sync")
                continue

            slave_status = check_info["cmd_results"][0]["table_data"][0]
            if slave_status["Slave_IO_Running"] != "Yes" or slave_status["Slave_SQL_Running"] != "Yes":
                # 表示同步线程状态不正常，则认为是同步异常
                err_list.append(
                    f"check node error: {check_info['address']} is abnormal, Slave_IO_Running: "
                    f"{slave_status['Slave_IO_Running']}, "
                    f"Slave_SQL_Running: {slave_status['Slave_SQL_Running']}"
                )
                continue
            if f"{slave_status['Master_Host']}:{slave_status['Master_Port']}" != current_primary:
                # 表示同步源，和当前集群的primary不一致，则认为是同步异常
                err_list.append(
                    f"check node error: {check_info['address']} is abnormal, "
                    f"Master_Host: {slave_status['Master_Host']},"
                    f"Master_Port: {slave_status['Master_Port']},"
                    f"current_primary: {current_primary}"
                )
                continue

            if int(slave_status["Seconds_Behind_Master"]) > 30 and not is_wait_sync:
                # 如果不是等待同步，则认为是同步异常
                # 因为大部分时间，中控集群都是静默状态，没有写入，故理论上同步延迟应该在5s以内
                # 表示同步延迟超过5s，记录异常
                err_list.append(
                    f"check node error: {check_info['address']} is abnormal,  "
                    f"The value of Seconds_Behind_Master is {slave_status['Seconds_Behind_Master']}s, "
                    f"which is greater than 30s. check"
                )
                continue

            if is_wait_sync:
                # 如果需要等待同步，则需要判断同步延迟是否0
                # 因为中控集群大部分是静默阶段，这里用简化版的判断，如果同步延迟为0，则认为是同步完成。
                # 复杂点后续可以考虑用心跳表或者GTID集合判断
                if int(slave_status["Seconds_Behind_Master"]) != 0:
                    # 表示同步延迟不为0，则认为是同步异常
                    err_list.append(f"Seconds_Behind_Master in {check_info['address']} > 0")
                    continue

        return err_list

    def _is_running_process(self, check_nodes: str, bk_cloud_id: int):
        """
        检测待回收的primary是否存在running状态的线程
        """
        check_sql = (
            f"select * from information_schema.TDBCTL_CLUSTER_PROCESSLIST where user = '{TDBCTL_USER}'"
            + " and command != 'Sleep' and info not like '%INFORMATION_SCHEMA.PROCESSLIST';"
        )
        res = DRSApi.rpc(
            {
                "addresses": [check_nodes],
                "cmds": ["set tc_admin=1", check_sql],
                "force": False,
                "bk_cloud_id": bk_cloud_id,
            }
        )
        if res[0]["error_msg"]:
            raise CtlSwitchToSlaveFailedException(
                message=_("select processlist failed: {}".format(res[0]["error_msg"]))
            )

        if res[0]["cmd_results"][1]["table_data"]:
            self.log_warning(f"There are also {res[0]['cmd_results'][1]['rows_affected']} non-sleep state threads")
            return False

        return True

    def check_node_health(self, cluster: Cluster, check_nodes: List[str]) -> List[str]:
        """
        检查tdbctl实例是否正常访问
        """
        error_nodes = []
        cmds = ["set tc_admin=0"]
        rpc_params = {
            "addresses": check_nodes,
            "cmds": cmds,
            "force": False,
            "bk_cloud_id": cluster.bk_cloud_id,
        }
        # 检测待下架的中控primary是否能连接上
        check_sql = "select 1;"
        rpc_params["cmds"] = cmds + [check_sql]
        res = DRSApi.rpc(rpc_params)
        for check_info in res:
            # 遍历检查结果，如果有异常收集，后续统一抛出异常
            if check_info["error_msg"]:
                self.log_error(f"[{check_info['address']}]check node error: {check_info['error_msg']}")
                error_nodes.append(check_info["address"])

        return error_nodes

    def _prepare_check(self, cluster: Cluster, reduce_ctl_primary: str, standby_ctl_list: List[ProxyInstance]) -> bool:
        """
        检测当前是否可以执行切换
        @param cluster: 集群元数据
        @param reduce_ctl_primary: 待下架的中控primary节点
        @param standby_ctl_list: 剩余的中控从节点
        @return: True，检查没有问题，当前primary是正常状态，走安全切换流程 ；False，检查有问题，当前primary不是正常状态，走强切流程
        如果检查存在有问题，则抛出异常，打印错误信息，代码不继续执行
        """

        # 检测待下架的中控primary是否能连接上
        if self.check_node_health(cluster=cluster, check_nodes=[reduce_ctl_primary]):
            # 任务待下架的节点已经故障，应该不做下面的处理，作为故障机处理
            return False

        # 安全切换的前置条件
        # 检测原primary节点是否正在执行中控命令
        if not self._is_running_process(check_nodes=reduce_ctl_primary, bk_cloud_id=cluster.bk_cloud_id):
            # 如果第一次检验到有running的process，则尝试等待10秒，重新检验一次，如果还存在则退出
            sleep(10)
            if not self._is_running_process(check_nodes=reduce_ctl_primary, bk_cloud_id=cluster.bk_cloud_id):
                raise CtlSwitchToSlaveFailedException(
                    message=_("After two detections, there are still non-sleep state threads in the instance")
                )

        # 判断传入的剩余中控slave（除了待剔除的节点），同步是否正常
        check_nodes = [f"{ctl.machine.ip}{IP_PORT_DIVIDER}{ctl.admin_port}" for ctl in standby_ctl_list]
        err_list = self._pre_sync_health_check(
            cluster=cluster,
            current_primary=reduce_ctl_primary,
            check_nodes=check_nodes,
        )

        if err_list:
            raise CtlSwitchToSlaveFailedException(
                message=_("pre-sync-health-check failed: {}".format("\n".join(err_list)))
            )

        self.log_info(_("预检测成功"))
        return True

    def _exec_primary(self, cluster: Cluster, reduce_ctl_primary, op_type: str = "disable"):
        """
        连接待下架的primary，操作是禁用还是启动状态
        @param cluster: 集群元数据
        @param reduce_ctl_primary: 待下架的中控primary节点
        @param op_type: 操作类型，disable 禁用，enable 启动
        @return: None
        """
        exec_cmd = "TDBCTL DISABLE PRIMARY" if op_type == "disable" else "TDBCTL ENABLE PRIMARY"

        res = DRSApi.rpc(
            {
                "addresses": [reduce_ctl_primary],
                "cmds": ["set tc_admin = 1", exec_cmd],
                "force": False,
                "bk_cloud_id": cluster.bk_cloud_id,
            }
        )
        if res[0]["error_msg"]:
            raise CtlSwitchToSlaveFailedException(
                message=_("exec {} failed: {}".format(exec_cmd, res[0]["error_msg"]))
            )
        self.log_info(f"[{reduce_ctl_primary}]exec {exec_cmd} success")
        return True

    def _stop_slave(self, cluster: Cluster, ctl_set):
        # 再分发stop slave命令
        rpc_params = {
            "addresses": [],
            "cmds": ["set tc_admin=0", "stop slave"],
            "force": False,
            "bk_cloud_id": cluster.bk_cloud_id,
        }
        for ctl in ctl_set:
            self.log_info(f"exec stop slave in instance[{ctl.machine.ip}{IP_PORT_DIVIDER}{ctl.admin_port}]")
            rpc_params["addresses"] = [f"{ctl.machine.ip}{IP_PORT_DIVIDER}{ctl.admin_port}"]
            res = DRSApi.rpc(rpc_params)

            if res[0]["error_msg"]:
                raise CtlSwitchToSlaveFailedException(
                    message=_(f"exec [{ctl.ip_port}] stop slave failed: {res[0]['error_msg']}")
                )

        return True

    def _new_master_enable_primary(
        self, cluster: Cluster, new_master: ProxyInstance, reduce_ctl_primary: str, is_force: bool = False
    ):
        """
        提升新节点作为主节点的逻辑
        @param cluster: 集群元数据
        @param new_master: 待升主的tdbctl元数据
        @param reduce_ctl_primary: 旧的tdbctl信息，格式ip:port
        @param is_force: 是否强制模式，默认不开启
        """
        enable_primary_sql = "TDBCTL ENABLE PRIMARY FORCE" if is_force else "TDBCTL ENABLE PRIMARY"
        rpc_params = {
            "addresses": [f"{new_master.machine.ip}{IP_PORT_DIVIDER}{new_master.admin_port}"],
            "cmds": [],
            "force": False,
            "bk_cloud_id": cluster.bk_cloud_id,
        }

        # 查询reduce_ctl_primary对应的server_name
        reduce_ip = reduce_ctl_primary.split(":")[0]
        reduce_port = reduce_ctl_primary.split(":")[1]
        server_name = "test_name"
        select_sql = [
            "set tc_admin = 0",
            f"select Server_name from mysql.servers where host = '{reduce_ip}' and port = {reduce_port}",
        ]
        rpc_params["cmds"] = select_sql
        res = DRSApi.rpc(rpc_params)
        if res[0]["error_msg"]:
            raise CtlSwitchToSlaveFailedException(
                message=_("select mysql.servers failed: {}".format(res[0]["error_msg"]))
            )
        if not res[0]["cmd_results"][1]["table_data"]:
            self.log_warning(f"Node [{reduce_ctl_primary}] no longer has routing information")
        else:
            server_name = res[0]["cmd_results"][1]["table_data"][0]["Server_name"]

        # 新primary需要执行reset slave, 避免提升主报错
        rpc_params["cmds"] = ["set tc_admin=0", "reset slave all;"]
        res = DRSApi.rpc(rpc_params)
        if res[0]["error_msg"]:
            raise CtlSwitchToSlaveFailedException(
                message=_("exec reset-slave-all failed: {}".format(res[0]["error_msg"]))
            )

        # 提升新主节点
        exec_sql = ["set tc_admin=1", f"TDBCTL DROP NODE IF EXISTS {server_name}", enable_primary_sql]
        rpc_params["cmds"] = exec_sql
        res = DRSApi.rpc(rpc_params)
        if res[0]["error_msg"]:
            raise CtlSwitchToSlaveFailedException(
                message=_("exec TDBCTL-DISABLE-PRIMARY failed: {}".format(res[0]["error_msg"]))
            )
        return True

    def _sync_to_new_master(self, cluster: Cluster, new_primary: ProxyInstance, other_secondary: List[ProxyInstance]):
        """
        其余的slave节点同步新的master
        """
        # 获取同步账号
        data = PayloadHandler.get_repl_account()

        # 基于GTID建立同步
        # 采用指定position的方式来同步数据
        file, position = SyncMasterService.get_bin_position(
            address=f"{new_primary.machine.ip}{IP_PORT_DIVIDER}{new_primary.admin_port}",
            bk_cloud_id=cluster.bk_cloud_id,
        )
        for secondary in other_secondary:
            repl_sql = (
                f"CHANGE MASTER TO "
                f"MASTER_HOST ='{new_primary.machine.ip}',"
                f"MASTER_PORT={new_primary.admin_port},"
                f"MASTER_USER ='{data['repl_user']}',"
                f"MASTER_PASSWORD='{data['repl_pwd']}',"
                f"MASTER_LOG_FILE = '{file}',"
                f"MASTER_LOG_POS = {position},"
                "MASTER_AUTO_POSITION = 0;"
            )

            res = DRSApi.rpc(
                {
                    "addresses": [f"{secondary.machine.ip}{IP_PORT_DIVIDER}{secondary.admin_port}"],
                    "cmds": ["set tc_admin = 0", repl_sql, "start slave;"],
                    "force": False,
                    "bk_cloud_id": cluster.bk_cloud_id,
                }
            )
            if res[0]["error_msg"]:
                raise CtlSwitchToSlaveFailedException(message=_(f"exec change master  failed: {res[0]['error_msg']}"))
        return True

    def _flush_routing(self, ctl_master: ProxyInstance, bk_cloud_id: int):
        """
        @param ctl_master: 当前集群的中控primary
        @param bk_cloud_id: 云区域id
        """
        get_flush_routing_sql_list = get_flush_routing_sql_for_server(
            ctl_master=f"{ctl_master.machine.ip}{IP_PORT_DIVIDER}{ctl_master.admin_port}",
            bk_cloud_id=bk_cloud_id,
        )
        self.log_info(f"exec flush_routing cmds:[{get_flush_routing_sql_list}]")

        # 如果返回为空，直接返回
        if not get_flush_routing_sql_list:
            return True

        res = DRSApi.rpc(
            {
                "addresses": [f"{ctl_master.machine.ip}{IP_PORT_DIVIDER}{ctl_master.admin_port}"],
                "cmds": ["set tc_admin=1"] + get_flush_routing_sql_list,
                "force": False,
                "bk_cloud_id": bk_cloud_id,
            }
        )
        if res[0]["error_msg"]:
            self.log_error(f"flush routing failed:[{res[0]['error_msg']}]")
            return False
        return True

    def _calc_all_health_ctl(self, cluster: Cluster, ctl_list: List[ProxyInstance]) -> List[ProxyInstance]:
        """
        计算所有的剩余的ctl节点是否健康
        @param ctl_list: 剩余的ctl节点
        @return: 健康的ctl节点
        """
        health_ctl_list = []
        for ctl in ctl_list:
            if not self.check_node_health(
                cluster=cluster, check_nodes=[f"{ctl.machine.ip}{IP_PORT_DIVIDER}{ctl.admin_port}"]
            ):
                # 如果节点访问正常，跳过
                health_ctl_list.append(ctl)
                continue

            # 如果节点访问失败，且元数据记录是不可用状态，则这里切换跳过这个节点的处理
            if ctl.status == InstanceStatus.UNAVAILABLE:
                self.log_warning(
                    f"ctl [{ctl.machine.ip}{IP_PORT_DIVIDER}{ctl.admin_port}] is unavailable, skip switch"
                )
                continue
            # 如果节点访问失败，且元数据记录是可用状态，则这里切换报出异常
            self.log_error(f"ctl [{ctl.machine.ip}{IP_PORT_DIVIDER}{ctl.admin_port}] is running, switch failed")
            raise CtlSwitchToSlaveFailedException(message=_("切换中控失败，有running状态ctl节点，drs访问失败"))

        # 如果health_ctl_list为空，则没有节点作为新的primary，则报出异常
        if not health_ctl_list:
            self.log_error("no healthy ctl found")
            raise CtlSwitchToSlaveFailedException(message=_("切换中控失败，没有健康的ctl节点"))

        return health_ctl_list

    def _execute(self, data, parent_data):
        """
        中控集群切换逻辑：

        1：如果原来的primary已经异常（走强切逻辑，中控有可能有丢数据风险）
            A：随机选择出一个new primary
            B: 关闭所有同步
            C: 剩余不剔除的tdbctl，与new primary建立同步
            D: new primary 执行TDBCTL ENABLE PRIMARY, 做中控集群的主节点
            E: 剩余的tdbctl 执行 flush routing 相关命令， 同步路由


        2：如果原来的primary是正常 （安全切换）
            A：检查old primary是否有活跃的链接
            B: 检查剩余的tdbctl节点，数据同步是否正常
            C：old primary执行 TDBCTL DISABLE PRIMARY命令，禁止中控转发DDL请求
            D: 随机选择出一个new primary，等待new primary 与 old primary 数据完全同步
            E: 关闭所有同步
            F: 剩余不剔除的tdbctl，与new primary建立同步
            G: new primary 执行TDBCTL ENABLE PRIMARY, 做中控集群的主节点
            H: 剩余的tdbctl 执行 flush routing 相关命令， 同步路由
        """
        kwargs = data.get_one_of_inputs("kwargs")

        reduce_ctl_primary = kwargs["reduce_ctl_primary"]
        reduce_ctl_secondary_list = kwargs["reduce_ctl_secondary_list"]

        # 获取cluster对象，包括中控实例、 spider端口等
        cluster = Cluster.objects.get(id=kwargs["cluster_id"])

        # 查询所有的spider-ctl的其余从节点对象
        exclude_ips = [reduce_ctl_primary.split(":")[0]] + [i["ip"] for i in reduce_ctl_secondary_list]
        ctl_set = cluster.proxyinstance_set.filter(
            tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_MASTER
        ).exclude(machine__ip__in=exclude_ips)

        # 检验剩余tdbctl节点的健康状态，如果节点访问失败，且元数据记录是不可用状态，则这里切换跳过这个节点；否则报出异常
        remaining_ctl_list = self._calc_all_health_ctl(cluster=cluster, ctl_list=list(ctl_set))
        new_ctl_primary = remaining_ctl_list[0]
        # 根据传入新的primary节点, 计算出其余的从节点
        other_secondary = remaining_ctl_list[1:]
        self.log_info(f"new_ctl_primary: {new_ctl_primary.machine.ip}{IP_PORT_DIVIDER}{new_ctl_primary.admin_port}")

        # 阶段1 先检测是否当前可以提升主切换
        result = self._prepare_check(
            cluster=cluster, reduce_ctl_primary=reduce_ctl_primary, standby_ctl_list=remaining_ctl_list
        )

        # 阶段2 尝试连接原来ctl_primary,走安全切换， 执行TDBCTL DISABLE PRIMARY， 意味着primary不处理DDL请求
        if result:
            self._exec_primary(cluster, reduce_ctl_primary, "disable")
            if not self._double_check_new_primary_sync(
                cluster=cluster,
                reduce_ctl_primary=reduce_ctl_primary,
                new_ctl_primary=f"{new_ctl_primary.machine.ip}{IP_PORT_DIVIDER}{new_ctl_primary.admin_port}",
            ):
                self.log_warning(_("退回操作，旧primary重新enable"))
                self._exec_primary(cluster, reduce_ctl_primary, "enable")
                raise CtlSwitchToSlaveFailedException(message=_("新primary未完全同步当前primary，请等待同步完成后重试"))

        # 阶段3 关闭所有从节点的主从同步
        self._stop_slave(cluster, remaining_ctl_list)
        self.log_info(_("关闭所有从节点的主从同步成功"))

        # 阶段3
        # 这里考虑到ctl集群只有一个节点的情况，则需要用Standalone模式提示为primary
        if not other_secondary:
            # Standalone 模式
            self.log_info(_("目前只有一个tdbctl节点，使用Standalone集群模式， 强制提升为primary"))
            # 连接新的primary节点，执行剔除原primary节点的命令, 并提升自己为primary TDBCTL ENABLE PRIMARY FORCE
            self._new_master_enable_primary(cluster, new_ctl_primary, reduce_ctl_primary, is_force=True)
            self.log_info(_("节点[{}:{}]提升自己为primary成功").format(new_ctl_primary.machine.ip, new_ctl_primary.admin_port))
        else:
            # 集群模式
            # 阶段4 其余节点同步新的primary节点
            self._sync_to_new_master(cluster, new_ctl_primary, other_secondary)
            self.log_info(_("在其余节点同步新的primary节点[{}]成功").format(new_ctl_primary))

            # 阶段5 连接新的primary节点，执行剔除原primary节点的命令, 并提升自己为primary TDBCTL ENABLE PRIMARY
            self._new_master_enable_primary(cluster, new_ctl_primary, reduce_ctl_primary)
            self.log_info(_("节点[{}:{}]提升自己为primary成功").format(new_ctl_primary.machine.ip, new_ctl_primary.admin_port))

        # 阶段6 其余tdbctl slave执行flush routing，确保路由是同步的
        self.log_info("exec flush routing ....")
        if not self._flush_routing(ctl_master=new_ctl_primary, bk_cloud_id=cluster.bk_cloud_id):
            return False
        self.log_info("exec flush routing successfully")
        return True


class CtlSwitchToSlaveComponent(Component):
    name = __name__
    code = "ctl_switch_to_slave"
    bound_service = CtlSwitchToSlaveService
