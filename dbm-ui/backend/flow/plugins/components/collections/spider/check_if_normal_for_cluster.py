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

from django.utils.translation import ugettext as _
from pipeline.component_framework.component import Component

from backend.components import DRSApi, NameServiceApi
from backend.db_meta.api.cluster.tendbcluster.handler import TenDBClusterClusterHandler
from backend.db_meta.enums import ClusterEntryType, TenDBClusterSpiderRole
from backend.db_meta.models import CLBEntryDetail, Cluster, ClusterEntry
from backend.db_services.plugin.nameservice.mysql_clb import get_cluster_entry_role, operate_part_target
from backend.flow.engine.bamboo.scene.common.machine_os_init import RecycleOutputContext
from backend.flow.engine.bamboo.scene.spider.common.exceptions import (
    CalcRecycleFailedException,
    DropSpiderNodeFailedException,
)
from backend.flow.plugins.components.collections.spider.drop_spider_ronting import DropSpiderRoutingService
from backend.flow.utils.base.flow_output import FlowOutputHandler
from backend.flow.utils.dns_manage import DnsManage
from backend.flow.utils.spider.spider_db_function import check_spider_node_is_add_cluster


@dataclass()
class CheckIfNormalSpiderNodeKwargs:
    cluster_id: int
    spider_hosts: list
    spider_role: TenDBClusterSpiderRole
    resource_spec: dict
    created_by: str
    is_slave_cluster_create: int = 0
    new_db_module_id: int = 0


