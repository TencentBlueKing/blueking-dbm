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

from django.utils.translation import gettext as _

from backend.db_meta.enums import (
    ClusterEntryRole,
    ClusterEntryType,
    ClusterType,
    InstanceInnerRole,
    TenDBClusterSpiderRole,
)
from backend.db_meta.models import Cluster, ClusterEntry
from backend.flow.consts import DnsOpType
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.engine.bamboo.scene.common.entrys_manager import BuildDNSManageSubflow
from backend.flow.engine.bamboo.scene.mysql.clone_grants_from_file import mysql_clone_grants_from_file_subflow
from backend.flow.plugins.components.collections.mysql.clone_proxy_client_in_backend import (
    CloneProxyUsersInBackendComponent,
)
from backend.flow.plugins.components.collections.mysql.clone_proxy_user_in_cluster import (
    CloneProxyUsersInClusterComponent,
)
from backend.flow.plugins.components.collections.mysql.mysql_db_meta import MySQLDBMetaComponent
from backend.flow.plugins.components.collections.name_service.mysql_clb_comp import (
    ClbOperationType,
    MySQLClbOperationComponent,
)
from backend.flow.utils.mysql.mysql_act_dataclass import (
    CloneProxyClientInBackendKwargs,
    CloneProxyUsersKwargs,
    DBMetaOPKwargs,
)
from backend.flow.utils.mysql.mysql_db_meta import MySQLDBMeta

logger = logging.getLogger("flow")


