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
import re
from collections import defaultdict
from typing import Dict, List

from backend.components import DRSApi
from backend.components.exception import DRSException
from backend.db_meta.enums import MachineType
from backend.db_meta.models import ProxyInstance, StorageInstance
from backend.flow.engine.bamboo.scene.mysql.clone_grants.exceptions import InvalidMySQLVersionException
from backend.flow.engine.validate.base_validate import validator_log_format
from backend.flow.engine.validate.mysql_base_validate import MysqlBaseValidator


class CloneMySQLGrantsFlowValidator(MysqlBaseValidator):
    spider_version_pattern = r".*tspider-(?P<subv>[\d]+\.[\d]+\.[\d]+).*"
    mysql_version_pattern = r"^(?P<subv>[\d]+\.[\d]+\.[\d]+).*"

    def __call__(self, *args, **kwargs):
        error_msgs = []

        # 实例不能同时出现在源和目的
        error_msgs.extend(self.__run_duplicate_instance_check(infos=self.data["infos"]))

        # 云区域内的存储实例必须存在
        for index, info in enumerate(self.data["infos"]):
            error_msgs.extend(self.__run_check_for_info(index=index, info=info))

        if error_msgs:
            return error_msgs

        self.data["validated"] = True
        return None

    def __run_duplicate_instance_check(self, infos: List) -> List[str]:
        error_msg = []
        source_collection = defaultdict(set)
        dest_collection = defaultdict(set)
        for info in infos:
            bk_cloud_id = info["bk_cloud_id"]
            source_collection[bk_cloud_id].add(info["source_address"])
            dest_collection[bk_cloud_id].update(info["dest_addresses"])

        for index, info in enumerate(infos):
            row_key = info.get("row_key", "")
            bk_cloud_id = info["bk_cloud_id"]
            source_address = info["source_address"]
            dest_addresses = info["dest_addresses"]

            log_format_tag = self.create_log_tag(field="source_address", index=index, row_key=row_key)
            err = self.__check_one_duplicate_instance(
                bk_cloud_id=bk_cloud_id, address=source_address, inst_collection=dest_collection, **log_format_tag
            )
            if err:
                error_msg.append(err)

            log_format_tag = self.create_log_tag(field="dest_addresses", index=index, row_key=row_key)
            for da in dest_addresses:
                err = self.__check_one_duplicate_instance(
                    bk_cloud_id=bk_cloud_id, address=da, inst_collection=source_collection, **log_format_tag
                )
                if err:
                    error_msg.append(err)

        return error_msg

    @classmethod
    @validator_log_format
    def __check_one_duplicate_instance(cls, bk_cloud_id: int, address: str, inst_collection: Dict) -> str:
        if address in inst_collection[bk_cloud_id]:
            return f"{address} can't be source and dest at sametime"

        return ""

    def __run_check_for_info(self, index: int, info: Dict) -> List[str]:
        """
        1. 实例存在性检查
        2. 版本检查
        """
        error_msg = []

        row_key = info.get("row_key", "")

        bk_cloud_id = info["bk_cloud_id"]
        machine_type = info["machine_type"]
        source_address = info["source_address"]
        dest_addresses = info["dest_addresses"]

        available_source = ""
        available_dests = []

        log_format_tag = self.create_log_tag(field="source_address", index=index, row_key=row_key)
        err = self.__check_instance_exists(
            bk_cloud_id=bk_cloud_id, machine_type=machine_type, instance_address=source_address, **log_format_tag
        )
        if err:
            error_msg.append(err)
        else:
            available_source = source_address

        log_format_tag = self.create_log_tag(field="dest_addresses", index=index, row_key=row_key)
        for instance_address in dest_addresses:
            err = self.__check_instance_exists(
                bk_cloud_id=bk_cloud_id, machine_type=machine_type, instance_address=instance_address, **log_format_tag
            )
            if err:
                error_msg.append(err)
            else:
                available_dests.append(instance_address)

        if machine_type != MachineType.PROXY and available_source and available_dests:
            log_format_tag = self.create_log_tag(field="source_address", index=index, row_key=row_key)
            err = self.__run_version_check(
                machine_type=machine_type,
                source_address=available_source,
                dest_addresses=available_dests,
                **log_format_tag,
            )
            if err:
                error_msg.append(err)

        return error_msg

    @classmethod
    @validator_log_format
    def __check_instance_exists(cls, bk_cloud_id: int, machine_type: MachineType, instance_address: str) -> str:
        if machine_type not in [
            MachineType.SINGLE,
            MachineType.BACKEND,
            MachineType.REMOTE,
            MachineType.SPIDER,
            MachineType.PROXY,
        ]:
            return f"not supported machine type {machine_type}"

        ip, port = instance_address.split(":")

        if machine_type in [MachineType.SINGLE, MachineType.BACKEND, MachineType.REMOTE]:
            try:
                StorageInstance.objects.get(machine__bk_cloud_id=bk_cloud_id, machine__ip=ip, port=int(port))
                return ""
            except StorageInstance.DoesNotExist:
                return f"{machine_type} {instance_address} not found in cloud {bk_cloud_id}"
        else:
            try:
                ProxyInstance.objects.get(machine__bk_cloud_id=bk_cloud_id, machine__ip=ip, port=int(port))
                return ""
            except ProxyInstance.DoesNotExist:
                return f"{machine_type} {instance_address} not found in cloud {bk_cloud_id}"

    # @classmethod
    @validator_log_format
    def __run_version_check(self, machine_type: MachineType, source_address: str, dest_addresses: List[str]) -> str:
        """
        MySQL 版本检查
        权限克隆不能高版本向低版本克隆
        """
        # error_msg = []

        rvs = self.__get_raw_version(addresses=dest_addresses + [source_address])

        bad_dest = []

        rsv = rvs[source_address]
        for da in dest_addresses:
            if self.__parse_version(machine_type=machine_type, v=rsv, major_only=True) > self.__parse_version(
                machine_type=machine_type, v=rvs[da], major_only=True
            ):
                bad_dest.append(da)

        if bad_dest:
            return "source version greater than dest {}".format(", ".join(bad_dest))

        return ""

    @classmethod
    def __get_raw_version(cls, addresses: List[str]) -> Dict[str, str]:
        drs_res = DRSApi.rpc({"addresses": addresses, "cmds": ["select @@version as version"]})
        if not drs_res:
            raise

        res = {}
        for sr in drs_res:
            if sr["error_msg"]:
                DRSException(sr["error_msg"])

            cmd_results = sr["cmd_results"]
            if cmd_results[0]["error_msg"]:
                DRSException(cmd_results[0]["error_msg"])

            table_data = cmd_results[0]["table_data"]

            res[sr["address"]] = table_data[0]["version"]

        return res

    @classmethod
    def __parse_version(cls, machine_type: MachineType, v: str, major_only: bool) -> int:
        if machine_type == MachineType.SPIDER.value:
            m = re.search(pattern=cls.spider_version_pattern, string=v)
        else:
            m = re.search(pattern=cls.mysql_version_pattern, string=v)

        if not m:
            InvalidMySQLVersionException(version=v)

        vx, vy, vz = m.group("subv").split(".")

        if major_only:
            return int(vx) * 1000 * 1000 + int(vy) * 1000
        else:
            return int(vx) * 1000 * 1000 + int(vy) * 1000 + int(vz)
