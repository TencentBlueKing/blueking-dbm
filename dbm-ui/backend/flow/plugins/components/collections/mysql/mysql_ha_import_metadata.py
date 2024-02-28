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
from typing import Dict, List, Optional, Union

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
)
from backend.flow.plugins.components.collections.common.base_service import BaseService

logger = logging.getLogger("celery")


def _get_machine_addition_info(ip: str, cluster_json: Dict) -> Dict:
    for ele in cluster_json["machines"]:
        if ele["IP"] == ip:
            return ele


def _setup_standby_slave(cluster_json: Dict):
    ins = StorageInstance.objects.get(
        machine__ip=cluster_json["stand_by_slave"]["ip"], port=cluster_json["stand_by_slave"]["port"]
    )
    ins.is_stand_by = True
    ins.save(update_fields=["is_stand_by"])


def _create_entries(cluster_json: Dict, cluster_obj: Cluster):
    for entry_json in cluster_json["entries"]:
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
        for ij in entry_json["instance"]:
            qs = ProxyInstance.objects.filter(machine__ip=ij["ip"], port=ij["port"])
            if qs.exists():
                entry_obj.proxyinstance_set.add(*list(qs))
            else:
                entry_obj.storageinstance_set.add(
                    *list(StorageInstance.objects.filter(machine__ip=ij["ip"], port=ij["port"]))
                )
        logging.info("create entry_json:{} success".format(entry_json))