def rollback_domain_exchange_subflow(root_id: str, ticket_data: dict, src_cluster: Cluster, dst_cluster: Cluster):
    """
    定义域名互换的子流程 先删除域名再添加域名
    @param root_id: root id
    @param ticket_data: 单据数据
    @param src_cluster: 源集群
    @param dst_cluster: 目标集群
    """
    exchange_sub_pipeline = SubBuilder(root_id=root_id, data=copy.deepcopy(ticket_data))
    #  查询从节点域名
    if src_cluster.cluster_type == ClusterType.TENDBCLUSTER.value:
        src_master_entry = src_cluster.clusterentry_set.get(
            cluster_entry_type=ClusterEntryType.DNS.value, role=ClusterEntryRole.MASTER_ENTRY.value
        )
        dst_master_entry = dst_cluster.clusterentry_set.get(
            cluster_entry_type=ClusterEntryType.DNS.value, role=ClusterEntryRole.MASTER_ENTRY.value
        )
        src_master_spiders = src_cluster.proxyinstance_set.filter(
            tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_MASTER
        )
        dst_master_spiders = dst_cluster.proxyinstance_set.filter(
            tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_MASTER
        )
        src_master_spiders_ips = [spider.machine.ip for spider in src_master_spiders]
        dst_master_spiders_ips = [spider.machine.ip for spider in dst_master_spiders]
        src_slave_entrys = src_cluster.clusterentry_set.filter(
            cluster_entry_type=ClusterEntryType.DNS.value, role=ClusterEntryRole.SLAVE_ENTRY.value
        )
        dst_slave_entrys = dst_cluster.clusterentry_set.filter(
            cluster_entry_type=ClusterEntryType.DNS.value, role=ClusterEntryRole.SLAVE_ENTRY.value
        )
        src_slave_spiders = src_cluster.proxyinstance_set.filter(
            tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_SLAVE
        )
        dst_slave_spiders = dst_cluster.proxyinstance_set.filter(
            tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_SLAVE
        )
        src_slave_spiders_ips = [spider.machine.ip for spider in src_slave_spiders]
        dst_slave_spiders_ips = [spider.machine.ip for spider in dst_slave_spiders]

        cluster_exchange_meta = {
            "source_cluster_id": src_cluster.id,
            "destination_cluster_id": dst_cluster.id,
            "source_master_domain": src_master_entry.entry,
            "destination_master_domain": dst_master_entry.entry,
            "source_slave_domain": src_slave_entrys[0].entry if len(src_slave_entrys) > 0 else "",
            "destination_slave_domain": dst_slave_entrys[0].entry if len(dst_slave_entrys) > 0 else "",
            "source_master_entry_id": src_master_entry.id,
            "destination_master_entry_id": dst_master_entry.id,
            "source_slave_entry_id": src_slave_entrys[0].id if len(src_slave_entrys) > 0 else -1,
            "destination_slave_entry_id": dst_slave_entrys[0].id if len(dst_slave_entrys) > 0 else -1,
        }

        if len(src_master_spiders_ips) < 1 or len(dst_master_spiders_ips) < 1:
            raise Exception(_("源/目标集群不存在主spider ip"))
        # 主spider域名必切，不需要判断。
        domain_del_list = [
            BuildDNSManageSubflow(
                root_id,
                ticket_data,
                DnsOpType.RECYCLE_RECORD,
                {
                    "bk_cloud_id": src_cluster.bk_cloud_id,
                    "port": src_master_spiders[0].port,
                    "del_ips": src_master_spiders_ips,
                },
            ),
            BuildDNSManageSubflow(
                root_id,
                ticket_data,
                DnsOpType.RECYCLE_RECORD,
                {
                    "bk_cloud_id": dst_cluster.bk_cloud_id,
                    "port": dst_master_spiders[0].port,
                    "del_ips": dst_master_spiders_ips,
                },
            ),
        ]

        domain_add_list = [
            BuildDNSManageSubflow(
                root_id,
                ticket_data,
                DnsOpType.CREATE,
                {
                    "bk_cloud_id": src_cluster.bk_cloud_id,
                    "port": src_master_spiders[0].port,
                    "add_ips": src_master_spiders_ips,
                    "entry": dst_master_entry.entry,
                },
            ),
            BuildDNSManageSubflow(
                root_id,
                ticket_data,
                DnsOpType.CREATE,
                {
                    "bk_cloud_id": dst_cluster.bk_cloud_id,
                    "port": dst_master_spiders[0].port,
                    "add_ips": dst_master_spiders_ips,
                    "entry": src_master_entry.entry,
                },
            ),
        ]

        #  tendbCluster 认为主spider必须有域名。而从spider必须同时存在才可切换。
        if len(src_slave_entrys) == 1:
            if len(src_slave_spiders) > 0:
                #  先删除双方域名
                domain_del_list.append(
                    BuildDNSManageSubflow(
                        root_id,
                        ticket_data,
                        DnsOpType.RECYCLE_RECORD,
                        {
                            "bk_cloud_id": src_cluster.bk_cloud_id,
                            "port": src_slave_spiders[0].port,
                            "del_ips": src_slave_spiders_ips,
                        },
                    )
                )
            if len(dst_slave_spiders) > 0:
                domain_add_list.append(
                    BuildDNSManageSubflow(
                        root_id,
                        ticket_data,
                        DnsOpType.CREATE,
                        {
                            "bk_cloud_id": dst_cluster.bk_cloud_id,
                            "port": dst_slave_spiders[0].port,
                            "add_ips": dst_slave_spiders_ips,
                            "entry": src_slave_entrys[0].entry,
                        },
                    )
                )
        elif len(src_slave_entrys) > 1:
            raise Exception(_("源端查询到多个 spider slave 域名"))

        if len(dst_slave_entrys) == 1:
            if len(dst_slave_spiders) > 0:
                domain_del_list.append(
                    BuildDNSManageSubflow(
                        root_id,
                        ticket_data,
                        DnsOpType.RECYCLE_RECORD,
                        {
                            "bk_cloud_id": dst_cluster.bk_cloud_id,
                            "port": dst_slave_spiders[0].port,
                            "del_ips": dst_slave_spiders_ips,
                        },
                    )
                )
            if len(src_slave_spiders) > 0:
                domain_add_list.append(
                    BuildDNSManageSubflow(
                        root_id,
                        ticket_data,
                        DnsOpType.CREATE,
                        {
                            "bk_cloud_id": src_cluster.bk_cloud_id,
                            "port": src_slave_spiders[0].port,
                            "add_ips": src_slave_spiders_ips,
                            "entry": dst_slave_entrys[0].entry,
                        },
                    )
                )
        elif len(dst_slave_entrys) > 1:
            raise Exception(_("目标端查询到多个 spider slave 域名"))

        exchange_sub_pipeline.add_parallel_acts(acts_list=domain_del_list)
        exchange_sub_pipeline.add_parallel_acts(acts_list=domain_add_list)

    elif src_cluster.cluster_type == ClusterType.TenDBHA.value:
        src_master_entry = src_cluster.clusterentry_set.get(
            cluster_entry_type=ClusterEntryType.DNS.value, role=ClusterEntryRole.MASTER_ENTRY.value
        )
        dst_master_entry = dst_cluster.clusterentry_set.get(
            cluster_entry_type=ClusterEntryType.DNS.value, role=ClusterEntryRole.SLAVE_ENTRY.value
        )
        src_master_proxys = src_cluster.proxyinstance_set.filter()
        dst_master_proxys = dst_cluster.proxyinstance_set.filter()
        src_master_proxy_ips = [proxy.machine.ip for proxy in src_master_proxys]
        dst_master_proxy_ips = [proxy.machine.ip for proxy in dst_master_proxys]

        src_is_standby_slave = src_cluster.storageinstance_set.get(
            instance_inner_role=InstanceInnerRole.SLAVE.value, is_stand_by=True
        )
        dst_is_standby_slave = dst_cluster.storageinstance_set.get(
            instance_inner_role=InstanceInnerRole.SLAVE.value, is_stand_by=True
        )
        src_is_standby_entry = src_is_standby_slave.bind_entry.get(
            cluster_entry_type=ClusterEntryType.DNS.value, role=ClusterEntryRole.SLAVE_ENTRY.value
        )
        dst_is_standby_entry = dst_is_standby_slave.bind_entry.get(
            cluster_entry_type=ClusterEntryType.DNS.value, role=ClusterEntryRole.SLAVE_ENTRY.value
        )
        cluster_exchange_meta = {
            "source_cluster_id": src_cluster.id,
            "destination_cluster_id": dst_cluster.id,
            "source_master_domain": src_master_entry.entry,
            "destination_master_domain": dst_master_entry.entry,
            "source_slave_domain": src_is_standby_entry.entry,
            "destination_slave_domain": dst_is_standby_entry.entry,
            "source_master_entry_id": src_master_entry.id,
            "destination_master_entry_id": dst_master_entry.id,
            "source_slave_entry_id": src_is_standby_entry.id,
            "destination_slave_entry_id": dst_is_standby_entry.id,
        }

        domain_del_list = [
            BuildDNSManageSubflow(
                root_id,
                ticket_data,
                DnsOpType.RECYCLE_RECORD,
                {
                    "bk_cloud_id": src_cluster.bk_cloud_id,
                    "port": src_master_proxys[0].port,
                    "del_ips": src_master_proxy_ips,
                },
            ),
            BuildDNSManageSubflow(
                root_id,
                ticket_data,
                DnsOpType.RECYCLE_RECORD,
                {
                    "bk_cloud_id": dst_cluster.bk_cloud_id,
                    "port": dst_master_proxys[0].port,
                    "del_ips": dst_master_proxy_ips,
                },
            ),
            BuildDNSManageSubflow(
                root_id,
                ticket_data,
                DnsOpType.RECYCLE_RECORD,
                {
                    "bk_cloud_id": src_cluster.bk_cloud_id,
                    "port": src_is_standby_slave.port,
                    "del_ips": src_is_standby_slave.machine.ip,
                },
            ),
            BuildDNSManageSubflow(
                root_id,
                ticket_data,
                DnsOpType.RECYCLE_RECORD,
                {
                    "bk_cloud_id": dst_cluster.bk_cloud_id,
                    "port": dst_is_standby_slave.port,
                    "del_ips": dst_is_standby_slave.machine.ip,
                },
            ),
        ]
        domain_add_list = [
            BuildDNSManageSubflow(
                root_id,
                ticket_data,
                DnsOpType.CREATE,
                {
                    "bk_cloud_id": src_cluster.bk_cloud_id,
                    "port": src_master_proxys[0].port,
                    "add_ips": src_master_proxy_ips,
                    "entry": dst_master_entry.entry,
                },
            ),
            BuildDNSManageSubflow(
                root_id,
                ticket_data,
                DnsOpType.CREATE,
                {
                    "bk_cloud_id": dst_cluster.bk_cloud_id,
                    "port": dst_master_entry[0].port,
                    "add_ips": dst_master_proxy_ips,
                    "entry": src_master_entry.entry,
                },
            ),
            BuildDNSManageSubflow(
                root_id,
                ticket_data,
                DnsOpType.CREATE,
                {
                    "bk_cloud_id": src_cluster.bk_cloud_id,
                    "port": src_is_standby_slave.port,
                    "add_ips": src_is_standby_slave.machine.ip,
                    "entry": dst_is_standby_entry.entry,
                },
            ),
            BuildDNSManageSubflow(
                root_id,
                ticket_data,
                DnsOpType.CREATE,
                {
                    "bk_cloud_id": dst_cluster.bk_cloud_id,
                    "port": dst_is_standby_slave.port,
                    "add_ips": dst_is_standby_slave.machine.ip,
                    "entry": src_is_standby_entry.entry,
                },
            ),
        ]

        exchange_sub_pipeline.add_parallel_acts(acts_list=domain_del_list)
        exchange_sub_pipeline.add_parallel_acts(acts_list=domain_add_list)
    elif src_cluster.cluster_type == ClusterType.TenDBSingle.value:
        src_master = src_cluster.storageinstance_set.get(instance_inner_role=InstanceInnerRole.ORPHAN.value)
        dst_master = dst_cluster.storageinstance_set.get(instance_inner_role=InstanceInnerRole.ORPHAN.value)
        src_master_entry = src_master.bind_entry.get(
            cluster_entry_type=ClusterEntryType.DNS.value, role=ClusterEntryRole.MASTER_ENTRY.value
        )
        dst_master_entry = dst_master.bind_entry.get(
            cluster_entry_type=ClusterEntryType.DNS.value, role=ClusterEntryRole.MASTER_ENTRY.value
        )
        cluster_exchange_meta = {
            "source_cluster_id": src_cluster.id,
            "destination_cluster_id": dst_cluster.id,
            "source_master_domain": src_master_entry.entry,
            "destination_master_domain": dst_master_entry.entry,
            "source_master_entry_id": src_master_entry.id,
            "destination_master_entry_id": dst_master_entry.id,
        }
        domain_del_list = [
            BuildDNSManageSubflow(
                root_id,
                ticket_data,
                DnsOpType.RECYCLE_RECORD,
                {"bk_cloud_id": src_cluster.bk_cloud_id, "port": src_master.port, "del_ips": src_master.machine.ip},
            ),
            BuildDNSManageSubflow(
                root_id,
                ticket_data,
                DnsOpType.RECYCLE_RECORD,
                {"bk_cloud_id": dst_cluster.bk_cloud_id, "port": dst_master.port, "del_ips": dst_master.machine.ip},
            ),
        ]
        domain_add_list = [
            BuildDNSManageSubflow(
                root_id,
                ticket_data,
                DnsOpType.CREATE,
                {
                    "bk_cloud_id": src_cluster.bk_cloud_id,
                    "port": src_master.port,
                    "add_ips": src_master.machine.ip,
                    "entry": dst_master_entry.entry,
                },
            ),
            BuildDNSManageSubflow(
                root_id,
                ticket_data,
                DnsOpType.CREATE,
                {
                    "bk_cloud_id": dst_cluster.bk_cloud_id,
                    "port": dst_master.port,
                    "add_ips": dst_master.machine.ip,
                    "entry": src_master_entry.entry,
                },
            ),
        ]
        exchange_sub_pipeline.add_parallel_acts(acts_list=domain_del_list)
        exchange_sub_pipeline.add_parallel_acts(acts_list=domain_add_list)
    else:
        raise Exception(_("域名互换不支持该集群类型"))

    exchange_sub_pipeline.add_act(
        act_name=_("域名切换修改元数据"),
        act_component_code=MySQLDBMetaComponent.code,
        kwargs=asdict(
            DBMetaOPKwargs(
                db_meta_class_func=MySQLDBMeta.tendb_exchange_domain.__name__,
                cluster=cluster_exchange_meta,
                is_update_trans_data=False,
            )
        ),
    )
    return exchange_sub_pipeline.build_sub_process(sub_name=_("域名互换"))


