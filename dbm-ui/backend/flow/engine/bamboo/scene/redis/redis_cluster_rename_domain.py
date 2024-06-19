# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""

import logging.config
from dataclasses import asdict
from typing import Dict, Optional

from django.db.models import Q
from django.utils.translation import ugettext as _

from backend.configuration.constants import DBType
from backend.db_meta.enums import ClusterEntryRole, ClusterEntryType, InstanceStatus
from backend.db_meta.models import Cluster, ClusterEntry
from backend.flow.consts import DEFAULT_REDIS_START_PORT, DnsOpType
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.redis.atom_jobs import ClusterIPsDbmonInstallAtomJob
from backend.flow.plugins.components.collections.redis.dns_manage import RedisDnsManageComponent
from backend.flow.plugins.components.collections.redis.get_redis_payload import GetRedisActPayloadComponent
from backend.flow.plugins.components.collections.redis.redis_config import RedisConfigComponent
from backend.flow.plugins.components.collections.redis.redis_db_meta import RedisDBMetaComponent
from backend.flow.utils.dns_manage import DnsManage
from backend.flow.utils.redis.redis_act_playload import RedisActPayload
from backend.flow.utils.redis.redis_context_dataclass import ActKwargs, CommonContext, DnsKwargs
from backend.flow.utils.redis.redis_db_meta import RedisDBMeta
from backend.flow.utils.redis.redis_util import domain_without_port

logger = logging.getLogger("flow")


