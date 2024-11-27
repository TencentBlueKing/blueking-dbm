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
from typing import Dict, Optional

from backend.configuration.constants import DBType
from backend.db_meta.enums import AccessLayer
from backend.db_meta.models import Machine, ProxyInstance, StorageInstance
from backend.flow.engine.bamboo.scene.common.builder import Builder
from backend.flow.engine.bamboo.scene.common.get_file_list import GetFileList
from backend.flow.engine.bamboo.scene.redis.atom_jobs import DirtyProxyMachineClear, DirtyRedisMachineClear
from backend.flow.utils.redis.redis_context_dataclass import ActKwargs, CommonContext

logger = logging.getLogger("flow")


class DirtyMachineClearFlow(Builder):
    """
    脏机清理流程
    """

    def __init__(self, root_id: str, data: Optional[Dict]):
        """
        @param root_id : 任务流程定义的root_id
        @param data : 单据传递过来的参数列表,是dict格式
        """
        self.root_id = root_id
        self.data = data
        self.precheck()

    def precheck(self):
        for host in self.data["clear_hosts"]:
            ip = host["ip"]
            proxy_inst = ProxyInstance.objects.filter(
                machine__ip=ip, machine__bk_cloud_id=self.data["bk_cloud_id"]
            ).first()
            storage_inst = StorageInstance.objects.filter(
                machine__ip=ip, machine__bk_cloud_id=self.data["bk_cloud_id"]
            ).first()

            if not proxy_inst and not storage_inst:
                # 如果不是redis proxy 和redis storage实例对应的机器,则报错
                logger.error(f"ip:{ip} is not proxy or storage instance")
                raise Exception(f"ip:{ip} is not proxy or storage instance")
            if proxy_inst:
                # 如果是proxy机器,其上任意实例属于某个集群,则报错
                for proxy_inst in ProxyInstance.objects.filter(
                    machine__ip=ip, machine__bk_cloud_id=self.data["bk_cloud_id"]
                ):
                    cluster = proxy_inst.cluster.first()
                    if cluster:
                        logger.error(
                            "ip:{} is  proxy instance and belong to cluster:{}".format(ip, cluster.immute_domain)
                        )
                        raise Exception(
                            "ip:{} is  proxy instance and belong to cluster:{}".format(ip, cluster.immute_domain)
                        )
            if storage_inst:
                # 如果是storage机器,其上任意实例属于某个集群,则报错
                for storage_inst in StorageInstance.objects.filter(
                    machine__ip=ip, machine__bk_cloud_id=self.data["bk_cloud_id"]
                ):
                    cluster = storage_inst.cluster.first()
                    if cluster:
                        logger.error(
                            "ip:{} is  storage instance and belong to cluster:{}".format(ip, cluster.immute_domain)
                        )

    def dirty_machine_clear_flow(self):
        """
        脏机器清理元数据和进程
        self.data:{
            "bk_biz_id": 1,
            "bk_cloud_id":0,
            "only_clear_dbmeta":True/False,
            "force": True/False,
            "clear_hosts":[
                {"ip":"a.a.a.a"},
            ]
        }
        """
        # 加个前置检查，以免误删。
        self.precheck_4_clean()

        redis_pipeline = Builder(root_id=self.root_id, data=self.data)
        trans_files = GetFileList(db_type=DBType.Redis)
        act_kwargs = ActKwargs()
        act_kwargs.set_trans_data_dataclass = CommonContext.__name__
        act_kwargs.file_list = trans_files.redis_base()
        act_kwargs.is_update_trans_data = True
        act_kwargs.bk_cloud_id = self.data["bk_cloud_id"]

        sub_pipelines = []
        for host in self.data["clear_hosts"]:
            ip = host["ip"]
            params = {
                "ip": ip,
                "force": self.data.get("force", False),
                "only_clear_dbmeta": self.data.get("only_clear_dbmeta", False),
            }
            proxy_inst = ProxyInstance.objects.filter(
                machine__ip=ip, machine__bk_cloud_id=self.data["bk_cloud_id"], bk_biz_id=self.data["bk_biz_id"]
            ).first()
            storage_inst = StorageInstance.objects.filter(
                machine__ip=ip, machine__bk_cloud_id=self.data["bk_cloud_id"], bk_biz_id=self.data["bk_biz_id"]
            ).first()
            if proxy_inst:
                sub_builder = DirtyProxyMachineClear(
                    root_id=self.root_id, ticket_data=self.data, sub_kwargs=act_kwargs, param=params
                )
                sub_pipelines.append(sub_builder)
            if storage_inst:
                sub_builder = DirtyRedisMachineClear(
                    root_id=self.root_id, ticket_data=self.data, sub_kwargs=act_kwargs, param=params
                )
                sub_pipelines.append(sub_builder)
        if sub_pipelines:
            redis_pipeline.add_parallel_sub_pipeline(sub_flow_list=sub_pipelines)
        redis_pipeline.run_pipeline()

    def precheck_4_clean(self):
        """
        元数据前置检查：
        1. 不能属于任何集群
        2. 必须传入正确的 bizID 和 IP
        """
        for host in self.data["clear_hosts"]:
            ip = host["ip"]
            try:
                host_obj = Machine.objects.get(
                    ip=ip, bk_cloud_id=self.data["bk_cloud_id"], bk_biz_id=self.data["bk_biz_id"]
                )
                if host_obj.access_layer == AccessLayer.PROXY:
                    for proxy_obj in ProxyInstance.objects.filter(machine=host_obj).all():
                        if proxy_obj.cluster.count() > 0:
                            raise Exception("proxy {} in cluster , can't do this .".format(proxy_obj))
                elif host_obj.access_layer == AccessLayer.STORAGE:
                    for inst_obj in StorageInstance.objects.filter(machine=host_obj).all():
                        if inst_obj.cluster.count() > 0:
                            raise Exception("storage {} in cluster , can't do this .".format(inst_obj))
            except Machine.DoesNotExist:
                logger.log.info("{} host does not exists , ignore ".format(ip))
            except Exception as e:
                raise Exception("unkown exception... bugs {}:{}".format(ip, e))
