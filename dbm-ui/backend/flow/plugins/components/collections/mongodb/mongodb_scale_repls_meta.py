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
from typing import Dict, List

from django.db import transaction
from pipeline.component_framework.component import Component
from pipeline.core.flow.activity import Service

from backend.configuration.constants import DBType
from backend.db_meta import api
from backend.db_meta.enums import (
    ClusterEntryType,
    ClusterType,
    InstanceInnerRole,
    InstanceRole,
    InstanceStatus,
    MachineType,
)
from backend.db_meta.models import Cluster, ClusterEntry, Machine, StorageInstance, StorageInstanceTuple
from backend.flow.plugins.components.collections.common.base_service import BaseService
from backend.flow.utils.cc_manage import CcManage
from backend.flow.utils.mongodb.mongodb_module_operate import MongoDBCCTopoOperator

logger = logging.getLogger("flow")


class MongoScaleReplsMetaService(BaseService):
    """
    # mongodb 增加/减少分片副本数
    #### 操作包含 (元数据): 1.安装, 2.添加到集群, 3.下架, 4.CC信息维护

    # 分片集群 参数
    {
      "created_by":"xxxx",
      "immute_domain":"xxx", # 可选
      "cluster_id":1111,  # 必须的
      "bk_biz_id":0,
      "scale_out":[
                {"shard": "S1","ip": "1.a.b.c","port":20000,"spec_id":112,
                "sepc_config":{},"reuse_machine":False,"role":"m1"}
      ],
      "scale_in": [
                {"shard": "S1","ip": "1.a.b.d","port":20000}
            ]
    }

    # 副本集 参数  ---> 这里需要兼容 多实例情况
    {
      "created_by":"xxxx",
      "immute_domain":"xxx", # 可选
      "cluster_id":1111,  # 必须的
      "bk_biz_id":0,
      "scale_out":[
                {"ip": "1.a.b.c","port":20000,"spec_id":112,"sepc_config":{},
                "reuse_machine":False,"role":"m1","domain":"xx.x.a.c"}
      ],
      "scale_in": [
                {"ip": "1.a.b.d","port":20000}
            ]
    }
    """

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        try:
            mongo_cluster = Cluster.objects.get(bk_biz_id=kwargs["bk_biz_id"], id=kwargs["cluster_id"])
            if kwargs.get("scale_out", None):
                self.scale_out_repls(mongo_cluster, kwargs["scale_out"], kwargs.get("created_by", ""))
            elif kwargs.get("scale_in", None):
                self.scale_in_repls(mongo_cluster, kwargs["scale_in"], kwargs.get("created_by", ""))
            else:
                logger.error("none scale param inputed ,{}", kwargs)
        except Exception as e:
            logger.error(traceback.format_exc())
            raise e

    # 流程节点输入参数
    def inputs_format(self) -> List:
        return [
            Service.InputItem(name="kwargs", key="kwargs", type="dict", required=True),
            Service.InputItem(name="global_data", key="global_data", type="dict", required=True),
        ]

    @transaction.atomic
    def scale_in_repls(self, cluster: Cluster, scale_list: Dict, created_by: str):
        """
        减少副本数 (这里的副本 在元数据层可能是个master 节点)
        """
        for scale_item in scale_list:
            del_obj = cluster.storageinstance_set.get(machine__ip=scale_item["ip"], port=scale_item["port"])
            if del_obj.instance_role == InstanceRole.MONGO_M1.value:  # 把他变成 slave
                self.change_role_2_slave(cluster, created_by, del_obj)

            # 去掉 cluster 关联
            cluster.storageinstance_set.remove(del_obj)
            # 去掉 storageinstance_bind_entry
            del_obj.bind_entry.clear()
            # 去掉主从关系
            StorageInstanceTuple.objects.get(receiver=del_obj).delete()
            # 删掉实例信息
            del_obj.delete()
            cc_manage = CcManage(cluster.bk_biz_id, DBType.MongoDB.value)
            cc_manage.delete_service_instance(bk_instance_ids=[del_obj.bk_instance_id])
            # 可能的话删掉主机信息 # 需要检查， 是否该机器上所有实例都已经清理干净，
            if StorageInstance.objects.filter(machine__ip=del_obj.machine.ip).exists():
                logger.info("ignore recycle machine {} , another instance existed.".format(del_obj.machine))
            else:
                logger.info("storage recycle machine {}".format(del_obj.machine))
                cc_manage.recycle_host([del_obj.machine.bk_host_id])
                del_obj.machine.delete()

    @transaction.atomic
    def change_role_2_slave(self, cluster, created_by, del_obj):
        # 获取一个不是 backup 的节点
        new_master = (
            StorageInstanceTuple.objects.filter(ejector=del_obj)
            .exclude(receiver__instance_role=InstanceRole.MONGO_BACKUP.value)
            .first()
            .receiver
        )
        logger.info(
            "scale in role is {}:{}:{}, find it's none backup slave {}".format(
                cluster.immute_domain, del_obj.instance_role, del_obj, new_master
            )
        )

        # 互换角色
        del_obj.instance_role = new_master.instance_role
        del_obj.instance_inner_role = InstanceInnerRole.SLAVE.value
        del_obj.save(update_fields=["instance_role", "instance_inner_role"])

        new_master.instance_role = InstanceRole.MONGO_M1.value
        new_master.instance_inner_role = InstanceInnerRole.MASTER.value
        new_master.save(update_fields=["instance_role", "instance_inner_role"])

        # 加成mongos
        tmp_proxy_objs = list(del_obj.proxyinstance_set.all())
        new_master.proxyinstance_set.add(*tmp_proxy_objs)
        del_obj.proxyinstance_set.clear()
        logger.info("add mongos link 4 storage {}:{}".format(cluster.immute_domain, new_master))

        # storageinstance_bind_entry 表更新
        tmp_entries = del_obj.bind_entry.all()
        new_master.bind_entry.add(*tmp_entries)

        # nosqlstoragesetdtl 表更新
        logger.info("change cluster {} setdtl master from {} to {}".format(cluster.immute_domain, del_obj, new_master))
        cluster.nosqlstoragesetdtl_set.filter(instance=del_obj).update(instance=new_master)

        # storageinstancetuple 表更新
        for tuple in StorageInstanceTuple.objects.filter(ejector=del_obj):
            receiver_obj = tuple.receiver
            if tuple.receiver.id == new_master.id:
                receiver_obj = del_obj
            ntuple = StorageInstanceTuple.objects.create(ejector=new_master, receiver=receiver_obj, creator=created_by)
            logger.info(
                "reset cluster {} tuple link from {}->{} to {}->{}".format(
                    cluster.immute_domain, tuple.ejector.id, tuple.receiver.id, ntuple.ejector.id, ntuple.receiver.id
                )
            )
            tuple.delete()

    @transaction.atomic
    def scale_out_repls(self, cluster: Cluster, scale_list: Dict, created_by: str):
        """
        增加副本数
        """
        for scale_item in scale_list:
            m1_obj, role = self.get_cluster_master_and_role(cluster, scale_item)

            # 创建实例
            machine_exist = Machine.objects.filter(
                bk_biz_id=cluster.bk_biz_id, ip=scale_item["ip"], bk_cloud_id=cluster.bk_cloud_id
            ).exists()
            if scale_item.get("reuse_machine", False) and not machine_exist:
                api.machine.create(
                    machines=[
                        {
                            "bk_biz_id": cluster.bk_biz_id,
                            "ip": scale_item["ip"],
                            "machine_type": MachineType.MONGODB.value,
                            "spec_id": scale_item["spec_id"],
                            "spec_config": scale_item.get("spec_config", {}),
                        }
                    ],
                    bk_cloud_id=cluster.bk_cloud_id,
                    creator=created_by,
                )
            else:
                raise Exception(
                    "machine will not create reuseFlag:{} and machineExist:{} bizID:{};IP:{};CloudID:{}".format(
                        scale_item.get("reuse_machine", False),
                        machine_exist,
                        cluster.bk_biz_id,
                        scale_item["ip"],
                        cluster.bk_cloud_id,
                    )
                )
            mongo_obj = api.storage_instance.create(
                instances=[{"ip": scale_item["ip"], "port": scale_item["port"], "instance_role": role}],
                status=InstanceStatus.RUNNING.value,
                creator=created_by,
            )[0]

            # add 2 slave
            mongo_obj.instance_role = role
            mongo_obj.instance_inner_role = InstanceInnerRole.SLAVE.value
            mongo_obj.cluster_type = m1_obj.cluster_type
            mongo_obj.save(update_fields=["cluster_type", "instance_role", "instance_inner_role"])
            # machine 实例信息更新
            new_machine = mongo_obj.machine
            new_machine.cluster_type = m1_obj.cluster_type
            new_machine.save(update_fields=["cluster_type"])
            logger.info("update {} role , cluster_type {}".format(mongo_obj, m1_obj.cluster_type))

            # add tuple
            StorageInstanceTuple.objects.create(ejector=m1_obj, receiver=mongo_obj, creator=created_by)

            # add 2 cluster ,
            cluster.storageinstance_set.add(mongo_obj)

            # storageinstance_bind_entry 增加记录
            tmp_entries = m1_obj.bind_entry.all()
            mongo_obj.bind_entry.add(*tmp_entries)

            is_increment = False
            if m1_obj.cluster_type == ClusterType.MongoReplicaSet.value:
                is_increment = True
                # 给复制集增加域名
                cluster_entry = ClusterEntry.objects.create(
                    cluster=cluster,
                    cluster_entry_type=ClusterEntryType.DNS,
                    entry=scale_item["domain"],
                    creator=created_by,
                )
                cluster_entry.storageinstance_set.add(
                    StorageInstance.objects.get(machine__ip=scale_item["ip"], port=scale_item["port"])
                )
                cluster_entry.save()
            # 转移模块
            MongoDBCCTopoOperator(cluster).transfer_instances_to_cluster_module(
                instances=[mongo_obj], is_increment=is_increment
            )
            logger.info(
                "add instance {}:{} 2 cluster {}:{} done".format(
                    mongo_obj, role, cluster.immute_domain, scale_item["shard"]
                )
            )

    # 获取到集群的master 节点， repSet 和 shardCluster 获取方式不一样
    def get_cluster_master_and_role(self, cluster: Cluster, scale_item: Dict):
        m1_obj, ava_role = "", scale_item.get("role")
        if cluster.cluster_type == ClusterType.MongoShardedCluster.value:
            m1_obj = cluster.storageinstance_set.get(
                id=cluster.nosqlstoragesetdtl_set.get(seg_range=scale_item["shard"]).instance_id
            )
        else:
            m1_obj = cluster.storageinstance_set.get(instance_role=InstanceRole.MONGO_M1.value)

        if ava_role is None:
            instance_roles = [
                ins.receiver.instance_role for ins in StorageInstanceTuple.objects.filter(ejector=m1_obj)
            ]
            ava_roles = list(set(self.get_mongo_slave_roles()) - set(instance_roles))
            if len(ava_roles) > 0:
                ava_role = ava_roles[0]  # 可以排个序, 再取一个
            else:
                raise Exception(
                    "unsupport more than 10 nodes per shard ------.{}=> {}".format(
                        cluster.immute_domain, instance_roles
                    )
                )
        logger.info(
            "get mongo m1 {} 4 cluster {}, with avaiable role : {}".format(m1_obj, cluster.immute_domain, ava_role)
        )
        return m1_obj, ava_role

    # 新增副本时，可选的角色
    def get_mongo_slave_roles(self):
        return [
            InstanceRole.MONGO_M2.value,
            InstanceRole.MONGO_M3.value,
            InstanceRole.MONGO_M4.value,
            InstanceRole.MONGO_M5.value,
            InstanceRole.MONGO_M6.value,
            InstanceRole.MONGO_M7.value,
            InstanceRole.MONGO_M8.value,
            InstanceRole.MONGO_M9.value,
            InstanceRole.MONGO_M10.value,
        ]


class MongoScaleReplsMetaComponent(Component):
    """
    增加/减少 副本数,适用于MongoShardCluster、MongoRepSet架构 [mongodb]
    """

    name = __name__
    code = "mongo_scale_repls_meta"
    bound_service = MongoScaleReplsMetaService
