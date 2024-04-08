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
import logging
import logging.config
import traceback
from typing import List

from django.db import transaction
from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import Service

from backend.db_meta import api
from backend.db_meta.enums import ClusterType, InstanceRole, InstanceStatus, MachineType
from backend.db_meta.models import Cluster, Machine, StorageInstance, StorageInstanceTuple
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.mongodb.mongodb_module_operate import MongoDBCCTopoOperator

logger = logging.getLogger("flow")


class MongoDBCapcityMetaService(BaseService):
    """
    集群容量变更:
      # 该元数据操作包含 : 1.安装, 2.添加到集群, 3.下架, 4.CC信息维护
    {
      "created_by":"xxxx",
      "immute_domain":"xxx", # 可选
      "cluster_id":1111,  # 必须的
      "bk_biz_id":0,
      "mongodb": [
                {
                    "ip": "1.a.b.c","port":20000,
                    "target": {"ip": "1.a.b.c","port":20000,"spec_id":111,"spec_config":{}},
                }
            ],
    }

    """

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")

        try:
            mongo_cluster = Cluster.objects.get(bk_biz_id=kwargs["bk_biz_id"], id=kwargs["cluster_id"])

            # 仅支持 MongoDB 实例级的容量变更
            if kwargs.get("mongodb"):
                logger.info(
                    "mongo cluster capcity specs changes {} mongodb : {} ".format(
                        mongo_cluster.immute_domain, kwargs.get("mongodb")
                    )
                )
                self.mongdb_instance_spec_modify(
                    mongo_cluster,
                    kwargs.get("mongodb"),
                    MachineType.MONGODB.value,
                    kwargs.get("created_by"),
                )
            else:
                raise Exception("unexpected inputs by cluster specs changs. {}".format(kwargs))
        except Exception as e:
            logger.error(traceback.format_exc())
            logger.error("cluster specs changs 4 meta fail, {}error:{}".format(kwargs, str(e)))
            return False
        logger.info("cluster specs changs 4 meta successfully {}".format(kwargs))
        return True

    # mongdb/mongo_cofig 替换
    @transaction.atomic
    def mongdb_instance_spec_modify(self, cluster: Cluster, mongodb_info, machine_type, created_by):
        machines, mongdb_insts = {}, []
        for rep_link in mongodb_info:
            old_ip, new_ip = rep_link["ip"], rep_link["target"]["ip"]
            old_port, new_port = rep_link["port"], rep_link["target"]["port"]
            logger.info(
                "cluster {} replace mongodb from {}:{} 【2】 {} begin.".format(
                    cluster.immute_domain, old_ip, old_port, rep_link["target"]
                )
            )
            # 机器
            machines[new_ip] = {
                "ip": new_ip,
                "bk_biz_id": cluster.bk_biz_id,
                "bk_cloud_id": cluster.bk_cloud_id,
                "machine_type": machine_type,
                "spec_id": rep_link["target"]["spec_id"],
                "spec_config": rep_link["target"]["spec_config"],
            }
            # 实例
            old_obj = StorageInstance.objects.get(machine__ip=old_ip, port=old_port, bk_biz_id=cluster.bk_biz_id)
            mongdb_insts.append(
                {
                    "old": {"ip": old_ip, "port": old_port, "instance_role": old_obj.instance_role},
                    "new": {
                        "ip": new_ip,
                        "port": new_port,
                        "instance_role": old_obj.instance_role,
                    },
                }
            )

        # 新增 mongos 到集群
        for machine in machines:
            if Machine.objects.filter(
                ip=machine["ip"],
                bk_biz_id=cluster.bk_biz_id,
                bk_cloud_id=cluster.bk_cloud_id,
                machine_type=MachineType.MONGODB.value,
            ).exists():
                logger.info("machine exists 4 replicate ,reuse it. {}".format(machine))
            else:
                api.machine.create(machines=[machine], bk_cloud_id=cluster.bk_cloud_id, creator=created_by)
        api.storage_instance.create(
            instances=[inst["new"] for inst in mongdb_insts], status=InstanceStatus.RUNNING.value, creator=created_by
        )
        self.mongo_package_meta(cluster, mongdb_insts, created_by)

        # # 实例下架
        api.cluster.nosqlcomm.decommission_backends(
            cluster, backends=[inst["old"] for inst in mongdb_insts], is_all=False
        )

    @transaction.atomic
    def mongo_package_meta(self, cluster, rep_insts, created_by):
        for inst_pair in rep_insts:
            old_ip, old_port = inst_pair["old"]["ip"], inst_pair["old"]["port"]
            new_ip, new_port = inst_pair["new"]["ip"], inst_pair["new"]["port"]
            old_obj = cluster.storageinstance_set.get(machine__ip=old_ip, port=old_port)
            new_obj = StorageInstance.objects.get(
                machine__ip=new_ip,
                port=new_port,
                bk_biz_id=cluster.bk_biz_id,
                machine__bk_cloud_id=cluster.bk_cloud_id,
            )

            # storageinstance  实例信息更新
            old_obj.status = InstanceStatus.UNAVAILABLE
            old_obj.save(update_fields=["status"])

            new_obj.instance_role = old_obj.instance_role
            new_obj.instance_inner_role = old_obj.instance_inner_role
            new_obj.cluster_type = old_obj.cluster_type
            new_obj.save(update_fields=["cluster_type", "instance_role", "instance_inner_role"])
            # machine 实例信息更新
            new_machine = new_obj.machine
            new_machine.cluster_type = old_obj.cluster_type
            new_machine.save(update_fields=["cluster_type"])
            logger.info("update {} role , cluster_type {}".format(new_ip, old_obj.cluster_type))

            # storageinstance_cluster 只做添加
            cluster.storageinstance_set.add(new_obj)

            # storageinstance_bind_entry 表更新
            tmp_entries = old_obj.bind_entry.all()
            new_obj.bind_entry.add(*tmp_entries)
            old_obj.bind_entry.clear()

            # 如果是 Master 节点
            if old_obj.instance_role == InstanceRole.MONGO_M1.value:
                # mongos 关系建立 [M1] / 只有mongodb 才有 ； mongo_config没有
                if (
                    old_obj.machine_type == MachineType.MONGODB.value
                    and cluster.cluster_type == ClusterType.MongoShardedCluster.value
                ):
                    tmp_proxy_objs = list(old_obj.proxyinstance_set.all())
                    new_obj.proxyinstance_set.add(*tmp_proxy_objs)
                    old_obj.proxyinstance_set.clear()
                    logger.info("add mongos link 4 storage {}:{}".format(cluster.immute_domain, new_obj))

                # nosqlstoragesetdtl 表更新
                logger.info(
                    "change cluster {} setdtl master from {} to {}".format(cluster.immute_domain, old_obj, new_obj)
                )
                cluster.nosqlstoragesetdtl_set.filter(instance=old_obj).update(instance=new_obj)

                # storageinstancetuple 表更新
                for tuple in StorageInstanceTuple.objects.filter(ejector=old_obj):
                    StorageInstanceTuple.objects.create(ejector=new_obj, receiver=tuple.receiver, creator=created_by)
                    tuple.delete()
            # slave 节点
            else:
                # tuple 表更新
                old_tuple = StorageInstanceTuple.objects.get(receiver=old_obj)
                StorageInstanceTuple.objects.create(ejector=old_tuple.ejector, receiver=new_obj, creator=created_by)
                old_tuple.delete()
            # 转移模块
            ins_is_increment = False
            if cluster.cluster_type == ClusterType.MongoReplicaSet.value:
                ins_is_increment = True
            MongoDBCCTopoOperator(cluster).transfer_instances_to_cluster_module(
                instances=[new_obj], is_increment=ins_is_increment
            )

    # 流程节点输入参数
    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]


class MongoDBCapcityMetaComponent(Component):
    """
    Mongo 容量变更
    ShardCluster , ReplicateRet
    """

    name = __name__
    code = "mongodb_capcity_meta"
    bound_service = MongoDBCapcityMetaService
