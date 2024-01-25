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
import logging
from typing import Dict, List, Tuple

from django.db import transaction
from django.utils.translation import ugettext as _
from pipeline.component_framework.component import Component

from backend.db_meta.enums import (
    AccessLayer,
    ClusterEntryRole,
    ClusterEntryType,
    ClusterPhase,
    ClusterStatus,
    ClusterType,
    InstanceInnerRole,
    InstancePhase,
    InstanceRole,
    InstanceStatus,
    MachineType,
    TenDBClusterSpiderRole,
)
from backend.db_meta.models import (
    BKCity,
    Cluster,
    ClusterEntry,
    Machine,
    ProxyInstance,
    Spec,
    StorageInstance,
    StorageInstanceTuple,
    TenDBClusterSpiderExt,
    TenDBClusterStorageSet,
)
from backend.flow.plugins.components.collections.common.base_service import BaseService

logger = logging.getLogger("celery")


def _get_machine_addition_info(ip: str, cluster_json: Dict) -> Dict:
    for ele in cluster_json["machines"]:
        if ele["IP"] == ip:
            return ele


def _create_entries(cluster_json: Dict, cluster_obj: Cluster):
    for entry_json in cluster_json["entries"].values():
        logging.info("entry_json: {}".format(entry_json))

        if entry_json["entry_role"] == ClusterEntryRole.MASTER_ENTRY.value:
            entry_role = ClusterEntryRole.MASTER_ENTRY.value
        else:
            entry_role = ClusterEntryRole.SLAVE_ENTRY.value

        entry_obj = ClusterEntry.objects.create(
            cluster=cluster_obj,
            cluster_entry_type=ClusterEntryType.DNS.value,
            entry=entry_json["domain"].rstrip("."),
            role=entry_role,
        )
        for ij in entry_json["instances"]:
            qs = ProxyInstance.objects.filter(machine__ip=ij["ip"], port=ij["port"])
            entry_obj.proxyinstance_set.add(*list(qs))

        logging.info("create entry_json:{} success".format(entry_json))


