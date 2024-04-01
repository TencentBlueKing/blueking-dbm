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

import json
import logging.config
import operator
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Tuple

from django.utils import timezone
from django.utils.translation import ugettext as _

from backend import env
from backend.components import DRSApi
from backend.db_meta.enums import InstanceRole
from backend.db_meta.models import Cluster
from backend.db_services.redis.maxmemory_set.models import TbTendisMaxmemoryBackends
from backend.db_services.redis.redis_dts.models import TbTendisDtsTask
from backend.db_services.redis.util import is_redis_instance_type
from backend.flow.consts import ConfigFileEnum, ConfigTypeEnum, NameSpaceEnum
from backend.flow.engine.bamboo.scene.redis.redis_cluster_maxmemory_set import RedisClusterMaxmemorySetSceneFlow
from backend.flow.utils.base.payload_handler import PayloadHandler
from backend.flow.utils.redis.redis_act_playload import RedisActPayload
from backend.flow.utils.redis.redis_util import decode_info_cmd, humanbytes, parse_human_size
from backend.ticket.constants import TicketType
from backend.utils.basic import generate_root_id

logger = logging.getLogger("flow")


class RedisClusterMaxmemorySet:
    """
    redis集群 maxmemory_set 配置
    """

    def __init__(self, cluster_id: int, creator: str = "admin"):
        self.cluster_id = cluster_id
        self.creator = creator
        self.master_addrs = []
        self.masters_used_memory = {}
        self.master_ip_ports = defaultdict(list)

        self.bk_biz_id_blacklist = set()
        self.domain_blacklist = set()
        self.used_memory_change_threshold = 0
        self.used_memory_change_percent = 0

        self.cluster: Cluster = None

    def get_cluster_data(self):
        self.cluster = Cluster.objects.get(id=self.cluster_id)
        self.bk_biz_id = self.cluster.bk_biz_id
        self.cluster_password = PayloadHandler.redis_get_cluster_password(self.cluster)

    def get_maxmemory_set_config(self):
        maxmemory_set_config = RedisActPayload.get_common_config(
            bk_biz_id=str(env.DBA_APP_BK_BIZ_ID),
            namespace=NameSpaceEnum.RedisCommon,
            conf_file=ConfigFileEnum.MaxMemorySet,
            conf_type=ConfigTypeEnum.Config,
        )
        if not maxmemory_set_config:
            return

        for item in maxmemory_set_config["bk_biz_id_blacklist"].replace(";", ",").split(","):
            item.strip()
            if item:
                self.bk_biz_id_blacklist.add(int(item))
        for item in maxmemory_set_config["domains_blacklist"].replace(";", ",").split(","):
            item.strip()
            if item:
                self.domain_blacklist.add(item)
        self.used_memory_change_percent = int(maxmemory_set_config.get("master_used_memory_change_percent", 20))
        threshold = maxmemory_set_config.get("master_used_memory_change_threshold", "200MB")
        self.used_memory_change_threshold = parse_human_size(threshold)

    def get_cluster_masters_used_memory(self):
        self.master_addrs = []
        self.master_ip_ports = defaultdict(list)
        for master_obj in self.cluster.storageinstance_set.filter(instance_role=InstanceRole.REDIS_MASTER.value):
            self.master_addrs.append("{}:{}".format(master_obj.machine.ip, master_obj.port))
            self.master_ip_ports[master_obj.machine.ip].append(master_obj.port)
        resp = DRSApi.redis_rpc(
            {
                "addresses": self.master_addrs,
                "db_num": 0,
                "password": self.cluster_password.get("redis_password"),
                "command": "info memory",
            }
        )
        self.masters_used_memory = {}
        for item in resp:
            info_ret = decode_info_cmd(item["result"])
            if "used_memory" in info_ret:
                self.masters_used_memory[item["address"]] = int(info_ret["used_memory"])

    def is_dts_task_dst_cluster(self):
        current_time = datetime.now(timezone.utc).astimezone()
        thirty_days_ago = current_time - timedelta(days=30)
        return TbTendisDtsTask.objects.filter(
            dst_cluster__startswith=self.cluster.immute_domain, status=1, update_time__gt=thirty_days_ago
        ).exists()

    def is_skip_maxmemory_set(self) -> Tuple[bool, str]:
        msg = ""
        if self.cluster.bk_biz_id in self.bk_biz_id_blacklist:
            msg = _("bk_biz_id {} in blacklist,skip maxmemory set").format(self.cluster.bk_biz_id)
            logger.info(msg)
            return True, msg
        if self.cluster.immute_domain in self.domain_blacklist:
            msg = _("domain {} in blacklist,skip maxmemory set").format(self.cluster.immute_domain)
            logger.info(msg)
            return True, msg
        if not is_redis_instance_type(self.cluster.cluster_type):
            msg = _("cluster {} cluster_type:{} is not redis instance,skip maxmemory set").format(
                self.cluster.immute_domain, self.cluster.cluster_type
            )
            logger.info(msg)
            return True, msg
        if self.is_dts_task_dst_cluster():
            msg = _("cluster {} is dts task dstCluster,skip maxmemory set").format(self.cluster.immute_domain)
            logger.info(msg)
            return True, msg
        return False, ""

    def save_cluster_backends(self):
        """
        将最新的 masters used_memory 写入到数据库
        """
        backends_row = TbTendisMaxmemoryBackends.objects.filter(cluster_domain=self.cluster.immute_domain).first()
        if not backends_row:
            backends_row = TbTendisMaxmemoryBackends()
            backends_row.cluster_domain = self.cluster.immute_domain
            backends_row.backends = json.dumps(self.masters_used_memory)
            backends_row.update_time = datetime.now(timezone.utc)
            backends_row.save()
        else:
            backends_row.backends = json.dumps(self.masters_used_memory)
            backends_row.update_time = datetime.now(timezone.utc)
            backends_row.save()

    # 是否满足更新cluster maxmemory的条件
    def should_update_cluter_maxmemory(self) -> Tuple[bool, str]:
        old_backends_row = TbTendisMaxmemoryBackends.objects.filter(cluster_domain=self.cluster.immute_domain).first()
        if not old_backends_row:
            return True, _("首次通过外围程序设置maxmemory")
        # 判断master addrs是否变化
        # 先从 old_backends_row.backends 中解析出 master addrs
        old_master_addrs = []
        old_masters_used_memory = json.loads(old_backends_row.backends)
        for k in old_masters_used_memory.keys():
            old_master_addrs.append(k)
        # old_master_addrs 和 self.master_addrs 排序后比较
        sortd_old_master_addrs = sorted(old_master_addrs)
        sortd_new_master_addrs = sorted(self.master_addrs)
        if not operator.eq(sortd_new_master_addrs, sortd_old_master_addrs):
            return True, _("集群 master addrs 发生变化")
        # 判断每个master的used_memory是否发生变化
        for master_addr in self.master_addrs:
            old_used_memory = old_masters_used_memory[master_addr]
            new_used_memory = self.masters_used_memory[master_addr]
            diff_mem = new_used_memory - old_used_memory
            sign_str = "+"
            if diff_mem < 0:
                sign_str = "-"
            if abs(diff_mem) > self.used_memory_change_threshold:
                return True, _("集群master {} 的 used_memory变化了 {}{}").format(
                    master_addr, sign_str, humanbytes(abs(diff_mem))
                )
            diffPercent = abs(diff_mem) * 100 / old_used_memory
            if diffPercent > self.used_memory_change_percent:
                return True, _("集群master {} 的 used_memory变化了 {}{}%").format(master_addr, sign_str, diffPercent)
        return False, _("集群master 的 used_memory没有发生变化")

    def letus_update_maxmemory(self):
        self.get_cluster_data()
        self.get_maxmemory_set_config()
        skip, msg = self.is_skip_maxmemory_set()
        if skip:
            return
        self.get_cluster_masters_used_memory()
        should_update, msg = self.should_update_cluter_maxmemory()
        if not should_update:
            return
        self.save_cluster_backends()
        root_id = generate_root_id()
        ticket_data: dict = {
            "uid": "180",
            "created_by": self.creator,
            "bk_biz_id": self.cluster.bk_biz_id,
            "bk_cloud_id": self.cluster.bk_cloud_id,
            "cluster_ids": [self.cluster.id],
            "ticket_type": TicketType.REDIS_CLUSTER_MAXMEMORY_SET.value,
        }
        flow = RedisClusterMaxmemorySetSceneFlow(root_id=root_id, data=ticket_data)
        flow.batch_clusters_maxmemory_set()
