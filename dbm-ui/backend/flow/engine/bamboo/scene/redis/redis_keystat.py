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

from django.utils.translation import gettext as _

from backend.configuration.constants import DBType
from backend.core.encrypt.constants import AsymmetricCipherConfigType
from backend.core.encrypt.handlers import AsymmetricHandler
from backend.db_meta.api.cluster.nosqlcomm.redis_cluster_repo import DbmClusterRepository
from backend.db_meta.enums.cluster_type import ClusterType
from backend.db_meta.models.cluster import Cluster
from backend.db_proxy.constants import ExtensionType
from backend.db_proxy.models import DBCloudProxy, DBExtension
from backend.flow.consts import ConfigDefaultEnum, RedisActuatorActionEnum
from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.plugins.components.collections.redis.exec_actuator_job2 import RedisExecJobComponent2
from backend.flow.plugins.components.collections.redis.trans_flies import TransFileComponent
from backend.flow.utils.redis.redis_context_dataclass import ActKwargs, CommonContext

logger = logging.getLogger("flow")


class RedisKeystatFlow(object):
    """
    redis 内存分析统计
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递过来的参数列表，是dict格式
        """
        self.root_id = root_id
        self.data = data

    @staticmethod
    def __get_nginx_ip(bk_cloud_id: int) -> str:
        nginx_ip = DBCloudProxy.objects.filter(bk_cloud_id=bk_cloud_id).last().internal_address
        return nginx_ip

    @staticmethod
    def __get_token(bk_cloud_id: int) -> str:
        token = AsymmetricHandler.encrypt(
            name=AsymmetricCipherConfigType.PROXYPASS.value, content=f"{bk_cloud_id}_dbactuator_token"
        )
        return token

    @classmethod
    def __get_exec_ip(cls, bk_cloud_id=0) -> str:
        """
        获取Redis内存分析统计中转机器
        """
        try:
            keystat_center = DBExtension.get_latest_extension(
                bk_cloud_id=bk_cloud_id, extension_type=ExtensionType.REDIS_KEYSTAT_CENTER
            )
        except Exception as e:
            raise Exception(_(f"Get REDIS_KEYSTAT_CENTER center failed: {str(e)}"))
        return keystat_center.details["ip"]

    def run_flow(self):
        # 检查输入的记录是否合法
        cluster_ids = [info["cluster_id"] for info in self.data["infos"]]
        cluster_ids = list(set(cluster_ids))
        if len(cluster_ids) != len(self.data["infos"]):
            raise Exception("input records contain duplicate cluster_ids")

        if len(cluster_ids) == 0:
            raise Exception("input records contain no cluster_ids")

        clusters = DbmClusterRepository.fetch_many_cluster_dict(id__in=cluster_ids)
        if len(clusters) != len(cluster_ids):
            raise Exception("input records contain invalid cluster_ids")

        # 检查输入的记录是否合法
        for info in self.data["infos"]:
            cluster = clusters[info["cluster_id"]]
            if not cluster:
                raise Exception(f"cluster_id:{info['cluster_id']} not exist")

            # check bk_biz_id is the same
            if cluster.bk_biz_id != self.data["bk_biz_id"]:
                msg = f"cluster_id:{info['cluster_id']} not belong to bk_biz_id:{self.data['bk_biz_id']}, "
                raise Exception(msg + f"but belong to bk_biz_id:{cluster.bk_biz_id}")

            # check cluster type is supported
            if not ClusterType.is_memory_redis(cluster.cluster_type):
                msg = f"cluster_id:{info['cluster_id']} cluster_type:{cluster.cluster_type} not support "
                raise Exception(msg)

            # check role is supported
            # if info["role"] not in [RedisRole.MASTER.value, RedisRole.SLAVE.value]:
            #    msg = f"cluster_id:{info['cluster_id']} ins:{info['ins']} role:{info['role']} not valid"
            #    raise Exception(msg)

            # check check_last_visit is boolean
            # if info["check_last_visit"] not in [True, False]:
            #    msg = f"cluster_id:{info['cluster_id']} check_last_visit:{info['check_last_visit']} not valid"
            #    raise Exception(msg)

        bk_cloud_id = self.data["bk_cloud_id"]

        # todo add keysplitter to GetFileList
        trans_files = GetFileList(db_type=DBType.Redis)
        act_kwargs = ActKwargs()
        act_kwargs.set_trans_data_dataclass = CommonContext.__name__
        act_kwargs.file_list = trans_files.get_db_actuator_package()
        act_kwargs.is_update_trans_data = True
        act_kwargs.bk_cloud_id = bk_cloud_id

        redis_pipeline = Builder(root_id=self.root_id, data=self.data)
        # exec ip for init config
        # act_kwargs.exec_ip = self.__get_exec_ip(bk_cloud_id)
        # redis_pipeline.add_act(
        #    act_name=_("初始化配置"), act_component_code=GetRedisActPayloadComponent.code, kwargs=asdict(act_kwargs)
        # )

        # exec ip for file transfer
        act_kwargs.exec_ip = self.__get_exec_ip(cluster.bk_cloud_id)
        redis_pipeline.add_act(
            act_name=_("下发介质包"), act_component_code=TransFileComponent.code, kwargs=asdict(act_kwargs)
        )

        seen_ins = set()
        # 检查ins是否在shard中
        for info in self.data["infos"]:
            cluster = clusters[info["cluster_id"]]
            storage_list = DbmClusterRepository.fetch_storage_list(cluster_id=cluster.id)
            shard_list = DbmClusterRepository.build_shard_list_by_instance_list(storage_list)
            info["cluster_shard_num"] = len(shard_list)
            info["analyzed_shard_num"] = len(info["ins"])
            for addr in info["ins"]:
                found = False
                for shard in shard_list:
                    if len(shard["members"]) == 0:
                        logger.error(f"cluster_id:{info['cluster_id']} shard:{shard} not have members")
                        continue

                    # 按master_addr来去重. 避免同一个分片添加多次.
                    master_addr = f"{shard['members'][0]['ip']}:{shard['members'][0]['port']}"
                    if master_addr in seen_ins:
                        raise Exception(f"cluster_id:{info['cluster_id']} ins:{addr['addr']} is duplicated")

                    seen_ins.add(master_addr)
                    if addr["addr"] == master_addr:
                        found = True
                        addr["shard_name"] = shard["shard_name"]
                        if len(shard["members"]) > 1:
                            addr["slave_addr"] = f"{shard['members'][1]['ip']}:{shard['members'][1]['port']}"
                        break

                if not found:
                    raise Exception(f"cluster_id:{info['cluster_id']} ins:{addr} not in cluster")

        # 生成下发任务
        acts_list = []
        for info in self.data["infos"]:
            cluster = clusters[info["cluster_id"]]
            acts_list.append(
                {
                    "act_name": _("实例内存分析统计: {}").format(cluster.immute_domain),
                    "act_component_code": RedisExecJobComponent2.code,
                    "kwargs": self.make_kwargs(
                        cluster,
                        info,
                        exec_ip=self.__get_exec_ip(cluster.bk_cloud_id),
                        nginx_ip=self.__get_nginx_ip(cluster.bk_cloud_id),
                        db_cloud_token=self.__get_token(cluster.bk_cloud_id),
                    ),
                }
            )

        redis_pipeline.add_parallel_acts(acts_list=acts_list)
        redis_pipeline.run_pipeline()

    @classmethod
    def make_kwargs(cls, cluster: Cluster, info: dict, exec_ip: str, nginx_ip: str, db_cloud_token: str) -> dict:
        proxy_pwd = "proxy_pwd"
        redis_pwd = "redis_pwd"
        return {
            "set_trans_data_dataclass": CommonContext.__name__,
            "get_trans_data_ip_var": None,
            "bk_cloud_id": cluster.bk_cloud_id,
            "exec_ip": exec_ip,
            "db_act_template": {
                "action": RedisActuatorActionEnum.KEYSTAT.value,
                "exec_account": "root",  # 执行脚本的用户，一般是root
                "sudo_account": "root",  # 执行actuator的用户，这里必须是必须用户.
                "file_path": ConfigDefaultEnum.DATA_DIRS[0],
                "payload": {
                    "cluster_id": cluster.id,
                    "cluster_shard_num": info["cluster_shard_num"],
                    "analyzed_shard_num": info["analyzed_shard_num"],
                    "bk_cloud_id": cluster.bk_cloud_id,
                    "exec_ip": exec_ip,
                    "api_server": "http://" + nginx_ip,
                    "db_cloud_token": db_cloud_token,
                    "check_interval": 60,  # 写入流量分析检查间隔时间，单位：秒
                    "record_id": info["record_id"],
                    "proxy_pwd": proxy_pwd,
                    "redis_password": redis_pwd,
                    "ins_list": info["ins"],
                    "check_last_visit": info["check_last_visit"],
                    "delimiter": info["delimiter"],
                },
            },
        }