def rollback_clb_exchange_subflow(root_id: str, ticket_data: dict, src_cluster: Cluster, dst_cluster: Cluster):
    """
    定义CLB域名互换的子流程
    @param root_id: root id
    @param ticket_data: 单据数据
    @param src_cluster: 源集群
    @param dst_cluster: 目标集群
    """
    exchange_sub_pipeline = SubBuilder(root_id=root_id, data=copy.deepcopy(ticket_data))

    #  先查看是否有dns
    src_master_entrys = ClusterEntry.objects.filter(
        cluster=src_cluster, cluster_entry_type=ClusterEntryType.CLB.value, role=ClusterEntryRole.MASTER_ENTRY
    )
    src_slave_entrys = ClusterEntry.objects.filter(
        cluster=src_cluster, cluster_entry_type=ClusterEntryType.CLB.value, role=ClusterEntryRole.SLAVE_ENTRY
    )
    dst_master_entrys = ClusterEntry.objects.filter(
        cluster=dst_cluster, cluster_entry_type=ClusterEntryType.CLB.value, role=ClusterEntryRole.MASTER_ENTRY
    )
    dst_slave_entrys = ClusterEntry.objects.filter(
        cluster=dst_cluster, cluster_entry_type=ClusterEntryType.CLB.value, role=ClusterEntryRole.SLAVE_ENTRY
    )

    clb_add_list = []
    clb_del_list = []
    if src_cluster.cluster_type == ClusterType.TenDBSingle.value:
        return None
    elif src_cluster.cluster_type == ClusterType.TENDBCLUSTER.value:
        scr_spider_master_ips = src_cluster.proxyinstance_set.filter(
            tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_MASTER
        )
        dst_spider_master_ips = dst_cluster.proxyinstance_set.filter(
            tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_MASTER
        )
        dst_spider_master_ips = [i.machine.ip for i in dst_spider_master_ips]
        src_spider_master_ips = [i.machine.ip for i in scr_spider_master_ips]
        if len(src_master_entrys) == 1:
            if len(dst_spider_master_ips) == 0:
                raise Exception(_("目标集群没有查询到 spider master"))
            clb_add_list.append(
                {
                    "act_name": _("源集群的Master CLB 映射到目标集群的spider ip"),
                    "act_component_code": MySQLClbOperationComponent.code,
                    "kwargs": {
                        "name_service_operation_type": ClbOperationType.CLB_REGISTER_PART_TARGET.value,
                        "cluster_id": src_cluster.id,
                        "creator": ticket_data["created_by"],
                        "role": TenDBClusterSpiderRole.SPIDER_MASTER,
                        "ips": dst_spider_master_ips,
                    },
                }
            )
            clb_del_list.append(
                {
                    "act_name": _("删除源集群 Master CLB 映射的ips"),
                    "act_component_code": MySQLClbOperationComponent.code,
                    "kwargs": {
                        "name_service_operation_type": ClbOperationType.CLB_DEREGISTER_PART_TARGET.value,
                        "cluster_id": src_cluster.id,
                        "creator": ticket_data["created_by"],
                        "role": TenDBClusterSpiderRole.SPIDER_MASTER,
                        "ips": src_spider_master_ips,
                    },
                }
            )
            # cluster_exchange_clb["source_master_entry_id"] = src_master_entrys[0].id
        if len(dst_master_entrys) == 1:
            if len(src_spider_master_ips) == 0:
                raise Exception(_("源集群没有查询到 spider master"))
            clb_add_list.append(
                {
                    "act_name": _("目标集群的Master CLB 映射到源集群的spider ip"),
                    "act_component_code": MySQLClbOperationComponent.code,
                    "kwargs": {
                        "name_service_operation_type": ClbOperationType.CLB_REGISTER_PART_TARGET.value,
                        "cluster_id": dst_cluster.id,
                        "creator": ticket_data["created_by"],
                        "role": TenDBClusterSpiderRole.SPIDER_MASTER,
                        "ips": src_spider_master_ips,
                    },
                }
            )
            clb_del_list.append(
                {
                    "act_name": _("删除目标集群 Master CLB 映射的ips"),
                    "act_component_code": MySQLClbOperationComponent.code,
                    "kwargs": {
                        "name_service_operation_type": ClbOperationType.CLB_DEREGISTER_PART_TARGET.value,
                        "cluster_id": dst_cluster.id,
                        "creator": ticket_data["created_by"],
                        "role": TenDBClusterSpiderRole.SPIDER_MASTER,
                        "ips": dst_spider_master_ips,
                    },
                }
            )
            # cluster_exchange_clb["destination_master_entry_id"] = dst_master_entrys[0].id

        scr_spider_slave_ips = src_cluster.proxyinstance_set.filter(
            tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_SLAVE
        )
        dst_spider_slave_ips = dst_cluster.proxyinstance_set.filter(
            tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_SLAVE
        )
        src_spider_slave_ips = [i.machine.ip for i in scr_spider_slave_ips]
        dst_spider_slave_ips = [i.machine.ip for i in dst_spider_slave_ips]
        if len(src_slave_entrys) == 1:
            if len(dst_spider_slave_ips) == 0:
                raise Exception(_("目标集群没有查询到 spider slave"))
            clb_add_list.append(
                {
                    "act_name": _("源集群的Slave CLB 映射到目标集群的spider slave ip"),
                    "act_component_code": MySQLClbOperationComponent.code,
                    "kwargs": {
                        "name_service_operation_type": ClbOperationType.CLB_REGISTER_PART_TARGET.value,
                        "cluster_id": src_cluster.id,
                        "creator": ticket_data["created_by"],
                        "role": TenDBClusterSpiderRole.SPIDER_SLAVE,
                        "ips": dst_spider_slave_ips,
                    },
                }
            )
            clb_del_list.append(
                {
                    "act_name": _("删除源集群 Slave CLB 映射的ips"),
                    "act_component_code": MySQLClbOperationComponent.code,
                    "kwargs": {
                        "name_service_operation_type": ClbOperationType.CLB_DEREGISTER_PART_TARGET.value,
                        "cluster_id": src_cluster.id,
                        "creator": ticket_data["created_by"],
                        "role": TenDBClusterSpiderRole.SPIDER_SLAVE,
                        "ips": src_spider_slave_ips,
                    },
                }
            )
            # cluster_exchange_clb["source_slave_entry_id"] = src_slave_entrys[0].id

        if len(dst_slave_entrys) == 1:
            if len(src_spider_slave_ips) == 0:
                raise Exception(_("源集群没有查询到 spider slave"))
            clb_add_list.append(
                {
                    "act_name": _("目标集群的Slave CLB 映射到源集群的spider ip"),
                    "act_component_code": MySQLClbOperationComponent.code,
                    "kwargs": {
                        "name_service_operation_type": ClbOperationType.CLB_REGISTER_PART_TARGET.value,
                        "cluster_id": dst_cluster.id,
                        "creator": ticket_data["created_by"],
                        "role": TenDBClusterSpiderRole.SPIDER_SLAVE,
                        "ips": src_spider_slave_ips,
                    },
                }
            )
            clb_del_list.append(
                {
                    "act_name": _("删除目标集群 Slave CLB 映射的ips"),
                    "act_component_code": MySQLClbOperationComponent.code,
                    "kwargs": {
                        "name_service_operation_type": ClbOperationType.CLB_DEREGISTER_PART_TARGET.value,
                        "cluster_id": dst_cluster.id,
                        "creator": ticket_data["created_by"],
                        "role": TenDBClusterSpiderRole.SPIDER_SLAVE,
                        "ips": dst_spider_slave_ips,
                    },
                }
            )
            # cluster_exchange_clb["destination_slave_entry_id"] = dst_slave_entrys[0].id

    elif src_cluster.cluster_type == ClusterType.TenDBHA.value:
        src_proxys = src_cluster.proxyinstance_set.filter()
        dst_proxys = dst_cluster.proxyinstance_set.filter()
        src_proxy_ips = [i.machine.ip for i in src_proxys]
        dst_proxy_ips = [i.machine.ip for i in dst_proxys]
        if len(src_master_entrys) == 1:
            if len(dst_proxy_ips) == 0:
                raise Exception(_("目标集群没有查询到 master proxy"))
            clb_add_list.append(
                {
                    "act_name": _("源集群的CLB 映射到目标集群的proxy ips"),
                    "act_component_code": MySQLClbOperationComponent.code,
                    "kwargs": {
                        "name_service_operation_type": ClbOperationType.CLB_REGISTER_PART_TARGET.value,
                        "cluster_id": src_cluster.id,
                        "creator": ticket_data["created_by"],
                        "role": None,
                        "ips": dst_proxy_ips,
                    },
                }
            )
            clb_del_list.append(
                {
                    "act_name": _("删除源集群CLB映射的ips"),
                    "act_component_code": MySQLClbOperationComponent.code,
                    "kwargs": {
                        "name_service_operation_type": ClbOperationType.CLB_DEREGISTER_PART_TARGET.value,
                        "cluster_id": src_cluster.id,
                        "creator": ticket_data["created_by"],
                        "role": None,
                        "ips": src_proxy_ips,
                    },
                }
            )
            # cluster_exchange_clb["source_master_entry_id"] = src_master_entrys[0].id
        if len(dst_master_entrys) == 1:
            if len(src_proxy_ips) == 0:
                raise Exception(_("源集群没有查询到 master proxy"))
            clb_add_list.append(
                {
                    "act_name": _("目标集群的CLB 映射到源集群的proxy ips"),
                    "act_component_code": MySQLClbOperationComponent.code,
                    "kwargs": {
                        "name_service_operation_type": ClbOperationType.CLB_REGISTER_PART_TARGET.value,
                        "cluster_id": dst_cluster.id,
                        "creator": ticket_data["created_by"],
                        "role": None,
                        "ips": src_proxy_ips,
                    },
                }
            )
            clb_del_list.append(
                {
                    "act_name": _("删除目标集群CLB映射的ips"),
                    "act_component_code": MySQLClbOperationComponent.code,
                    "kwargs": {
                        "name_service_operation_type": ClbOperationType.CLB_DEREGISTER_PART_TARGET.value,
                        "cluster_id": dst_cluster.id,
                        "creator": ticket_data["created_by"],
                        "role": None,
                        "ips": dst_proxy_ips,
                    },
                }
            )
            # cluster_exchange_clb["destination_master_entry_id"] = dst_master_entrys[0].id
    else:
        return None
    if len(clb_del_list) > 0 and len(clb_add_list) > 0:
        exchange_sub_pipeline.add_parallel_acts(acts_list=clb_del_list)
        exchange_sub_pipeline.add_parallel_acts(acts_list=clb_add_list)
        exchange_sub_pipeline.add_act(
            act_name=_("域名切换修改元数据"),
            act_component_code=MySQLDBMetaComponent.code,
            kwargs=asdict(
                DBMetaOPKwargs(
                    db_meta_class_func=MySQLDBMeta.tendb_exchange_clb.__name__,
                    cluster={"source_cluster_id": src_cluster.id, "destination_cluster_id": dst_cluster.id},
                    is_update_trans_data=False,
                )
            ),
        )
    else:
        return None
    return exchange_sub_pipeline.build_sub_process(sub_name=_("CLB域名互换"))


