"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""

from django.utils.translation import ugettext_lazy as _
from pipeline.component_framework.component import Component

from backend.components import DRSApi, MySQLPrivManagerApi
from backend.constants import IP_PORT_DIVIDER
from backend.core.encrypt.handlers import AsymmetricHandler
from backend.db_meta.enums import TenDBClusterSpiderRole
from backend.db_meta.models import Cluster
from backend.flow.consts import TDBCTL_USER, PrivRole
from backend.flow.engine.bamboo.scene.spider.common.exceptions import (
    AddSpiderNodeFailedException,
    NormalSpiderFlowException,
)
from backend.flow.plugins.components.collections.common.base_service import BaseService


class AddSpiderRoutingService(BaseService):
    """
    定义spider(tenDB cluster)集群添加spider node的路由信息的活动节点
    幂等的内容包括:  添加内置账号、添加路由信息
    私有变量的主要结构体kwargs：
    {
        “cluster_id”: id,  待关联的集群id
        "add_spiders": 待加入的spider列表
        "add_spider_role": role, 待接入的spider节点角色
        "user": user, 待加入节点的内置账号名称
        "pass": pass, 待加入节点的内置账号密码

    }
    """

    def _drop_user(self, spider_ip: str, spider_port: int, cluster: Cluster):
        """
        这里做一个对当前primary的内置账号删除的逻辑，
        这样做是避免在 create note 过程中，系统内部生成内置账号失败，或者是数据同步失败的情况
        """
        primary_host = cluster.tendbcluster_ctl_primary_address().split(":")[0]
        res = DRSApi.rpc(
            {
                "addresses": [f"{spider_ip}{IP_PORT_DIVIDER}{spider_port}"],
                "cmds": [f"DROP USER  if exists '{TDBCTL_USER}'@'{primary_host}'"],
                "force": False,
                "bk_cloud_id": cluster.bk_cloud_id,
            }
        )
        if res[0]["error_msg"]:
            self.log_error(f"drop user failed:[{res[0]['error_msg']}]")
            return False
        return True

    def _read_ctl_pass(self, ctl_master, bk_cloud_id):
        """
        获取第一次集群部署中控的密码，保证统一集群的所有中控访问的账号秘密是一致的，避免中控同步出现复制冲突
        """
        res = DRSApi.rpc(
            {
                "addresses": [f"{ctl_master}"],
                "cmds": ["select Password as result from mysql.servers where Server_name like 'TDBCTL%' limit 1"],
                "force": False,
                "bk_cloud_id": bk_cloud_id,
            }
        )
        if res[0]["error_msg"]:
            self.log_error(f"drop user failed:[{res[0]['error_msg']}]")
            return ""

        return res[0]["cmd_results"][0]["table_data"][0]["result"]

    def _reset_master(self, spider_ip: str, spider_port: int, bk_cloud_id):
        """
        定义reset master 方法，tdbctl添加时专属
        """
        res = DRSApi.rpc(
            {
                "addresses": [f"{spider_ip}{IP_PORT_DIVIDER}{spider_port}"],
                "cmds": ["reset master"],
                "force": False,
                "bk_cloud_id": bk_cloud_id,
            }
        )
        if res[0]["error_msg"]:
            self.log_error(f"reset master failed:[{res[0]['error_msg']}]")
            return False
        return True

    def _check_node_is_add(self, spider_ip: str, spider_port: int, cluster: Cluster):
        """
        定义一个内置的检测方式，添加之前检测节点是否已存在添加
        @param spider_ip: 待检测node的ip
        @param spider_port: 待检测node的port
        @param cluster: 待关联的cluster对象
        """
        check_sql = "select * from mysql.servers where Host = '{}' and Port = {}".format(spider_ip, spider_port)
        res = DRSApi.rpc(
            {
                "addresses": [cluster.tendbcluster_ctl_primary_address()],
                "cmds": ["set tc_admin=0", check_sql],
                "force": False,
                "bk_cloud_id": cluster.bk_cloud_id,
            }
        )
        if res[0]["error_msg"]:
            raise AddSpiderNodeFailedException(
                message=_("select mysql.servers failed: {}".format(res[0]["error_msg"]))
            )

        if res[0]["cmd_results"][1]["table_data"]:
            self.log_warning("The node has already joined, here choose to skip [{}:{}]".format(spider_ip, spider_port))
            return False

        return True

    def _exec_create_node(self, cluster: Cluster, user: str, passwd: str, spider_ip: str, spider_port: int, tag: str):
        """
        定义通过中控master添加node的公共方法
        """
        cmds = ["set tc_admin=1"]
        rpc_params = {
            "addresses": [cluster.tendbcluster_ctl_primary_address()],
            "cmds": cmds,
            "force": False,
            "bk_cloud_id": cluster.bk_cloud_id,
        }

        if not self._check_node_is_add(cluster=cluster, spider_ip=spider_ip, spider_port=spider_port):
            # 代表这个节点在集群的路由表已经存在，则这里选择跳过
            # todo 这里出现重复只能选择跳过，如果选择重做还没有想好逻辑，而且重做会有风险。
            return True

        if tag == "TDBCTL":
            # 如果create node 是一个tdbctl，则由于gtid的原因需要先reset master，保证新实例GTID_EXECUTED为空，再create node
            if not self._reset_master(spider_ip=spider_ip, spider_port=spider_port, bk_cloud_id=cluster.bk_cloud_id):
                return False

        sql = (
            "tdbctl create node wrapper '{}' options(user '{}', password '{}', host '{}', port {}) with database"
        ).format(tag, user, passwd, spider_ip, spider_port)

        rpc_params["cmds"] = cmds + [sql] + ["TDBCTL FLUSH ROUTING"]
        res = DRSApi.rpc(rpc_params)

        if res[0]["error_msg"]:
            self.log_error("TdbCtl-create-node failed: {}".format(res[0]["error_msg"]))
            return False

        self.log_info("TdbCtl-create-node added successfully [{}:{}]".format(spider_ip, spider_port))
        return True

    def _add_system_user(
        self,
        cluster: Cluster,
        add_spiders: list,
        created_by: str,
        user: str,
        passwd: str,
        ctl_pass: str,
        clt_master_ip: str,
        add_spider_role: str,
    ):
        """
        待加入spider节点对ctl_master添加内置账号
        @param cluster: 待关联的集群对象
        @param add_spiders: 待加入的spider节点列表
        @param created_by: 发起单据的用户名称
        @param user: 内置账号名称，
        @param passwd: 内置账号密码，
        @param ctl_pass: 中控的内置账号密码
        @param clt_master_ip: 当前集群的中控实例的ip
        @param add_spider_role: 添加的spider角色
        """
        # 获取云区域id的方式,已集群信息为准
        spider_port = cluster.proxyinstance_set.first().port
        admin_port = cluster.proxyinstance_set.first().admin_port

        # 密码加密
        encrypted = AsymmetricHandler.encrypt_with_pubkey(
            pubkey=MySQLPrivManagerApi.fetch_public_key(), content=passwd
        )
        for spider_ip in add_spiders:
            if not self._drop_user(spider_ip=spider_ip["ip"], spider_port=spider_port, cluster=cluster):
                return False

            content = {
                "bk_cloud_id": cluster.bk_cloud_id,
                "bk_biz_id": cluster.bk_biz_id,
                "operator": created_by,
                "user": user,
                "psw": encrypted,
                "hosts": [clt_master_ip],
                "dbname": "%",
                "dml_ddl_priv": "",
                "global_priv": "all privileges",
                "address": f'{spider_ip["ip"]}{IP_PORT_DIVIDER}{spider_port}',
                "role": PrivRole.SPIDER.value,
            }

            try:
                MySQLPrivManagerApi.add_priv_without_account_rule(content)
                self.log_info(_("在[{}]创建添加内置账号成功").format(content["address"]))

                if add_spider_role == TenDBClusterSpiderRole.SPIDER_MASTER.value:
                    # 部署spider-master实例，必定启动中控实例，这里增加对中控实例的内置授权
                    content["address"] = f'{spider_ip["ip"]}{IP_PORT_DIVIDER}{admin_port}'
                    content["role"] = PrivRole.TDBCTL.value
                    content["psw"] = AsymmetricHandler.encrypt_with_pubkey(
                        pubkey=MySQLPrivManagerApi.fetch_public_key(), content=ctl_pass
                    )
                    MySQLPrivManagerApi.add_priv_without_account_rule(content)
                    self.log_info(_("在[{}]创建添加内置账号成功").format(content["address"]))

            except Exception as e:  # pylint: disable=broad-except
                self.log_error(_("[{}]添加用户接口异常，相关信息: {}").format(content["address"], e))
                return False

        return True

    def _execute(self, data, parent_data):
        kwargs = data.get_one_of_inputs("kwargs")
        global_data = data.get_one_of_inputs("global_data")

        # 获取cluster对象，包括中控实例、 spider端口等
        cluster = Cluster.objects.get(id=kwargs["cluster_id"])
        ctl_master = cluster.tendbcluster_ctl_primary_address()
        spider_port = cluster.proxyinstance_set.first().port
        admin_port = cluster.proxyinstance_set.first().admin_port
        ctl_pass = ""

        if kwargs["add_spider_role"] == TenDBClusterSpiderRole.SPIDER_MASTER.value:
            # 如果添加的是spider_master，则必须添加中控实例，添加中控实例之前，获取中控实例的密码
            ctl_pass = self._read_ctl_pass(ctl_master=ctl_master, bk_cloud_id=cluster.bk_cloud_id)
            if not ctl_pass:
                return False

        # 先对待加入的spider节点添加内置账号，接口幂等

        if not self._add_system_user(
            cluster=cluster,
            add_spiders=kwargs["add_spiders"],
            created_by=global_data["created_by"],
            user=kwargs["user"],
            passwd=kwargs["passwd"],
            ctl_pass=ctl_pass,
            clt_master_ip=ctl_master.split(":")[0],
            add_spider_role=kwargs["add_spider_role"],
        ):
            return False

        # 循环添加路由信息，添加之前判断是否已经存在
        for add_spider in kwargs["add_spiders"]:

            if kwargs["add_spider_role"] == TenDBClusterSpiderRole.SPIDER_SLAVE.value:
                tag = "SPIDER_SLAVE"
            elif kwargs["add_spider_role"] in [
                TenDBClusterSpiderRole.SPIDER_MASTER.value,
                TenDBClusterSpiderRole.SPIDER_MNT.value,
            ]:
                tag = "SPIDER"
            else:
                raise NormalSpiderFlowException(message=_("This spider-role is not supported,check"))

            # 执行添加node的方法，方法幂等
            if not self._exec_create_node(
                cluster=cluster,
                user=kwargs["user"],
                passwd=kwargs["passwd"],
                spider_ip=add_spider["ip"],
                spider_port=spider_port,
                tag=tag,
            ):
                return False

            if kwargs["add_spider_role"] == TenDBClusterSpiderRole.SPIDER_MASTER.value:
                # 对中控实例也执行添加node行为
                tag = "TDBCTL"
                if not self._exec_create_node(
                    cluster=cluster,
                    user=kwargs["user"],
                    passwd=ctl_pass,
                    spider_ip=add_spider["ip"],
                    spider_port=admin_port,
                    tag=tag,
                ):
                    return False
        return True


class AddSpiderRoutingComponent(Component):
    name = __name__
    code = "add_add_spider_routing_in_cluster"
    bound_service = AddSpiderRoutingService
