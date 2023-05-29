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
from collections import defaultdict
from dataclasses import asdict
from typing import Any, Dict, Optional

from django.utils.translation import ugettext as _

from backend.components import DBConfigApi
from backend.components.dbconfig.constants import FormatType, LevelName
from backend.configuration.constants import DBType
from backend.constants import IP_PORT_DIVIDER
from backend.db_meta import api
from backend.db_meta.enums import ClusterType, InstanceRole
from backend.db_meta.models import Cluster
from backend.db_services.redis.util import is_twemproxy_proxy_type
from backend.flow.consts import DEFAULT_DB_MODULE_ID
from backend.flow.engine.bamboo.scene.common.builder import Builder, SubBuilder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.redis.redis_slots_migrate_sub import (
    redis_migrate_slots_4_contraction,
    redis_rebalance_slots_4_expansion,
    redis_specifed_slots_migrate,
)
from backend.flow.plugins.components.collections.redis.get_redis_payload import GetRedisActPayloadComponent
from backend.flow.utils.base.payload_handler import PayloadHandler
from backend.flow.utils.redis.redis_context_dataclass import ActKwargs, CommonContext

logger = logging.getLogger("flow")


class RedisSlotsMigrateFlow(object):
    """
        ## redis slots migrate :tendisplus 扩缩容和解决热点key迁移
    {
        "bk_biz_id": 3,
        "uid": "2022051612120001",
        "created_by":"admin",
        "ticket_type":"REDIS_SLOTS_MIGRATE",
        "infos": [
                {
                    "cluster_id": 10,
                    "bk_cloud_id": 0,
                    "src_node": {
                        "ip": "a.0.0.1",
                        "port":40000,
                        "password": "redisPassTest"
                    },
                    "dst_node": {
                        "ip": "a.0.0.1",
                        "port":47001,
                        "password": "redisPassTest"
                    },
                    "is_delete_node":true,
                    "migrate_specified_slot":false,
                    "slots":"0-100"

                }
        ]
    }
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递过来的参数列表，是dict格式
        """
        self.root_id = root_id
        self.data = data

    def redis_slots_migrate_for_hotkey_flow(self):
        """
        slots 迁移,迁移热点key解决倾斜问题：
            直接调度迁移actuator
        /apis/v1/flow/scene/redis_slots_migrate

         {
        "bk_biz_id": 3,
        "uid": "2022051612120001",
        "created_by":"admin",
        "ticket_type":"REDIS_SLOTS_MIGRATE",
        "infos": [
            {
            "cluster_id": 12,
            "bk_cloud_id": 0,
            "batch_migrate":[
                {
                    "slots":"12015-13653",
                    "src_node": "xx.xx.xx.xx:30002",
                    "dst_node": "xx.xx.xx.xx:30000"
                },
                {
                    "slots":"10378-10922",
                    "src_node": "xx.xx.xx.xx:30002",
                    "dst_node": "xx.xx.xx.xx:30001"
                }

            ]
           }

        ]
        }
        """

        redis_pipeline_all = Builder(root_id=self.root_id, data=self.data)

        sub_pipelines_multi_cluster = []
        # 支持多集群操作
        for info in self.data["infos"]:
            redis_pipeline, act_kwargs = self.__init_builder(_("REDIS_SLOTS_MIGRATE"), info)
            if act_kwargs.cluster["cluster_type"] != ClusterType.TendisPredixyTendisplusCluster.value:
                raise NotImplementedError("Not supported cluster type: %s" % act_kwargs.cluster["cluster_type"])
            flow_data = self.data
            sub_pipelines_migrate = []
            for migrate_info in info["batch_migrate"]:
                # 判断是否是迁移特定的slots,slots不为空
                if migrate_info["slots"] is not None:
                    migrate_slots_pipe = redis_specifed_slots_migrate(
                        self.root_id, flow_data, act_kwargs, migrate_info
                    )
                    sub_pipelines_migrate.append(migrate_slots_pipe)
            # 并发执行
            redis_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines_migrate)

            sub_pipelines_multi_cluster.append(
                redis_pipeline.build_sub_process(sub_name=_("{}slots 迁移").format(act_kwargs.cluster["immute_domain"]))
            )

        redis_pipeline_all.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines_multi_cluster)
        redis_pipeline_all.run_pipeline()

    def redis_migrate_4_expansion_flow(self):
        """
            扩容：
            部署redis -》 建立集群关系和做主从 -》 集群reblance（迁移slots扩容）-》 元数据加入集群 -》 刷新predixy配置文件
            -> 写入扩缩容表
            /apis/v1/flow/scene/redis_slots_migrate_for_expansion

           {
            "bk_biz_id": 3,
            "uid": "2022051612120001",
            "created_by":"admin",
            "ticket_type":"REDIS_SLOTS_MIGRATE",
            "infos": [
                {
                "cluster_id": 12,
                "bk_cloud_id": 0,
                "current_group_num": 1,
                "target_group_num": 2,
                "new_ip_group":[
                    {
                        "master":"aa.bb.cc.dd",
                        "slave":"xx.bb.cc.dd"
                    }

                ],
             "resource_spec": {
                "redis": {
                    "id": 1}}
               }

            ]
        }
        """

        redis_pipeline_all = Builder(root_id=self.root_id, data=self.data)

        sub_pipelines_multi_cluster = []
        # 支持多集群操作
        for info in self.data["infos"]:
            redis_pipeline, act_kwargs = self.__init_builder(_("REDIS_SLOTS_MIGRATE"), info)
            if act_kwargs.cluster["cluster_type"] != ClusterType.TendisPredixyTendisplusCluster.value:
                raise NotImplementedError("Not supported cluster type: %s" % act_kwargs.cluster["cluster_type"])
            flow_data = self.data
            # 扩容,传入的新ip组大于0,target_group_num大于current_group_num
            if len(info["new_ip_group"]) > 0 and (info["target_group_num"] - info["current_group_num"]) > 0:
                expansion_pipe = redis_rebalance_slots_4_expansion(self.root_id, flow_data, act_kwargs, info)
                redis_pipeline.add_sub_pipeline(expansion_pipe)

            sub_pipelines_multi_cluster.append(
                redis_pipeline.build_sub_process(sub_name=_("{}slots迁移扩容").format(act_kwargs.cluster["immute_domain"]))
            )

        redis_pipeline_all.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines_multi_cluster)
        redis_pipeline_all.run_pipeline()

    def redis_migrate_4_contraction_flow(self):
        """
             缩容:
             根据传入的节点数得到待删除的instance -> slots 迁移 -> predixy 配置刷新(去掉缩容的节点) -> 节点下架&删除元数据
             -> 写入扩缩容表
            /apis/v1/flow/scene/redis_slots_migrate_for_contraction

        {
             "bk_biz_id": 3,
             "uid": "2022051612120001",
             "created_by":"admin",
             "ticket_type":"REDIS_SLOTS_MIGRATE",
             "infos": [
                 {
                 "cluster_id": 12,
                 "bk_cloud_id": 0,
                 "is_delete_node":true,
                 "current_group_num": 2,
                 "target_group_num": 1
                 }
             ]
         }
        """

        redis_pipeline_all = Builder(root_id=self.root_id, data=self.data)

        sub_pipelines_multi_cluster = []
        # 支持多集群操作
        for info in self.data["infos"]:
            redis_pipeline, act_kwargs = self.__init_builder(_("REDIS_SLOTS_MIGRATE"), info)
            if act_kwargs.cluster["cluster_type"] != ClusterType.TendisPredixyTendisplusCluster.value:
                raise NotImplementedError("Not supported cluster type: %s" % act_kwargs.cluster["cluster_type"])
            flow_data = self.data
            # 缩容，删除node是true
            if info["is_delete_node"] and (info["target_group_num"] - info["current_group_num"]) < 0:
                contraction_pipe = redis_migrate_slots_4_contraction(self.root_id, flow_data, act_kwargs, info)
                redis_pipeline.add_sub_pipeline(contraction_pipe)
            sub_pipelines_multi_cluster.append(
                redis_pipeline.build_sub_process(sub_name=_("{}slots 迁移").format(act_kwargs.cluster["immute_domain"]))
            )

        redis_pipeline_all.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines_multi_cluster)
        redis_pipeline_all.run_pipeline()

    def __get_cluster_info(self, bk_biz_id: int, cluster_id: int) -> dict:
        """获取集群现有信息
        1. master 对应 slave 机器
        2. master 上的端口列表
        3. 实例对应关系：{master:port:slave:port}
        """
        cluster = Cluster.objects.get(id=cluster_id, bk_biz_id=bk_biz_id)

        master_ports, slave_ports = defaultdict(list), defaultdict(list)
        ins_pair_map, slave_ins_map = defaultdict(), defaultdict()
        master_slave_map, slave_master_map = defaultdict(), defaultdict()

        for master_obj in cluster.storageinstance_set.filter(instance_role=InstanceRole.REDIS_MASTER.value):
            slave_obj = master_obj.as_ejector.get().receiver
            master_ports[master_obj.machine.ip].append(master_obj.port)
            slave_ports[slave_obj.machine.ip].append(slave_obj.port)
            ins_pair_map["{}{}{}".format(master_obj.machine.ip, IP_PORT_DIVIDER, master_obj.port)] = "{}{}{}".format(
                slave_obj.machine.ip, IP_PORT_DIVIDER, slave_obj.port
            )

            ifslave = master_slave_map.get(master_obj.machine.ip)
            if ifslave and ifslave != slave_obj.machine.ip:
                raise Exception(
                    "unsupport mutil slave with cluster {} 4:{}".format(cluster.immute_domain, master_obj.machine.ip)
                )
            else:
                master_slave_map[master_obj.machine.ip] = slave_obj.machine.ip

            slave_ins_map["{}{}{}".format(slave_obj.machine.ip, IP_PORT_DIVIDER, slave_obj.port)] = "{}{}{}".format(
                master_obj.machine.ip, IP_PORT_DIVIDER, master_obj.port
            )

            ifmaster = slave_master_map.get(slave_obj.machine.ip)
            if ifmaster and ifmaster != master_obj.machine.ip:
                raise Exception(
                    "unsupport mutil master for cluster {}:{}".format(cluster.immute_domain, slave_obj.machine.ip)
                )
            else:
                slave_master_map[slave_obj.machine.ip] = master_obj.machine.ip

            cluster_info = api.cluster.nosqlcomm.other.get_cluster_detail(cluster_id)[0]

            cluster_name = cluster_info["name"]
            cluster_type = cluster_info["cluster_type"]
            redis_master_set = cluster_info["redis_master_set"]
            redis_slave_set = cluster_info["redis_slave_set"]
            servers = []
            if is_twemproxy_proxy_type(cluster_type):
                for seg in redis_master_set:
                    ip_port, seg_range = str.split(seg)
                    servers.append("{} {} {} {}".format(ip_port, cluster_name, seg_range, 1))
            else:
                servers = redis_master_set + redis_slave_set
            master_ip = list(set([ip.split(":")[0] for ip in redis_master_set]))

            passwd_ret = PayloadHandler.redis_get_password_by_domain(cluster.immute_domain)
            password = passwd_ret.get("redis_password")

        return {
            "immute_domain": cluster.immute_domain,
            "bk_biz_id": str(cluster.bk_biz_id),
            "bk_cloud_id": cluster.bk_cloud_id,
            "cluster_type": cluster.cluster_type,
            "cluster_name": cluster.name,
            "cluster_id": cluster.id,
            "slave_ports": dict(slave_ports),
            "master_ports": dict(master_ports),
            "ins_pair_map": dict(ins_pair_map),
            "slave_ins_map": dict(slave_ins_map),
            "slave_master_map": dict(slave_master_map),
            "master_slave_map": dict(master_slave_map),
            "proxy_port": cluster.proxyinstance_set.first().port,
            "proxy_ips": [proxy_obj.machine.ip for proxy_obj in cluster.proxyinstance_set.all()],
            "db_version": cluster.major_version,
            "backend_servers": servers,
            "redis_master": redis_master_set,
            "master_ip": master_ip,
            "password": password,
        }

    def __init_builder(self, operate_name: str, info: dict):

        cluster_info = self.__get_cluster_info(self.data["bk_biz_id"], info["cluster_id"])
        logger.info("+===+++++===cluster_info+++++===++++ :: {}".format(cluster_info))

        flow_data = self.data
        flow_data.update(cluster_info)

        redis_pipeline = SubBuilder(root_id=self.root_id, data=flow_data)
        trans_files = GetFileList(db_type=DBType.Redis)
        act_kwargs = ActKwargs()
        act_kwargs.set_trans_data_dataclass = CommonContext.__name__
        act_kwargs.file_list = trans_files.redis_base()
        act_kwargs.is_update_trans_data = True
        act_kwargs.cluster = {
            **cluster_info,
            "operate": operate_name,
        }
        act_kwargs.bk_cloud_id = cluster_info["bk_cloud_id"]
        logger.info("+===+++++===current tick_data info+++++===++++ :: {}".format(act_kwargs))

        redis_pipeline.add_act(
            act_name=_("初始化配置"), act_component_code=GetRedisActPayloadComponent.code, kwargs=asdict(act_kwargs)
        )

        return redis_pipeline, act_kwargs

    def __get_cluster_config(self, domain_name: str, db_version: str, conf_type: str, namespace: str) -> Any:
        """
        获取已部署的实例配置
        """
        data = DBConfigApi.query_conf_item(
            params={
                "bk_biz_id": str(self.data["bk_biz_id"]),
                "level_name": LevelName.CLUSTER,
                "level_value": domain_name,
                "level_info": {"module": str(DEFAULT_DB_MODULE_ID)},
                "conf_file": db_version,
                "conf_type": conf_type,
                "namespace": namespace,
                "format": FormatType.MAP,
            }
        )
        return data["content"]