def rollback_users_grant(root_id: str, ticket_data: dict, src_cluster: Cluster, dst_cluster: Cluster):
    """
    回滚用户授权
    :param root_id: 根任务ID
    :param ticket_data: 工单数据
    :param src_cluster: 源集群
    :param dst_cluster: 目标集群
    :return: 用户授权子流程
    """

    user_grant_sub_pipeline = SubBuilder(root_id=root_id, data=copy.deepcopy(ticket_data))
    if src_cluster.cluster_type == ClusterType.TenDBHA.value:
        src_master = src_cluster.storageinstance_set.get(instance_inner_role=InstanceInnerRole.MASTER.value)
        dst_master = dst_cluster.storageinstance_set.get(instance_inner_role=InstanceInnerRole.MASTER.value)
        src_is_standby_slave = src_cluster.storageinstance_set.get(
            instance_inner_role=InstanceInnerRole.SLAVE.value, is_stand_by=True
        )
        dst_is_standby_slave = dst_cluster.storageinstance_set.get(
            instance_inner_role=InstanceInnerRole.SLAVE.value, is_stand_by=True
        )
        user_grant_sub_pipeline.add_parallel_sub_pipeline(
            sub_flow_list=[
                mysql_clone_grants_from_file_subflow(
                    root_id=root_id,
                    data=copy.deepcopy(ticket_data),
                    bk_cloud_id=src_cluster.bk_cloud_id,
                    bk_biz_id=src_cluster.bk_biz_id,
                    source_address=src_master.ip_port,
                    dest_addresses=[dst_master.ip_port],
                ),
                mysql_clone_grants_from_file_subflow(
                    root_id=root_id,
                    data=copy.deepcopy(ticket_data),
                    bk_cloud_id=src_cluster.bk_cloud_id,
                    bk_biz_id=src_cluster.bk_biz_id,
                    source_address=src_is_standby_slave.ip_port,
                    dest_addresses=[dst_is_standby_slave.ip_port],
                ),
            ]
        )
        # 从集群内已有 proxy 克隆用户白名单到新 proxy
        clone_user_acts_list = []
        add_proxy_user_acts_list = []
        src_proxys = src_cluster.proxyinstance_set.all()
        dst_proxys = dst_cluster.proxyinstance_set.all()
        for dst_proxy in dst_proxys:
            #  proxy 克隆报名单
            clone_user_acts_list.append(
                {
                    "act_name": _("克隆proxy用户白名单[{}:{}]".format(dst_proxy.machine.ip, dst_proxy.port)),
                    "act_component_code": CloneProxyUsersInClusterComponent.code,
                    "kwargs": asdict(
                        CloneProxyUsersKwargs(
                            cluster_id=src_cluster.id,
                            target_proxy_host=dst_proxy.machine.ip,
                        )
                    ),
                }
            )
            #  todo 在后端 MySQL 上为新 proxy 的 IP 创建访问权限 确定是否可跨集群 。需要考虑从所有src_proxy复制吗？
            add_proxy_user_acts_list.append(
                {
                    "act_name": _("集群对新的proxy添加权限[{}:{}]".format(dst_proxy.machine.ip, dst_proxy.port)),
                    "act_component_code": CloneProxyUsersInBackendComponent.code,
                    "kwargs": asdict(
                        CloneProxyClientInBackendKwargs(
                            cluster_id=dst_cluster.id,
                            target_proxy_host=dst_proxy.machine.ip,
                            origin_proxy_host=src_proxys[0].machine.ip,
                        )
                    ),
                }
            )
        user_grant_sub_pipeline.add_parallel_acts(acts_list=clone_user_acts_list)
        user_grant_sub_pipeline.add_parallel_acts(acts_list=add_proxy_user_acts_list)

    elif src_cluster.cluster_type == ClusterType.TenDBSingle:
        src_master = src_cluster.storageinstance_set.get(instance_inner_role=InstanceInnerRole.ORPHAN.value)
        dst_master = dst_cluster.storageinstance_set.get(instance_inner_role=InstanceInnerRole.ORPHAN.value)
        user_grant_sub_pipeline.add_sub_pipeline(
            sub_flow=mysql_clone_grants_from_file_subflow(
                root_id=root_id,
                data=copy.deepcopy(ticket_data),
                bk_cloud_id=src_cluster.bk_cloud_id,
                bk_biz_id=src_cluster.bk_biz_id,
                source_address=src_master.ip_port,
                dest_addresses=[dst_master.ip_port],
            )
        )
    elif src_cluster.cluster_type == ClusterType.TenDBCluster:
        src_spider_master = src_cluster.proxyinstance_set.filter(
            tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_MASTER
        ).first()
        dst_spider_masters = dst_cluster.proxyinstance_set.filter(
            tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_MASTER
        )

        if src_spider_master is None or len(dst_spider_masters) == 0:
            raise Exception(_("源集群没有查询到 spider master 或目标集群没有查询到 spider master"))

        clone_master_acts_list = []
        clone_slave_acts_list = []
        for dst_spider_master in dst_spider_masters:
            clone_master_acts_list.append(
                mysql_clone_grants_from_file_subflow(
                    root_id=root_id,
                    data=copy.deepcopy(ticket_data),
                    bk_cloud_id=src_cluster.bk_cloud_id,
                    bk_biz_id=src_cluster.bk_biz_id,
                    source_address=src_spider_master.ip_port,
                    dest_addresses=[dst_spider_master.ip_port],
                ),
            )
        src_spider_slave = src_cluster.proxyinstance_set.filter(
            tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_SLAVE
        ).first()
        dst_spider_slaves = dst_cluster.proxyinstance_set.filter(
            tendbclusterspiderext__spider_role=TenDBClusterSpiderRole.SPIDER_SLAVE
        )
        if src_spider_slave is not None:
            for dst_spider_slave in dst_spider_slaves:
                clone_slave_acts_list.append(
                    mysql_clone_grants_from_file_subflow(
                        root_id=root_id,
                        data=copy.deepcopy(ticket_data),
                        bk_cloud_id=src_cluster.bk_cloud_id,
                        bk_biz_id=src_cluster.bk_biz_id,
                        source_address=src_spider_slave.ip_port,
                        dest_addresses=[dst_spider_slave.ip_port],
                    ),
                )
        user_grant_sub_pipeline.add_parallel_acts(acts_list=clone_master_acts_list)
        if len(clone_slave_acts_list) > 0:
            user_grant_sub_pipeline.add_parallel_acts(acts_list=clone_slave_acts_list)
    else:
        raise Exception(_("不支持的集群类型"))
    return user_grant_sub_pipeline.build_sub_process(sub_name=_("授权到目标集群"))