class CheckIfNormalSpiderNodeService(DropSpiderRoutingService):
    """
    定义检查spider节点是否正常进入集群内，并且已经在提供访问
    判断逻辑：
    1：是否正常加入到路由表
    2：是否加入dns和clb
    3：是否写入集群元数据中
    场景A：如果1、2、3 都写入，则认为机器也完成加入集群并提供访问，则不进入主机回收列表
    场景B：如果1、2写入，3没有写，则也认为机器也完成加入集群并提供访问，但需要主动加入集群元数据，加入完成后，不进入回收列表
    场景C：如果1写入，2没有写，则认为机器没有进入集群并提供访问,则尝试执回退1，并行进入回收列表
    其他场景，都进入回收列表
    """

    def _execute(self, data, parent_data) -> bool:

        kwargs = data.get_one_of_inputs("kwargs")
        global_data = data.get_one_of_inputs("global_data")
        recycle_hosts = []
        # 判断集群是否还存在
        cluster = self._get_cluster_with_id(kwargs["cluster_id"])
        if not cluster:
            # 表示cluster_id对应的集群已经下架, 则这单据针对这个集群申请到的机器都进入退回列表
            recycle_hosts.extend(kwargs["spider_hosts"])
            return True

        # 判断每个spider_ip是否加入到集群中
        for spider_host in kwargs["spider_hosts"]:
            if not self._check_ip_for_cluster(
                cluster=cluster,
                spider_host=spider_host,
                spider_role=kwargs["spider_role"],
                resource_spec=kwargs["resource_spec"],
                is_slave_cluster_create=kwargs["is_slave_cluster_create"],
                new_db_module_id=kwargs["new_db_module_id"],
                created_by=kwargs["created_by"],
            ):
                recycle_hosts.append(spider_host)

        self.log_info(f"recycle_hosts:{recycle_hosts}")
        if recycle_hosts:
            # 输出待回收host信息
            FlowOutputHandler(RecycleOutputContext.ToResourceSerializer).insert_data(
                global_data["job_root_id"], recycle_hosts
            )

        return True

    def _check_ip_for_cluster(
        self, cluster: Cluster, spider_host: dict, spider_role: TenDBClusterSpiderRole, **kwargs
    ) -> bool:
        """
        判断ip节点是否已经加入到集群当中
        返回如果True，表示不退回，反之返回False，表示退回
        """
        check_routing_result = self._check_routing(cluster=cluster, spider_ip=spider_host["ip"])
        check_dns_result, check_clb_result = self._check_entry(
            cluster=cluster, spider_ip=spider_host["ip"], spider_role=spider_role
        )
        check_db_meta_result = self._check_db_meta(cluster=cluster, spider_ip=spider_host["ip"])
        self.log_info(f"check_routing_result:{check_routing_result}")
        self.log_info(f"check_dns_result:{check_dns_result}")
        self.log_info(f"check_clb_result:{check_clb_result}")
        self.log_info(f"check_db_meta_result:{check_db_meta_result}")

        if check_routing_result and (check_dns_result or check_clb_result):
            # 场景A和B, 路由加入、访问入口加入， 按照逻辑节点已经对外，应该向前滚动修复，并且不加入主机退回流程
            if not check_dns_result:
                # 修复dns
                self.log_info("fix dns...")
                self._fix_dns(cluster=cluster, spider_ip=spider_host["ip"], spider_role=spider_role)
            if not check_clb_result:
                # 修复clb
                self.log_info("fix clb...")
                self._fix_clb(cluster=cluster, spider_ip=spider_host["ip"], spider_role=spider_role)

            if not check_db_meta_result:
                # 修复元数据
                self.log_info("fix db_meta...")
                self._fix_db_meta(
                    cluster=cluster,
                    spiders=[spider_host],
                    spider_role=spider_role,
                    resource_spec=kwargs["resource_spec"],
                    is_slave_cluster_create=kwargs["is_slave_cluster_create"],
                    new_db_module_id=kwargs["new_db_module_id"],
                    created_by=kwargs["created_by"],
                )
            return True

        elif check_routing_result and not check_dns_result and not check_clb_result:
            # 场景C, 路由加入了，但是访问入口没有加上，就回退路由信息，加入到待回收列表
            # 删除路由信息
            ctl_primary = cluster.tendbcluster_ctl_primary_address()
            spider_port = cluster.proxyinstance_set.first().port

            self._exec_drop_routing(
                cluster=cluster, ctl_primary=ctl_primary, spider_ip=spider_host["ip"], spider_port=spider_port
            )
            if spider_role == TenDBClusterSpiderRole.SPIDER_MASTER:
                # 顺便把tdbctl给删除了
                ctl_port = cluster.proxyinstance_set.first().admin_port
                self._exec_drop_routing(
                    cluster=cluster, ctl_primary=ctl_primary, spider_ip=spider_host["ip"], spider_port=ctl_port
                )
            # 刷线路由信息
            if not self.flush_routing(ctl_master=ctl_primary, bk_cloud_id=cluster.bk_cloud_id):
                raise CalcRecycleFailedException(f"cluster [{cluster.immute_domain}] flush routing error")
            return False

        else:
            # 剩余检测场景，就是没有路由信息场景
            # 统一加入待回收队列
            return False

    def _get_cluster_with_id(self, cluster_id) -> Cluster | None:
        """
        根据cluster_id获取cluster元信息
        @param cluster_id: 集群id
        """
        try:
            cluster = Cluster.objects.get(id=cluster_id)
            return cluster
        except Cluster.DoesNotExist:
            self.log_error(_("集群ID[{}]已在平台不存在".format(cluster_id)))
            return None

    def _check_routing(self, cluster: Cluster, spider_ip: str) -> bool:
        """
        检查路由信息
        加入返回True，反之返回False
        @param cluster: 集群元信息
        @param spider_ip: 需要检查的spider ip信息

        """
        spider_port = cluster.proxyinstance_set.first().port
        if check_spider_node_is_add_cluster(cluster=cluster, spider_port=spider_port, spider_ip=spider_ip):
            self.log_info(
                f"[check routing result]: "
                f"spider_instance[{spider_ip}:{spider_port}] has already joined the cluster[{cluster.immute_domain}]"
            )
            return True

        self.log_error(
            f"[check routing result]: "
            f"spider_instance[{spider_ip}:{spider_port}] has not joined the cluster[{cluster.immute_domain}]"
        )
        return False

    def _check_dns(self, cluster: Cluster, spider_ip: str, domain: str):
        """
        检查dns域名是否有解析
        """
        dns_manage = DnsManage(bk_biz_id=cluster.bk_biz_id, bk_cloud_id=cluster.bk_cloud_id)
        for row in dns_manage.get_domain(domain_name=domain):
            if row["ip"] == spider_ip:
                self.log_info(f"{spider_ip} DNS resolution already exists[{domain}]")
                return True

        self.log_error(f"{spider_ip} DNS resolution is not exists[{domain}]")
        return False

    def _fix_dns(self, cluster: Cluster, spider_ip: str, spider_role: TenDBClusterSpiderRole):
        """
        修复dns域名解析
        """
        entry_role = get_cluster_entry_role(spider_role)
        spider_port = cluster.proxyinstance_set.first().port
        dns = ClusterEntry.objects.get(cluster=cluster, role=entry_role, cluster_entry_type=ClusterEntryType.DNS)
        dns_manage = DnsManage(bk_biz_id=cluster.bk_biz_id, bk_cloud_id=cluster.bk_cloud_id)
        try:
            dns_manage.create_domain(instance_list=[f"{spider_ip}#{spider_port}"], add_domain_name=dns.entry)
            self.log_info(f"{spider_ip} add DNS resolution [{dns.entry}] successfully")
            return True
        except Exception as err:
            raise CalcRecycleFailedException(f"{spider_ip} add DNS resolution [{dns.entry}] failed: {err}")

    def _check_clb(self, cluster: Cluster, spider_ip: str, entry: ClusterEntry):
        """
        检查clb是否有绑定到ip信息
        """
        clb_detail = CLBEntryDetail.objects.get(entry=entry)
        info = NameServiceApi.clb_check_clb_register_target_by_ip({"region": cluster.region, "ips": [spider_ip]})
        if info and info["clbid"] == clb_detail.clb_id:
            # 表示主机已经绑定好clb
            self.log_info(f"{spider_ip} already bound to clb [{clb_detail.clb_id}]")
            return True

        self.log_error(f"{spider_ip} is not bound to clb [{clb_detail.clb_id}]")
        return False

    def _fix_clb(self, cluster: Cluster, spider_ip: str, spider_role: TenDBClusterSpiderRole):
        """
        修复clb绑定到ip信息
        """
        try:
            entry_role = get_cluster_entry_role(spider_role)
            ClusterEntry.objects.get(cluster=cluster, role=entry_role, cluster_entry_type=ClusterEntryType.CLB)
        except ClusterEntry.DoesNotExist:
            self.log_warning(f"[_fix_clb]: cluster[{cluster.immute_domain}] no clb config, skip check")
            return True

        output = operate_part_target(cluster_id=cluster.id, ips=[spider_ip], bind=True, role=spider_role)
        if output["code"] == 0:
            # 表示绑定成功
            self.log_info(f"{spider_ip} binding clb successfully")
            return True
        else:
            raise CalcRecycleFailedException(f"{spider_ip} binding clb error: [{output['message']}]")

    def _check_entry(self, cluster: Cluster, spider_ip: str, spider_role: TenDBClusterSpiderRole) -> tuple[bool, bool]:
        """
        检查访问入口是否有解析, 目前spider只接入dns和clb请求
        加入返回True，反之返回False
        @param cluster: 集群元信息
        @param spider_ip: 需要检查的spider ip信息
        """
        entry_role = get_cluster_entry_role(spider_role)
        dns_entry = ClusterEntry.objects.get(cluster=cluster, role=entry_role, cluster_entry_type=ClusterEntryType.DNS)
        dns_is_add = self._check_dns(cluster=cluster, spider_ip=spider_ip, domain=dns_entry.entry)

        # clb配置是TenDBCLuster集群可选配置，不一定存在，这里做一下try-except处理，如果clb不存在，则认为不需要处理clb
        try:
            clb_entry = ClusterEntry.objects.get(
                cluster=cluster, role=entry_role, cluster_entry_type=ClusterEntryType.CLB
            )
            clb_is_add = self._check_clb(cluster=cluster, spider_ip=spider_ip, entry=clb_entry)
        except ClusterEntry.DoesNotExist:
            self.log_warning(f"[check entry result]: cluster[{cluster.immute_domain}] no clb config, skip check")
            clb_is_add = False

        return dns_is_add, clb_is_add

    def _check_db_meta(self, cluster: Cluster, spider_ip: str) -> bool:
        """
        检查元数据
        因为单据写入元数据是原子任务，那么这里判断一下集群是否找到对应spider_ip, 如果有，则表示数据已经完整写入，判断正常。
        反之则代表单据原子任务全回滚，写入失败
        """
        if cluster.proxyinstance_set.filter(machine__ip=spider_ip).exists():
            self.log_info(
                f"[check db meta result]:{spider_ip} already add in db_meta_cluster [{cluster.immute_domain}]"
            )
            return True

        self.log_error(f"[check db meta result]:{spider_ip} is not add in db_meta_cluster [{cluster.immute_domain}]")
        return False

    @staticmethod
    def _fix_db_meta(
        cluster: Cluster,
        spiders: list,
        spider_role: TenDBClusterSpiderRole,
        resource_spec: dict,
        is_slave_cluster_create: bool,
        new_db_module_id: int,
        created_by: str = "fix_admin",
    ) -> bool:
        """
        修复元数据
        """
        kwargs = {
            "cluster_id": cluster.id,
            "creator": created_by,
            "add_spiders": spiders,
            "spider_role": spider_role,
            "resource_spec": resource_spec,
            "is_slave_cluster_create": is_slave_cluster_create,
            "new_db_module_id": new_db_module_id,
        }
        TenDBClusterClusterHandler.add_spiders(**kwargs)
        return True

    def _exec_drop_routing(self, cluster: Cluster, ctl_primary: str, spider_ip: str, spider_port: int):
        """
        执行删除节点路由逻辑
        """

        rpc_params = {
            "addresses": [ctl_primary],
            "cmds": [],
            "force": False,
            "bk_cloud_id": cluster.bk_cloud_id,
        }

        select_sqls = [
            "set tc_admin=1",
            f"select Server_name from mysql.servers where host = '{spider_ip}' and port = {spider_port}",
        ]

        rpc_params["cmds"] = select_sqls
        res = DRSApi.rpc(rpc_params)

        if res[0]["error_msg"]:
            raise DropSpiderNodeFailedException(
                message=_("select mysql.servers failed: {}".format(res[0]["error_msg"]))
            )

        if not res[0]["cmd_results"][1]["table_data"]:
            self.log_warning(f"Node [{spider_ip}:{spider_port}] no longer has routing information")
            return True

        else:
            server_name = res[0]["cmd_results"][1]["table_data"][0]["Server_name"]

            # 删除节点路由信息
            exec_sql = [
                "set tc_admin=1",
                f"TDBCTL DROP NODE IF EXISTS {server_name}",
            ]
            self.log_info(f"exec drop node cmds: [{exec_sql}]")
            rpc_params["cmds"] = exec_sql
            res = DRSApi.rpc(rpc_params)
            if res[0]["error_msg"]:
                raise DropSpiderNodeFailedException(
                    message=_("exec TDBCTL-DROP-NODE failed: {}".format(res[0]["error_msg"]))
                )
            return True


class CheckIfNormalSpiderNodeComponent(Component):
    name = __name__
    code = "check_if_normal_for_cluster"
    bound_service = CheckIfNormalSpiderNodeService
    kwargs = CheckIfNormalSpiderNodeKwargs
