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

from backend.components import DRSApi
from backend.db_meta.enums import InstanceInnerRole
from backend.db_meta.models import Cluster, StorageInstance

logger = logging.getLogger("root")

query_cmds = """show global variables where Variable_name in ('binlog_format','binlog_row_image','character_set_server',
'collation_server','interactive_timeout','log_bin_compress','long_query_time',
'lower_case_table_names','max_allowed_packet','max_binlog_size','max_connections',
'net_buffer_length','relay_log_uncompress','replica_parallel_type','replica_parallel_workers',
'slave_exec_mode','slave_parallel_type','slave_parallel_workers','sql_mode','table_definition_cache',
'table_open_cache','wait_timeout','time_zone','group_concat_max_len')"""


def get_cluster_config(cluster: Cluster) -> dict:
    master_config = {}
    master_model = cluster.storageinstance_set.filter(instance_inner_role=InstanceInnerRole.MASTER.value).first()
    if master_model is None:
        return {}
    res = DRSApi.rpc(
        {
            "addresses": [master_model.ip_port],
            "cmds": [query_cmds],
            "force": False,
            "bk_cloud_id": cluster.bk_cloud_id,
        }
    )
    if res[0]["error_msg"]:
        logging.error("{} get backup info error {}".format(master_model.ip_port, res[0]["error_msg"]))
    if isinstance(res[0]["cmd_results"][0]["table_data"], list) and len(res[0]["cmd_results"][0]["table_data"]) > 0:
        configs = res[0]["cmd_results"][0]["table_data"]
        for config in configs:
            master_config[config["Variable_name"]] = config["Value"]
        if "time_zone" in master_config.keys():
            master_config["default_time_zone"] = master_config["time_zone"]
            master_config.pop("time_zone")
    logger.debug(master_config)
    return master_config


def get_instance_config(bk_cloud_id: int, ip: str, ports: list = None) -> dict:
    all_storage_config = {}
    if ports is None:
        storages = StorageInstance.objects.filter(bk_cloud_id=bk_cloud_id, machine__ip=ip).all()
    else:
        storages = StorageInstance.objects.filter(
            machine__bk_cloud_id=bk_cloud_id, machine__ip=ip, port__in=ports
        ).all()

    for storage in storages:
        res = DRSApi.rpc(
            {
                "addresses": [storage.ip_port],
                "cmds": [query_cmds],
                "force": False,
                "bk_cloud_id": bk_cloud_id,
            }
        )
        storage_config = {}
        if res[0]["error_msg"]:
            logging.error("{} get backup info error {}".format(storage.ip_port, res[0]["error_msg"]))
        if (
            isinstance(res[0]["cmd_results"][0]["table_data"], list)
            and len(res[0]["cmd_results"][0]["table_data"]) > 0
        ):
            configs = res[0]["cmd_results"][0]["table_data"]
            for config in configs:
                storage_config[config["Variable_name"]] = config["Value"]
            if "time_zone" in storage_config.keys():
                storage_config["default_time_zone"] = storage_config["time_zone"]
                storage_config.pop("time_zone")
        all_storage_config[str(storage.port)] = storage_config
    logger.debug("get instance config", all_storage_config)
    return all_storage_config
