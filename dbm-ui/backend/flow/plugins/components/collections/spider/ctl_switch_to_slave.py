"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
from time import sleep

from django.utils.translation import ugettext_lazy as _
from pipeline.component_framework.component import Component

from backend.components import DBConfigApi, DRSApi, MySQLPrivManagerApi
from backend.components.dbconfig.constants import FormatType, LevelName
from backend.constants import IP_PORT_DIVIDER
from backend.core.encrypt.handlers import RSAHandler
from backend.db_meta.enums import TenDBClusterSpiderRole
from backend.db_meta.models import Cluster
from backend.flow.consts import TDBCTL_USER, ConfigTypeEnum, NameSpaceEnum, PrivRole
from backend.flow.engine.bamboo.scene.spider.common.exceptions import CtlSwitchToSlaveFailedException
from backend.flow.plugins.components.collections.common.base_service import BaseService


class CtlSwitchToSlaveService(BaseService):
    """
    定义spider(tenDB cluster)集群的中控集群做主节点提示，适用于spider裁撤场合调用
    这里暂时不考虑主从互切场景，仅仅做提升主节点场景，因为互切展示没有需求
    幂等的内容包括: 预检测、断开同步、选择新的主节点、重新同步新主节点
    私有变量的主要结构体kwargs：
    {
        “cluster_id”: id,  待关联的集群id
        "reduce_ctl_primary": 传入的待删除的中控primary实例，格式“ip:port”
        "new_ctl_primary": 传入的待提升primary的中控实例，格式“ip:port”
    }
    """

    def _is_running_process(self, rds_params):
        """
        检测待回收的primary是否存在running状态的线程
        """
        check_sql = (
            f"select * from information_schema.TDBCTL_CLUSTER_PROCESSLIST where user = '{TDBCTL_USER}'"
            + " and command != 'Sleep' and info not like '%INFORMATION_SCHEMA.PROCESSLIST';"
        )
        rds_params["cmds"] = ["set tc_admin=1"] + [check_sql]
        res = DRSApi.rpc(rds_params)
        if res[0]["error_msg"]:
            raise CtlSwitchToSlaveFailedException(
                message=_("select processlist failed: {}".format(res[0]["error_msg"]))
            )

        if res[0]["cmd_results"][1]["table_data"]:
            self.log_warning(f"There are also {res[0]['cmd_results'][1]['rows_affected']} non-sleep state threads")
            return False

        return True

    def _prepare_check(self, cluster: Cluster, reduce_ctl_primary: str):
        """
        检测当前是否可以执行切换
        todo 是否需要检验checksum结果？
        """
        cmds = ["set tc_admin=1"]
        rpc_params = {
            "addresses": [reduce_ctl_primary],
            "cmds": cmds,
            "force": False,
            "bk_cloud_id": cluster.bk_cloud_id,
        }
        # 检测待下架的中控primary是否能连接上
        check_sql = "select 1;"
        rpc_params["cmds"] = cmds + [check_sql]
        res = DRSApi.rpc(rpc_params)
        if "connection refused" in res[0]["error_msg"]:
            # 任务待下架的节点已经故障，应该不做下面的处理，作为故障机处理
            self.log_warning(res[0]["error_msg"])
            return False

        # 检测原primary节点是否正在执行中控命令
        if self._is_running_process(rds_params=rpc_params):
            # 如果第一次检验到有running的process，则尝试等待10秒，重新检验一次，如果还存在则退出
            sleep(10)
            if not self._is_running_process(rds_params=rpc_params):
                raise CtlSwitchToSlaveFailedException(
                    message=_("After two detections, there are still non-sleep state threads in the instance")
                )
        return True

    def _exec_disable_primary(self, cluster: Cluster, reduce_ctl_primary):
        """
        连接待下架的primary，执行执行TDBCTL DISABLE PRIMARY
        """
        res = DRSApi.rpc(
            {
                "addresses": [reduce_ctl_primary],
                "cmds": ["set tc_admin = 1", "TDBCTL DISABLE PRIMARY"],
                "force": False,
                "bk_cloud_id": cluster.bk_cloud_id,
            }
        )
        if res[0]["error_msg"]:
            raise CtlSwitchToSlaveFailedException(
                message=_("exec TDBCTL-DISABLE-PRIMARY failed: {}".format(res[0]["error_msg"]))
            )
        self.log_info(f"[{reduce_ctl_primary}]exec TDBCTL-DISABLE-PRIMARY success")
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
            self.log_info(f"exec stop slave in instance[{ctl.machine.ip}{IP_PORT_DIVIDER}{ctl.admin_port}")
            rpc_params["addresses"] = [f"{ctl.machine.ip}{IP_PORT_DIVIDER}{ctl.admin_port}"]
            res = DRSApi.rpc(rpc_params)

            if res[0]["error_msg"]:
                raise CtlSwitchToSlaveFailedException(
                    message=_(f"exec [{ctl.ip_port}] stop slave failed: {res[0]['error_msg']}")
                )

        return True

    def _new_master_enable_primary(self, cluster: Cluster, new_master, reduce_ctl_primary):
        """
        提升新节点作为主节点的逻辑
        """
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
            "set tc_admin = 1",
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

        # 提升新主节点
        exec_sql = ["set tc_admin=1", f"TDBCTL DROP NODE IF EXISTS {server_name}", "TDBCTL ENABLE PRIMARY"]
        rpc_params["cmds"] = exec_sql
        res = DRSApi.rpc(rpc_params)
        if res[0]["error_msg"]:
            raise CtlSwitchToSlaveFailedException(
                message=_("exec TDBCTL-DISABLE-PRIMARY failed: {}".format(res[0]["error_msg"]))
            )
        return True

    def _sync_to_new_master(self, cluster: Cluster, new_primary, other_secondary):
        """
        其余的slave节点同步新的master
        """
        # 获取同步账号
        data = DBConfigApi.query_conf_item(
            {
                "bk_biz_id": "0",
                "level_name": LevelName.PLAT,
                "level_value": "0",
                "conf_file": "mysql#user",
                "conf_type": ConfigTypeEnum.InitUser,
                "namespace": NameSpaceEnum.TenDB.value,
                "format": FormatType.MAP,
            }
        )["content"]

        # 远程授权
        MySQLPrivManagerApi.add_priv_without_account_rule(
            {
                "bk_cloud_id": cluster.bk_cloud_id,
                "bk_biz_id": cluster.bk_biz_id,
                "operator": "",
                "user": data["repl_user"],
                "psw": RSAHandler.encrypt_password(
                    MySQLPrivManagerApi.fetch_public_key(), data["repl_pwd"], salt=None
                ),
                "hosts": [slave.machine.ip for slave in other_secondary],
                "dbname": "%",
                "dml_ddl_priv": "",
                "global_priv": "REPLICATION SLAVE, REPLICATION CLIENT",
                "address": new_primary,
                "role": PrivRole.TDBCTL.value,
            }
        )
        self.log_info(_("在[{}]创建添加同步账号成功").format(new_primary))

        # 基于GTID建立同步
        for secondary in other_secondary:
            repl_sql = (
                f"CHANGE MASTER TO"
                f"MASTER_HOST ='{new_primary.split(':')[0]}',"
                f"MASTER_PORT={new_primary.split(':')[1]},"
                f"MASTER_USER ='{data['repl_user']}',"
                f"MASTER_PASSWORD='{data['repl_pwd']}',"
                "MASTER_AUTO_POSITION = 1;"
            )

            res = DRSApi.rpc(
                {
                    "addresses": [f"{secondary.machine.ip}{IP_PORT_DIVIDER}{secondary.admin_port}"],
                    "cmds": ["set tc_admin = 0", repl_sql],
                    "force": False,
                    "bk_cloud_id": cluster.bk_cloud_id,
                }
            )
            if res[0]["error_msg"]:
                raise CtlSwitchToSlaveFailedException(message=_(f"exec change master  failed: {res[0]['error_msg']}"))
        return True

    def _execute(self, data, parent_data):
        kwargs = data.get_one_of_inputs("kwargs")

        reduce_ctl_primary = kwargs["reduce_ctl_primary"]
        new_ctl_primary = kwargs["new_ctl_primary"]

        # 获取cluster对象，包括中控实例、 spider端口等
        cluster = Cluster.objects.get(id=kwargs["cluster_id"])

        # 查询所有的spider-ctl的其余从节点对象
        ctl_set = cluster.proxyinstance_set.filter(
            tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_MASTER
        ).exclude(machine__ip=reduce_ctl_primary.split(":")[0])

        # 阶段1 先检测是否当前可以提升主切换
        result = self._prepare_check(cluster=cluster, reduce_ctl_primary=reduce_ctl_primary)

        # 阶段2 尝试连接原来ctl_primary,执行TDBCTL DISABLE PRIMARY
        if result:
            self._exec_disable_primary(cluster, reduce_ctl_primary)

        # 阶段3 关闭所有从节点的主从同步
        self._stop_slave(cluster, ctl_set)

        # 阶段3 根据传入新的primary节点,计算出其余的从节点
        other_secondary = ctl_set.exclude(machine__ip=new_ctl_primary.split(":")[0])

        # 阶段4 其余节点同步新的primary节点
        self._sync_to_new_master(cluster, new_ctl_primary, other_secondary)

        # 阶段5 连接新的primary节点，执行剔除原primary节点的命令, 并提升自己为primary TDBCTL ENABLE PRIMARY
        self._new_master_enable_primary(cluster, new_ctl_primary, reduce_ctl_primary)


class CtlSwitchToSlaveComponent(Component):
    name = __name__
    code = "ctl_switch_to_slave"
    bound_service = CtlSwitchToSlaveService