class MySQLHAImportMetadataService(BaseService):
    def __init__(self, name=None):
        super().__init__(name=name)
        self.bk_biz_id = 0
        self.db_module_id = 0
        self.proxy_spec: Spec = Spec()
        self.storage_spec: Spec = Spec()

    @transaction.atomic
    def _execute(self, data, parent_data):
        kwargs = data.get_one_of_inputs("kwargs")
        trans_data = data.get_one_of_inputs("trans_data")
        global_data = data.get_one_of_inputs("global_data")

        self.log_info(_("[{}] get trans_data: {}".format(kwargs["node_name"], trans_data)))

        self.bk_biz_id = global_data["bk_biz_id"]
        self.db_module_id = global_data["db_module_id"]
        proxy_spec_id = global_data["proxy_spec_id"]
        storage_spec_id = global_data["storage_spec_id"]

        self.proxy_spec = Spec.objects.get(pk=proxy_spec_id)
        self.storage_spec = Spec.objects.get(pk=storage_spec_id)

        json_content = global_data["json_content"]

        cluster_ids = []
        for cluster_json in json_content:
            cluster_obj = self._create_cluster(
                cluster_id=cluster_json["cluster_id"],
                name=cluster_json["name"],
                immute_domain=cluster_json["immute_domain"].rstrip("."),
                version=cluster_json["version"],  # ["master"]["Version"],
                disaster=cluster_json["disaster_level"],
                creator=global_data["created_by"],
            )

            master_obj = self._create_master_instance(cluster_json=cluster_json)
            slave_objs = self._create_slave_instances(cluster_json=cluster_json)
            proxy_objs = self._create_proxy_instance(cluster_json=cluster_json)

            cluster_obj.storageinstance_set.add(master_obj)
            cluster_obj.storageinstance_set.add(*slave_objs)
            cluster_obj.proxyinstance_set.add(*proxy_objs)
            master_obj.proxyinstance_set.add(*proxy_objs)

            cluster_obj.region = master_obj.machine.bk_city.logical_city.name
            cluster_obj.save(update_fields=["region"])

            _setup_standby_slave(cluster_json=cluster_json)

            StorageInstanceTuple.objects.bulk_create(
                [StorageInstanceTuple(ejector=master_obj, receiver=ele) for ele in slave_objs]
            )

            _create_entries(cluster_json=cluster_json, cluster_obj=cluster_obj)

            cluster_ids.append(cluster_obj.id)

        self.log_info(_("[{}] cluster ids = {}".format(kwargs["node_name"], cluster_ids)))

        trans_data.cluster_ids = cluster_ids
        data.outputs["trans_data"] = trans_data
        self.log_info(_("[{}] 元数据写入完成".format(kwargs["node_name"])))
        return True

    def _create_machine(
        self, ip: str, addition_info: Dict, access_layer: AccessLayer, machine_type: MachineType
    ) -> Machine:
        cc_info = json.loads(addition_info["CCInfo"])
        bk_city_id = addition_info["CityID"]

        if access_layer == AccessLayer.PROXY:
            spec_obj = self.proxy_spec
        else:
            spec_obj = self.storage_spec

        machine, _ = Machine.objects.get_or_create(
            ip=ip,
            bk_biz_id=self.bk_biz_id,
            db_module_id=self.db_module_id,
            access_layer=access_layer.value,
            machine_type=machine_type.value,
            cluster_type=ClusterType.TenDBHA.value,
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

    def __create_instance(
        self,
        ip: str,
        port: int,
        addition_info: Dict,
        machine_type: MachineType,
        inner_role: Optional[InstanceInnerRole] = None,
        version: Optional[str] = None,
    ) -> Union[ProxyInstance, StorageInstance]:
        if machine_type == MachineType.PROXY:
            access_layer = AccessLayer.PROXY
        else:
            access_layer = AccessLayer.STORAGE

        machine = self._create_machine(
            ip=ip, addition_info=addition_info, access_layer=access_layer, machine_type=machine_type
        )

        if machine_type == MachineType.PROXY:
            return self.__create_proxy_instance(machine=machine, port=port)
        else:
            return self.__create_storage_instance(machine=machine, port=port, inner_role=inner_role, version=version)

    def __create_proxy_instance(self, machine: Machine, port: int) -> ProxyInstance:
        return ProxyInstance.objects.create(
            version="",
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

    def __create_storage_instance(
        self, machine: Machine, port: int, inner_role: InstanceInnerRole, version: str
    ) -> StorageInstance:
        if inner_role == InstanceInnerRole.MASTER:
            role = InstanceRole.BACKEND_MASTER
        else:
            role = InstanceRole.BACKEND_SLAVE

        return StorageInstance.objects.create(
            version=version,
            port=port,
            machine=machine,
            db_module_id=self.db_module_id,
            bk_biz_id=self.bk_biz_id,
            access_layer=machine.access_layer,
            machine_type=machine.machine_type,
            instance_role=role,
            instance_inner_role=inner_role,
            cluster_type=machine.cluster_type,
            status=InstanceStatus.RUNNING.value,
            phase=InstancePhase.TRANS_STAGE.value,
        )

    def _create_cluster(
        self, cluster_id: int, name: str, immute_domain: str, version: str, disaster: str, creator: str
    ) -> Cluster:
        return Cluster.objects.create(
            id=cluster_id,
            name=name,
            bk_biz_id=self.bk_biz_id,
            cluster_type=ClusterType.TenDBHA.value,
            db_module_id=self.db_module_id,
            immute_domain=immute_domain,
            major_version="MySQL-" + ".".join(version.split(".")[:2]),
            phase=ClusterPhase.TRANS_STAGE.value,
            status=ClusterStatus.NORMAL.value,
            bk_cloud_id=0,
            disaster_tolerance_level=disaster,
            creator=creator,
        )

    def _create_master_instance(self, cluster_json: Dict) -> StorageInstance:
        ip = cluster_json["master"]["ip"]
        port = cluster_json["master"]["port"]
        version = cluster_json["master"]["Version"]

        addition_info = _get_machine_addition_info(ip=ip, cluster_json=cluster_json)
        return self.__create_instance(
            ip=ip,
            port=port,
            addition_info=addition_info,
            machine_type=MachineType.BACKEND,
            inner_role=InstanceInnerRole.MASTER,
            version=version,
        )

    def _create_slave_instances(self, cluster_json: Dict) -> List[StorageInstance]:
        slaves = []
        for ij in cluster_json["slaves"]:
            ip = ij["ip"]
            port = ij["port"]
            version = ij["Version"]
            addition_info = _get_machine_addition_info(ip=ip, cluster_json=cluster_json)
            slaves.append(
                self.__create_instance(
                    ip=ip,
                    port=port,
                    addition_info=addition_info,
                    machine_type=MachineType.BACKEND,
                    inner_role=InstanceInnerRole.SLAVE,
                    version=version,
                )
            )

        return slaves

    def _create_proxy_instance(self, cluster_json: Dict) -> List[ProxyInstance]:
        proxies = []
        for ij in cluster_json["proxies"]:
            ip = ij["ip"]
            port = ij["port"]
            addition_info = _get_machine_addition_info(ip=ip, cluster_json=cluster_json)
            proxies.append(
                self.__create_instance(ip=ip, port=port, addition_info=addition_info, machine_type=MachineType.PROXY)
            )

        return proxies


class MySQLHAImportMetadataComponent(Component):
    name = __name__
    code = "mysql_ha_import_metadata"
    bound_service = MySQLHAImportMetadataService