class TenDBClusterImportMetadataService(BaseService):
    def __init__(self):
        super().__init__()
        self.bk_biz_id = 0
        self.db_module_id = 0
        self.spider_spec: Spec = Spec()
        self.remote_spec: Spec = Spec()

    @transaction.atomic
    def _execute(self, data, parent_data):
        kwargs = data.get_one_of_inputs("kwargs")
        trans_data = data.get_one_of_inputs("trans_data")
        global_data = data.get_one_of_inputs("global_data")

        self.log_info(_("[{}] get trans_data: {}".format(kwargs["node_name"], trans_data)))

        self.bk_biz_id = global_data["bk_biz_id"]
        self.db_module_id = global_data["db_module_id"]
        spider_spec_id = global_data["spider_spec_id"]
        remote_spec_id = global_data["remote_spec_id"]

        self.spider_spec = Spec.objects.get(pk=spider_spec_id)
        self.remote_spec = Spec.objects.get(pk=remote_spec_id)

        json_content = global_data["json_content"]
        cluster_ids = []
        for cluster_json in json_content.values():
            cluster_obj = self._create_cluster(
                name=cluster_json["name"],
                immute_domain=cluster_json["immute_domain"].rstrip("."),
                version=cluster_json["version"],
                disaster=cluster_json["disaster_level"],
                creator=global_data["created_by"],
            )
            master_objs, slave_objs = self._create_remote_sets(cluster_obj=cluster_obj, cluster_json=cluster_json)
            spider_master_objs = self._create_spider_masters(cluster_json=cluster_json)
            spider_slave_objs = self._create_spider_slaves(cluster_json=cluster_json)
            spider_master_mnt_objs = self._create_spider_master_mnts(cluster_json=cluster_json)
            spider_slave_mnt_objs = self._create_spider_slave_mnts(cluster_json=cluster_json)

            for master_obj in master_objs:
                master_obj.proxyinstance_set.add(*spider_master_objs)
                master_obj.proxyinstance_set.add(*spider_master_mnt_objs)

            for slave_obj in slave_objs:
                slave_obj.proxyinstance_set.add(*spider_slave_objs)
                slave_obj.proxyinstance_set.add(*spider_slave_mnt_objs)

            cluster_obj.storageinstance_set.add(*master_objs)
            cluster_obj.storageinstance_set.add(*slave_objs)
            cluster_obj.proxyinstance_set.add(*spider_master_objs)
            cluster_obj.proxyinstance_set.add(*spider_slave_objs)
            cluster_obj.proxyinstance_set.add(*spider_master_mnt_objs)
            cluster_obj.proxyinstance_set.add(*spider_slave_mnt_objs)

            cluster_obj.region = master_objs[0].machine.bk_city.logical_city.name
            cluster_obj.save(update_fields=["region"])

            _create_entries(cluster_json=cluster_json, cluster_obj=cluster_obj)
            cluster_ids.append(cluster_obj.id)

        self.log_info(_("[{}] cluster ids = {}".format(kwargs["node_name"], cluster_ids)))

        trans_data.cluster_ids = cluster_ids
        data.outputs["trans_data"] = trans_data
        self.log_info(_("[{}] 元数据写入完成".format(kwargs["node_name"])))
        return True

    def _create_cluster(self, name: str, immute_domain: str, version: str, disaster: str, creator: str) -> Cluster:
        return Cluster.objects.create(
            name=name,
            bk_biz_id=self.bk_biz_id,
            cluster_type=ClusterType.TenDBCluster.value,
            db_module_id=self.db_module_id,
            immute_domain=immute_domain,
            major_version="MySQL-" + ".".join(version.split(".")[:2]),
            phase=ClusterPhase.TRANS_STAGE.value,
            status=ClusterStatus.NORMAL.value,
            bk_cloud_id=0,
            disaster_tolerance_level=disaster,
            creator=creator,
        )

    def _create_spider_masters(self, cluster_json: Dict) -> List[ProxyInstance]:
        res = []
        for ele in cluster_json["master_spiders"]:
            ins = self._create_spider_instance(
                ip=ele["ip"], port=ele["port"], version=ele["version"], cluster_json=cluster_json
            )
            TenDBClusterSpiderExt.objects.create(instance=ins, spider_role=TenDBClusterSpiderRole.SPIDER_MASTER.value)
            res.append(ins)
        return res

    def _create_spider_slaves(self, cluster_json: Dict) -> List[ProxyInstance]:
        res = []
        for ele in cluster_json["slave_spiders"]:
            ins = self._create_spider_instance(
                ip=ele["ip"], port=ele["port"], version=ele["version"], cluster_json=cluster_json
            )
            TenDBClusterSpiderExt.objects.create(instance=ins, spider_role=TenDBClusterSpiderRole.SPIDER_SLAVE.value)
            res.append(ins)
        return res

    def _create_spider_master_mnts(self, cluster_json: Dict) -> List[ProxyInstance]:
        res = []
        for ele in cluster_json["master_tmp_spiders"]:
            ins = self._create_spider_instance(
                ip=ele["ip"], port=ele["port"], version=ele["version"], cluster_json=cluster_json
            )
            TenDBClusterSpiderExt.objects.create(instance=ins, spider_role=TenDBClusterSpiderRole.SPIDER_MNT.value)
            res.append(ins)
        return res

    def _create_spider_slave_mnts(self, cluster_json: Dict) -> List[ProxyInstance]:
        res = []
        for ele in cluster_json["slave_tmp_spiders"]:
            ins = self._create_spider_instance(
                ip=ele["ip"], port=ele["port"], version=ele["version"], cluster_json=cluster_json
            )
            TenDBClusterSpiderExt.objects.create(
                instance=ins, spider_role=TenDBClusterSpiderRole.SPIDER_SLAVE_MNT.value
            )
            res.append(ins)
        return res

    def _create_spider_instance(self, ip: str, port: int, version: str, cluster_json: Dict) -> ProxyInstance:
        addition_info = _get_machine_addition_info(ip=ip, cluster_json=cluster_json)
        machine = self._create_machine(
            ip=ip, addition_info=addition_info, access_layer=AccessLayer.PROXY, machine_type=MachineType.SPIDER
        )

        return ProxyInstance.objects.create(
            version=version,
            port=port,
            admin_port=port + 1000,
            machine=machine,
            db_module_id=self.db_module_id,
            bk_biz_id=self.bk_biz_id,
            access_layer=machine.access_layer,
            machine_type=machine.machine_type,
            cluster_type=machine.cluster_type,
            status=InstanceStatus.RUNNING.value,
            phase=InstancePhase.TRANS_STAGE.value,
        )

    def _create_remote_sets(
        self, cluster_obj: Cluster, cluster_json: Dict
    ) -> Tuple[List[StorageInstance], List[StorageInstance]]:
        master_objects = []
        slave_objects = []

        for remote_set in cluster_json["sets"]:
            master = remote_set["master"]
            slave = remote_set["slave"]
            master_obj = self._create_remote_instance(
                ip=master["ip"],
                port=master["port"],
                version=master["version"],
                instance_role=InstanceRole.REMOTE_MASTER.value,
                instance_inner_role=InstanceInnerRole.MASTER.value,
                cluster_json=cluster_json,
            )
            slave_obj = self._create_remote_instance(
                ip=slave["ip"],
                port=slave["port"],
                version=slave["version"],
                instance_role=InstanceRole.REMOTE_SLAVE.value,
                instance_inner_role=InstanceInnerRole.SLAVE.value,
                cluster_json=cluster_json,
            )
            slave_obj.is_stand_by = True
            slave_obj.save(update_fields=["is_stand_by"])

            storage_tuple_obj = StorageInstanceTuple.objects.create(ejector=master_obj, receiver=slave_obj)
            TenDBClusterStorageSet.objects.create(
                cluster=cluster_obj, storage_instance_tuple=storage_tuple_obj, shard_id=remote_set["shard_id"]
            )

            master_objects.append(master_obj)
            slave_objects.append(slave_obj)

        return master_objects, slave_objects

    def _create_remote_instance(
        self,
        ip: str,
        port: int,
        version: str,
        instance_role: InstanceRole,
        instance_inner_role: InstanceInnerRole,
        cluster_json: Dict,
    ) -> StorageInstance:
        addition_info = _get_machine_addition_info(ip=ip, cluster_json=cluster_json)
        machine = self._create_machine(
            ip=ip, addition_info=addition_info, access_layer=AccessLayer.STORAGE, machine_type=MachineType.REMOTE
        )

        return StorageInstance.objects.create(
            version=version,
            port=port,
            machine=machine,
            db_module_id=self.db_module_id,
            bk_biz_id=self.bk_biz_id,
            access_layer=machine.access_layer,
            machine_type=machine.machine_type,
            instance_role=instance_role,
            instance_inner_role=instance_inner_role,
            cluster_type=machine.cluster_type,
            status=InstanceStatus.RUNNING.value,
            phase=InstancePhase.TRANS_STAGE.value,
        )

    def _create_machine(
        self, ip: str, addition_info: Dict, access_layer: AccessLayer, machine_type: MachineType
    ) -> Machine:
        cc_info = json.loads(addition_info["CCInfo"])
        bk_city_id = addition_info["CityID"]

        if access_layer == AccessLayer.PROXY:
            spec_obj = self.spider_spec
        else:
            spec_obj = self.remote_spec

        machine, _ = Machine.objects.get_or_create(
            ip=ip,
            bk_biz_id=self.bk_biz_id,
            db_module_id=self.db_module_id,
            access_layer=access_layer.value,
            machine_type=machine_type.value,
            cluster_type=ClusterType.TenDBCluster.value,
            bk_city=BKCity.objects.get(pk=bk_city_id),
            bk_host_id=cc_info["bk_host_id"],
            bk_os_name=cc_info["bk_os_name"],
            bk_idc_area=cc_info["bk_idc_area"],
            bk_idc_area_id=cc_info["bk_idc_area_id"],
            bk_sub_zone=cc_info["sub_zone"],
            bk_sub_zone_id=cc_info["sub_zone_id"],
            bk_rack=cc_info["rack"],
            bk_rack_id=cc_info["rack_id"],
            bk_svr_device_cls_name=cc_info["bk_svr_device_cls_name"],
            bk_idc_name=cc_info["idc_name"],
            bk_idc_id=cc_info["idc_id"],
            bk_cloud_id=0,  # addition_info["bk_cloud_id"],
            net_device_id=cc_info["net_device_id"],
            spec_id=spec_obj.spec_id,
            spec_config=spec_obj.get_spec_info(),
        )
        return machine


class TenDBClusterImportMetadataComponent(Component):
    name = __name__
    code = "tendb-cluster-import-metadata"
    bound_service = TenDBClusterImportMetadataService