class RedisClusterRenameDomainFlow(object):
    """
    redis集群重命名域名
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递过来的参数列表,是dict格式
        data={
            'infos':[
                { "cluster_id":44,"new_domain":"tendisplus.test01.testapp.db"},
                { "cluster_id":45,"new_domain":"tendisplus.test02.testapp.db"},
            ]
        }
        """
        self.root_id = root_id
        self.data = data
        self.precheck_all()

    def precheck_all(self):
        """
        流程前置检查
        """
        for info in self.data["infos"]:
            self.precheck_info_item(cluster_id=info["cluster_id"], new_domain=info["new_domain"])

    @staticmethod
    def precheck_info_item(cluster_id: int, new_domain: str):
        """
        检查单个集群,cluster.immute_domain、cluster_entry.entry 是否已经是new_domain
        检查 域名解析是否已经和 cluster.proxyinstance_set.all() 相同
        如果均满足,则报错
        """
        new_domain = domain_without_port(new_domain)
        cluster = Cluster.objects.get(id=cluster_id)
        if cluster.immute_domain != new_domain:
            return
        cluster_entry = ClusterEntry.objects.get(
            Q(cluster__id=cluster_id)
            & Q(cluster_entry_type=ClusterEntryType.DNS)
            & (Q(role=ClusterEntryRole.PROXY_ENTRY) | Q(role=ClusterEntryRole.MASTER_ENTRY)),
        )
        if cluster_entry.entry != new_domain:
            return
        proxy_insts_addrs = set()
        for inst in cluster.proxyinstance_set.all():
            proxy_insts_addrs.add(f"{inst.machine.ip}:{inst.port}")
        proxy_dns_addrs = set()
        dns_manage = DnsManage(bk_biz_id=cluster.bk_biz_id, bk_cloud_id=cluster.bk_cloud_id)
        for row in dns_manage.get_domain(cluster.immute_domain):
            proxy_dns_addrs.add(f"{row['ip']}:{row['port']}")
        if proxy_insts_addrs == proxy_dns_addrs:
            return
        raise Exception(_("cluster_id:{} 当前域名已经是{}，无需重命名").format(cluster_id, new_domain))

    def redis_cluster_rename_domain(self):
        redis_pipeline = Builder(root_id=self.root_id, data=self.data)
        trans_files = GetFileList(db_type=DBType.Redis)

        sub_pipelines = []
        for info in self.data["infos"]:
            new_domain = domain_without_port(info["new_domain"])
            cluster = Cluster.objects.get(id=info["cluster_id"])
            node_entry = ClusterEntry.objects.filter(
                cluster__id=cluster.id, role=ClusterEntryRole.NODE_ENTRY.value
            ).first()
            act_kwargs = ActKwargs()
            act_kwargs.set_trans_data_dataclass = CommonContext.__name__
            act_kwargs.file_list = trans_files.redis_base()
            act_kwargs.is_update_trans_data = True
            act_kwargs.bk_cloud_id = cluster.bk_cloud_id

            sub_pipeline = SubBuilder(root_id=self.root_id, data=self.data)

            sub_pipeline.add_act(
                act_name=_("初始化配置"),
                act_component_code=GetRedisActPayloadComponent.code,
                kwargs=asdict(act_kwargs),
            )

            cluster_running_ips = set()
            meta_proxy_ips = []
            meta_storage_ips = set()
            for inst in cluster.proxyinstance_set.filter(status=InstanceStatus.RUNNING):
                meta_proxy_ips.append(f"{inst.machine.ip}")
                cluster_running_ips.add(f"{inst.machine.ip}")
            meta_proxy_port = cluster.proxyinstance_set.first().port

            for inst in cluster.storageinstance_set.filter(status=InstanceStatus.RUNNING):
                cluster_running_ips.add(f"{inst.machine.ip}")
                meta_storage_ips.add(f"{inst.machine.ip}")

            act_kwargs.cluster["meta_func_name"] = RedisDBMeta.redis_cluster_rename_domain.__name__
            act_kwargs.cluster["cluster_id"] = info["cluster_id"]
            act_kwargs.cluster["new_domain"] = new_domain
            sub_pipeline.add_act(
                act_name=_("更新元数据和cc模块"),
                act_component_code=RedisDBMetaComponent.code,
                kwargs=asdict(act_kwargs),
            )

            act_kwargs.cluster = {
                "bill_id": self.data["uid"],
                "cluster_id": cluster.id,
                "old_domain": cluster.immute_domain,
                "new_domain": new_domain,
            }
            act_kwargs.get_redis_payload_func = RedisActPayload.redis_custer_rename_domain_update_dbconfig.__name__
            sub_pipeline.add_act(
                act_name=_("更新集群dbconfig配置"),
                act_component_code=RedisConfigComponent.code,
                kwargs=asdict(act_kwargs),
            )

            dns_proxy_ips = []
            dns_proxy_port = 0
            dns_manage = DnsManage(bk_biz_id=cluster.bk_biz_id, bk_cloud_id=cluster.bk_cloud_id)
            for row in dns_manage.get_domain(cluster.immute_domain):
                dns_proxy_ips.append(f"{row['ip']}")
                dns_proxy_port = row["port"]

            dns_kwargs = DnsKwargs(
                dns_op_type=DnsOpType.RECYCLE_RECORD,
                dns_op_exec_port=dns_proxy_port,
            )
            act_kwargs.exec_ip = dns_proxy_ips
            sub_pipeline.add_act(
                act_name=_("删除旧域名记录{}").format(cluster.immute_domain),
                act_component_code=RedisDnsManageComponent.code,
                kwargs={**asdict(act_kwargs), **asdict(dns_kwargs)},
            )
            if node_entry:
                # 如果有nodes域名,则先删除
                dns_storage_ips = []
                dns_storage_port = 0
                for row in dns_manage.get_domain(node_entry.entry):
                    dns_storage_ips.append(f"{row['ip']}")
                    dns_storage_port = row["port"]
                dns_kwargs = DnsKwargs(
                    dns_op_type=DnsOpType.RECYCLE_RECORD,
                    dns_op_exec_port=dns_storage_port,
                )
                act_kwargs.exec_ip = dns_storage_ips
                sub_pipeline.add_act(
                    act_name=_("删除旧nodes域名记录{}").format(node_entry.entry),
                    act_component_code=RedisDnsManageComponent.code,
                    kwargs={**asdict(act_kwargs), **asdict(dns_kwargs)},
                )

            dns_kwargs = DnsKwargs(
                dns_op_type=DnsOpType.CREATE,
                add_domain_name=new_domain,
                dns_op_exec_port=meta_proxy_port,
            )
            act_kwargs.exec_ip = meta_proxy_ips
            sub_pipeline.add_act(
                act_name=_("添加新域名记录{}").format(new_domain),
                act_component_code=RedisDnsManageComponent.code,
                kwargs={**asdict(act_kwargs), **asdict(dns_kwargs)},
            )

            if node_entry:
                # 如果有nodes域名,再添加
                dns_kwargs = DnsKwargs(
                    dns_op_type=DnsOpType.CREATE,
                    add_domain_name="nodes." + new_domain,
                    dns_op_exec_port=DEFAULT_REDIS_START_PORT,
                )
                act_kwargs.exec_ip = list(meta_storage_ips)
                sub_pipeline.add_act(
                    act_name=_("添加新域名记录{}").format("nodes." + new_domain),
                    act_component_code=RedisDnsManageComponent.code,
                    kwargs={**asdict(act_kwargs), **asdict(dns_kwargs)},
                )

            # 集群所有节点,重装bkdbmon
            params = {
                "cluster_domain": new_domain,
                "ips": list(cluster_running_ips),
                "is_stop": False,
            }
            dbmon_builfer = ClusterIPsDbmonInstallAtomJob(self.root_id, self.data, act_kwargs, params)
            sub_pipeline.add_sub_pipeline(sub_flow=dbmon_builfer)
            sub_pipelines.append(
                sub_pipeline.build_sub_process(_("集群:{}重命名域名为{}").format(cluster.id, cluster.immute_domain))
            )

        redis_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        redis_pipeline.run_pipeline()
