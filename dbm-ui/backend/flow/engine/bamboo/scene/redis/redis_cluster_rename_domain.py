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
from backend.db_meta.enums import ClusterEntryRole, ClusterEntryType
from backend.db_meta.models import Cluster, ClusterEntry
from backend.flow.consts import DnsOpType
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.redis.dns_manage import RedisDnsManageComponent
from backend.flow.plugins.components.collections.redis.get_redis_payload import GetRedisActPayloadComponent
from backend.flow.plugins.components.collections.redis.redis_db_meta import RedisDBMetaComponent
from backend.flow.utils.dns_manage import DnsManage
from backend.flow.utils.redis.redis_context_dataclass import ActKwargs, CommonContext, DnsKwargs
from backend.flow.utils.redis.redis_db_meta import RedisDBMeta

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
        self.precheck()

    def precheck(self):
        """
        流程前置检查
        """
        for info in self.data["infos"]:
            cluster = Cluster.objects.get(id=info["cluster_id"])
            if cluster.immute_domain != info["new_domain"]:
                continue
            cluster_entry = ClusterEntry.objects.get(
                Q(cluster__id=info["cluster_id"])
                & Q(cluster_entry_type=ClusterEntryType.DNS)
                & (Q(role=ClusterEntryRole.PROXY_ENTRY) | Q(role=ClusterEntryRole.MASTER_ENTRY)),
            )
            if cluster_entry.entry != info["new_domain"]:
                continue
            proxy_insts_addrs = set()
            for inst in cluster.proxyinstance_set.all():
                proxy_insts_addrs.add(f"{inst.machine.ip}:{inst.port}")
            proxy_domain_addrs = set()
            dns_manage = DnsManage(bk_biz_id=cluster.bk_biz_id, bk_cloud_id=cluster.bk_cloud_id)
            for row in dns_manage.get_domain(cluster.immute_domain):
                proxy_domain_addrs.add(f"{row['ip']}:{row['port']}")
            if proxy_insts_addrs == proxy_domain_addrs:
                continue
            raise Exception(_("cluster_id:{} 当前域名已经是{}，无需重命名").format(info["cluster_id"], info["new_domain"]))

    def redis_cluster_rename_domain(self):
        redis_pipeline = Builder(root_id=self.root_id, data=self.data)
        trans_files = GetFileList(db_type=DBType.Redis)

        sub_pipelines = []
        for info in self.data["infos"]:
            act_kwargs = ActKwargs()
            act_kwargs.set_trans_data_dataclass = CommonContext.__name__
            act_kwargs.file_list = trans_files.redis_base()
            act_kwargs.is_update_trans_data = True
            act_kwargs.bk_cloud_id = self.data["bk_cloud_id"]

            sub_pipeline = SubBuilder(root_id=self.root_id, data=self.data)

            sub_pipeline.add_act(
                act_name=_("初始化配置"),
                act_component_code=GetRedisActPayloadComponent.code,
                kwargs=asdict(act_kwargs),
            )

            cluster = Cluster.objects.get(id=info["cluster_id"])
            proxy_ips = []
            for inst in cluster.proxyinstance_set.all():
                proxy_ips.append(f"{inst.machine.ip}")
            proxy_port = cluster.proxyinstance_set.first().port
            dns_kwargs = DnsKwargs(
                dns_op_type=DnsOpType.RECYCLE_RECORD,
                dns_op_exec_port=proxy_port,
            )
            act_kwargs.exec_ip = proxy_ips

            sub_pipeline.add_act(
                act_name=_("删除旧记录{}").format(cluster.immute_domain),
                act_component_code=RedisDnsManageComponent.code,
                kwargs={**asdict(act_kwargs), **asdict(dns_kwargs)},
            )

            dns_kwargs = DnsKwargs(
                dns_op_type=DnsOpType.CREATE,
                add_domain_name=info["new_domain"],
                dns_op_exec_port=proxy_port,
            )
            act_kwargs.exec_ip = proxy_ips
            sub_pipeline.add_act(
                act_name=_("添加记录{}").format(info["new_domain"]),
                act_component_code=RedisDnsManageComponent.code,
                kwargs={**asdict(act_kwargs), **asdict(dns_kwargs)},
            )

            act_kwargs.cluster["meta_func_name"] = RedisDBMeta.redis_cluster_rename_domain.__name__
            act_kwargs.cluster["cluster_id"] = info["cluster_id"]
            act_kwargs.cluster["new_domain"] = info["new_domain"]
            sub_pipeline.add_act(
                act_name=_("更新元数据"),
                act_component_code=RedisDBMetaComponent.code,
                kwargs=asdict(act_kwargs),
            )
            sub_pipelines.append(sub_pipeline.build_sub_process(sub_name=_("集群域名{}重命名").format(cluster.immute_domain)))
        redis_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        redis_pipeline.run_pipeline()
