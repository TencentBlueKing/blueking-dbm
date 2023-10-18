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

import ast
import base64
import logging.config
import re
import traceback
from typing import Dict, List, Tuple

from django.db.models import Q
from django.utils.translation import ugettext as _

from backend.components import DBConfigApi, DRSApi
from backend.components.dbconfig.constants import FormatType, LevelName
from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.enums import ClusterType, InstanceRole, InstanceStatus
from backend.db_meta.models import Cluster
from backend.db_services.redis.redis_dts.constants import DtsOperateType, DtsTaskType
from backend.db_services.redis.redis_dts.enums import DtsBillType, DtsCopyType, DtsSyncStatus
from backend.db_services.redis.redis_dts.models import TbTendisDTSJob, TbTendisDtsTask
from backend.db_services.redis.rollback.models import TbTendisRollbackTasks
from backend.db_services.redis.util import (
    is_redis_instance_type,
    is_tendisplus_instance_type,
    is_tendisssd_instance_type,
    is_twemproxy_proxy_type,
)
from backend.flow.consts import DEFAULT_TENDISPLUS_KVSTORECOUNT, ConfigTypeEnum
from backend.flow.utils.redis.redis_cluster_nodes import get_masters_with_slots
from backend.flow.utils.redis.redis_context_dataclass import ActKwargs
from backend.flow.utils.redis.redis_proxy_util import decode_twemproxy_backends
from backend.utils.time import datetime2str

from .models import TendisDtsServer

logger = logging.getLogger("flow")


def get_safe_regex_pattern(key_regex):
    """
    将用户输入的正则表达式转换为正确的正则表达式
    """
    if key_regex == "":
        return ""

    if key_regex == "*" or key_regex == ".*" or key_regex.startswith("^.*"):
        return ".*"

    final_pattern = ""
    patterns = key_regex.split("\n")

    for pattern in patterns:
        tmp_pattern = pattern.strip()
        if tmp_pattern == "":
            continue

        tmp_pattern = tmp_pattern.replace("|", "\\|")
        tmp_pattern = tmp_pattern.replace(".", "\\.")
        tmp_pattern = tmp_pattern.replace("*", ".*")

        if final_pattern == "":
            if tmp_pattern.startswith("^"):
                final_pattern = tmp_pattern
            else:
                final_pattern = "^" + tmp_pattern
        else:
            if tmp_pattern.startswith("^"):
                final_pattern += "|" + tmp_pattern
            else:
                final_pattern += "|^" + tmp_pattern

    return final_pattern


def get_redis_type_by_cluster_type(cluster_type: str) -> str:
    """
    根据集群类型获取redis类型
    """
    if cluster_type in [
        ClusterType.TendisPredixyRedisCluster,
        ClusterType.RedisCluster,
        ClusterType.TendisTwemproxyRedisInstance,
        ClusterType.TendisRedisInstance,
        ClusterType.TendisRedisCluster,
    ]:
        return ClusterType.TendisRedisInstance.value
    elif cluster_type in [
        ClusterType.TendisPredixyTendisplusCluster,
        ClusterType.TendisTwemproxyTendisplusIns,
        ClusterType.TendisTendisplusInsance,
        ClusterType.TendisTendisplusCluster,
    ]:
        return ClusterType.TendisTendisplusInsance.value
    elif cluster_type in [ClusterType.TwemproxyTendisSSDInstance, ClusterType.TwemproxyTendisSSDInstance]:
        return ClusterType.TendisTendisSSDInstance.value
    else:
        raise Exception(f"get redis type by cluster type failed, cluster_type: {cluster_type}")


def get_cluster_info_by_id(
    bk_biz_id: int,
    cluster_id: int,
) -> dict:
    """
    根据集群id获取集群信息(域名,id,类型等)
    """
    try:
        # cluster_id = domain_without_port(cluster_id)
        cluster = Cluster.objects.get(bk_biz_id=bk_biz_id, id=cluster_id)
        one_master = cluster.storageinstance_set.filter(
            instance_role=InstanceRole.REDIS_MASTER.value, status=InstanceStatus.RUNNING
        ).first()
        proxy_conf = DBConfigApi.query_conf_item(
            params={
                "bk_biz_id": str(cluster.bk_biz_id),
                "level_name": LevelName.CLUSTER.value,
                "level_value": cluster.immute_domain,
                "level_info": {"module": str(cluster.db_module_id)},
                "conf_file": cluster.proxy_version,
                "conf_type": ConfigTypeEnum.ProxyConf,
                "namespace": cluster.cluster_type,
                "format": FormatType.MAP,
            }
        )
        proxy_content = proxy_conf.get("content", {})

        redis_conf = DBConfigApi.query_conf_item(
            params={
                "bk_biz_id": str(cluster.bk_biz_id),
                "level_name": LevelName.CLUSTER.value,
                "level_value": cluster.immute_domain,
                "level_info": {"module": str(cluster.db_module_id)},
                "conf_file": cluster.major_version,
                "conf_type": ConfigTypeEnum.DBConf,
                "namespace": cluster.cluster_type,
                "format": FormatType.MAP,
            }
        )
        redis_content = redis_conf.get("content", {})

        # 获取redis的databases
        master_addrs = ["{}:{}".format(one_master.machine.ip, one_master.port)]
        resp = DRSApi.redis_rpc(
            {
                "addresses": master_addrs,
                "db_num": 0,
                "password": redis_content.get("requirepass"),
                "command": "confxx get databases",
                "bk_cloud_id": cluster.bk_cloud_id,
            }
        )
        databases = 2
        if len(resp) > 0 and resp[0].get("result", "") != "":
            databases = int(resp[0]["result"].split("\n")[1])

        return {
            "cluster_id": cluster.id,
            "bk_cloud_id": cluster.bk_cloud_id,
            "cluster_domain": cluster.immute_domain,
            "cluster_type": cluster.cluster_type,
            "cluster_password": proxy_content.get("password"),
            "cluster_port": proxy_content.get("port"),
            "cluster_version": cluster.major_version,
            "cluster_name": cluster.name,
            "cluster_city_name": one_master.machine.bk_city.bk_idc_city_name,
            "redis_password": redis_content.get("requirepass"),
            "redis_databases": databases,
            "region": cluster.region,
        }
    except Exception as e:
        traceback.print_exc()
        logger.error(f"get cluster info by id failed {e}, cluster_id: {cluster_id}")
        raise Exception(f"get cluster info by id failed {e}, cluster_id: {cluster_id}")


def common_cluster_precheck(bk_biz_id: int, cluster_id: int):
    try:
        cluster = Cluster.objects.get(bk_biz_id=bk_biz_id, id=cluster_id)
    except Cluster.DoesNotExist:
        raise Exception(_("redis集群 {} 不存在").format(cluster_id))

    not_running_proxy = cluster.proxyinstance_set.exclude(status=InstanceStatus.RUNNING)
    if not_running_proxy.exists():
        raise Exception(
            _("redis集群 {} 存在 {} 个状态非 running 的 proxy").format(cluster.immute_domain, len(not_running_proxy))
        )

    not_running_redis = cluster.storageinstance_set.exclude(status=InstanceStatus.RUNNING)
    if not_running_redis.exists():
        raise Exception(
            _("redis集群 {} 存在 {} 个状态非 running 的 redis").format(cluster.immute_domain, len(not_running_redis))
        )

    cluster_info = get_cluster_info_by_id(bk_biz_id=bk_biz_id, cluster_id=cluster_id)
    proxy_addrs = [r.ip_port for r in cluster.proxyinstance_set.all()]
    try:
        DRSApi.redis_rpc(
            {
                "addresses": proxy_addrs,
                "db_num": 0,
                "password": cluster_info["cluster_password"],
                "command": "ping",
                "bk_cloud_id": cluster_info["bk_cloud_id"],
            }
        )
    except Exception:
        raise Exception(_("redis集群:{} proxy:{} ping失败").format(cluster.immute_domain, proxy_addrs))

    redis_addrs = [r.ip_port for r in cluster.storageinstance_set.all()]
    try:
        DRSApi.redis_rpc(
            {
                "addresses": redis_addrs,
                "db_num": 0,
                "password": cluster_info["redis_password"],
                "command": "ping",
                "bk_cloud_id": cluster_info["bk_cloud_id"],
            }
        )
    except Exception:
        raise Exception(_("redis集群:{} redis:{} ping失败").format(cluster.immute_domain, redis_addrs))
    master_insts = cluster.storageinstance_set.filter(instance_role=InstanceRole.REDIS_MASTER.value)
    if not master_insts:
        raise Exception(_("redis集群 {} 没有master??").format(cluster.immute_domain))
    for master_obj in master_insts:
        if not master_obj.as_ejector or not master_obj.as_ejector.first():
            raise Exception(
                _("redis集群{} master {} 没有 slave").format(
                    cluster.immute_domain,
                    master_obj.ip_port,
                )
            )


def get_cluster_one_running_master(bk_biz_id: int, cluster_id: int) -> dict:
    """
    获取集群下的slaves实例信息
    """
    try:
        cluster = Cluster.objects.get(bk_biz_id=bk_biz_id, id=cluster_id)
        one_master_instance = cluster.storageinstance_set.filter(
            instance_role=InstanceRole.REDIS_MASTER.value, status=InstanceStatus.RUNNING
        ).first()
        running_master = {
            "ip": one_master_instance.machine.ip,
            "port": one_master_instance.port,
            "status": one_master_instance.status,
            "instance_role": one_master_instance.instance_role,
        }
        return running_master
    except Exception as e:
        logger.error(f"get cluster one running master data failed {e}, cluster_id: {cluster_id}")
        raise Exception(f"get cluster one running master data failed {e}, cluster_id: {cluster_id}")


def get_cluster_segment_info(cluster_id: int) -> Tuple[dict, dict]:
    master_segment_info = {}
    slave_segment_info = {}
    cluster = Cluster.objects.get(id=cluster_id)
    for dtl_row in cluster.nosqlstoragesetdtl_set.all():
        master_obj = dtl_row.instance
        master_inst = "{}:{}".format(master_obj.machine.ip, master_obj.port)
        seg_start = int(dtl_row.seg_range.split("-")[0])
        seg_end = int(dtl_row.seg_range.split("-")[1])
        master_segment_info[master_inst] = {"segment_start": seg_start, "segment_end": seg_end}
        if master_obj.as_ejector and master_obj.as_ejector.first():
            slave_obj = master_obj.as_ejector.get().receiver
            slave_inst = "{}:{}".format(slave_obj.machine.ip, slave_obj.port)
            slave_segment_info[slave_inst] = {"segment_start": seg_start, "segment_end": seg_end}
    return master_segment_info, slave_segment_info


def get_dbm_cluster_slaves_data(bk_biz_id: int, cluster_id: int) -> Tuple[list, list]:
    """
    获取dbm集群的slaves实例信息
    """
    try:
        cluster = Cluster.objects.get(bk_biz_id=bk_biz_id, id=cluster_id)
        slave_instances = []
        uniq_hosts = set()
        slave_hosts = []
        kvstore: int = 0
        _, slave_segment_info = get_cluster_segment_info(cluster_id)
        for slave in cluster.storageinstance_set.filter(instance_role=InstanceRole.REDIS_SLAVE.value):
            if is_tendisplus_instance_type(cluster.cluster_type):
                kvstore = DEFAULT_TENDISPLUS_KVSTORECOUNT
            else:
                kvstore = 1
            slave_inst = "{}:{}".format(slave.machine.ip, slave.port)
            seg_start = -1
            seg_end = -1
            if slave_inst in slave_segment_info:
                seg_start = slave_segment_info[slave_inst]["segment_start"]
                seg_end = slave_segment_info[slave_inst]["segment_end"]
            slave_instances.append(
                {
                    "ip": slave.machine.ip,
                    "port": slave.port,
                    "db_type": get_redis_type_by_cluster_type(cluster.cluster_type),
                    "status": slave.status,
                    "data_size": 0,
                    "kvstorecount": kvstore,
                    "segment_start": seg_start,
                    "segment_end": seg_end,
                }
            )
            if slave.machine.ip in uniq_hosts:
                continue
            uniq_hosts.add(slave.machine.ip)
            slave_hosts.append(
                {
                    "ip": slave.machine.ip,
                    "mem_info": {},
                    "disk_info": {},
                }
            )
        return slave_instances, slave_hosts
    except Exception as e:
        logger.error(f"get cluster slave data failed {e}, cluster_id: {cluster_id}")
        raise Exception(f"get cluster slave data failed {e}, cluster_id: {cluster_id}")


def get_rollback_cluster_masters_data(rollback_row: TbTendisRollbackTasks) -> Tuple[list, list]:
    """
    获取数据构造临时集群的masters实例信息
    """
    master_instances = []
    master_hosts = []
    uniq_hosts = set()
    kvstore: int = 0
    proxy_backend_decoded = {}
    if is_twemproxy_proxy_type(rollback_row.temp_cluster_type):
        proxy_ip_port = rollback_row.temp_cluster_proxy.split(IP_PORT_DIVIDER)
        proxy_admin_addr = proxy_ip_port[0] + ":" + str(int(proxy_ip_port[1]) + 1000)
        resp = DRSApi.twemproxy_rpc(
            {
                "addresses": [proxy_admin_addr],
                "db_num": 0,
                "password": "",
                "command": "get nosqlproxy servers",
                "bk_cloud_id": rollback_row.bk_cloud_id,
            }
        )
        _, proxy_backend_decoded = decode_twemproxy_backends(resp[0]["result"])

    for master in rollback_row.temp_instance_range:
        if is_tendisplus_instance_type(rollback_row.temp_cluster_type):
            kvstore = DEFAULT_TENDISPLUS_KVSTORECOUNT
        else:
            kvstore = 1
        ip_port = master.split(IP_PORT_DIVIDER)

        segment_start = -1
        segment_end = -1
        if master in proxy_backend_decoded:
            segment_start = proxy_backend_decoded.get(master).segment_start
            segment_end = proxy_backend_decoded.get(master).segment_end
        master_instances.append(
            {
                "ip": ip_port[0],
                "port": int(ip_port[1]),
                "db_type": get_redis_type_by_cluster_type(rollback_row.temp_cluster_type),
                "status": InstanceStatus.RUNNING,
                "data_size": 0,
                "kvstorecount": kvstore,
                "segment_start": segment_start,
                "segment_end": segment_end,
            }
        )
        if ip_port[0] in uniq_hosts:
            continue
        uniq_hosts.add(ip_port[0])
        master_hosts.append(
            {
                "ip": ip_port[0],
                "mem_info": {},
                "disk_info": {},
            }
        )
    return master_instances, master_hosts


def get_user_built_cluster_masters_data(
    addr: str, password: str, bk_cloud_id: int, cluster_type: str
) -> Tuple[list, list]:
    """
    获取用户自建集群的masters实例信息
    """
    master_instances = []
    master_hosts = []
    uniq_hosts = set()
    if cluster_type == ClusterType.TendisRedisInstance:
        ip_port = addr.split(IP_PORT_DIVIDER)
        master_instances.append(
            {
                "ip": ip_port[0],
                "port": int(ip_port[1]),
                "db_type": get_redis_type_by_cluster_type(cluster_type),
                "status": InstanceStatus.RUNNING,
                "data_size": 0,
                "kvstorecount": 1,
                "segment_start": -1,
                "segment_end": -1,
            }
        )
        master_hosts.append(
            {
                "ip": ip_port[0],
                "mem_info": {},
                "disk_info": {},
            }
        )
    elif cluster_type == ClusterType.TendisRedisCluster:
        resp = DRSApi.redis_rpc(
            {
                "addresses": [addr],
                "db_num": 0,
                "password": password,
                "command": "cluster nodes",
                "bk_cloud_id": bk_cloud_id,
            }
        )
        masters_with_slots = get_masters_with_slots(resp[0]["result"])
        if len(masters_with_slots) == 0:
            logger.error("user built cluster({}) has no master with slots".format(addr))
            raise Exception("user built cluster({}) has no master with slots".format(addr))
        for master in masters_with_slots:
            master_instances.append(
                {
                    "ip": master.ip,
                    "port": master.port,
                    "db_type": get_redis_type_by_cluster_type(cluster_type),
                    "status": InstanceStatus.RUNNING,
                    "data_size": 0,
                    "kvstorecount": 1,
                    "segment_start": -1,
                    "segment_end": -1,
                }
            )
            if master.ip in uniq_hosts:
                continue
            uniq_hosts.add(master.ip)
            master_hosts.append(
                {
                    "ip": master.ip,
                    "mem_info": {},
                    "disk_info": {},
                }
            )
    return master_instances, master_hosts


def decode_info_cmd(info_str: str) -> Dict:
    info_ret: Dict[str, dict] = {}
    info_list: List = info_str.split("\n")
    for info_item in info_list:
        info_item = info_item.strip()
        if info_item.startswith("#"):
            continue
        if len(info_item) == 0:
            continue
        tmp_list = info_item.split(IP_PORT_DIVIDER, 1)
        if len(tmp_list) < 2:
            continue
        tmp_list[0] = tmp_list[0].strip()
        tmp_list[1] = tmp_list[1].strip()
        info_ret[tmp_list[0]] = tmp_list[1]
    return info_ret


def get_redis_slaves_data_size(cluster_data: dict) -> list:
    """
    获取redis slave的数据大小
    """
    info_cmd: str = ""
    if is_redis_instance_type(cluster_data["cluster_type"]):
        info_cmd = "info memory"
    elif is_tendisplus_instance_type(cluster_data["cluster_type"]):
        info_cmd = "info Dataset"
    elif is_tendisssd_instance_type(cluster_data["cluster_type"]):
        info_cmd = "info"
    slave_addrs = [slave["ip"] + IP_PORT_DIVIDER + str(slave["port"]) for slave in cluster_data["slave_instances"]]
    resp = DRSApi.redis_rpc(
        {
            "addresses": slave_addrs,
            "db_num": 0,
            "password": cluster_data["redis_password"],
            "command": info_cmd,
            "bk_cloud_id": cluster_data["bk_cloud_id"],
        }
    )
    info_ret: Dict[str, Dict] = {}
    for item in resp:
        info_ret[item["address"]] = decode_info_cmd(item["result"])
    new_slave_instances: List = []
    for slave in cluster_data["slave_instances"]:
        slave_addr = slave["ip"] + IP_PORT_DIVIDER + str(slave["port"])
        if slave["db_type"] == ClusterType.TendisRedisInstance.value:
            slave["data_size"] = int(info_ret[slave_addr]["used_memory"])
        elif slave["db_type"] == ClusterType.TendisTendisplusInsance.value:
            slave["data_size"] = int(info_ret[slave_addr]["rocksdb.total-sst-files-size"])
        elif slave["db_type"] == ClusterType.TendisTendisSSDInstance.value:
            rockdb_size = 0
            level_head_reg = re.compile(r"^level-\d+$")
            level_data_reg = re.compile(r"^bytes=(\d+),num_entries=(\d+),num_deletions=(\d+)")
            for k, v in info_ret[slave_addr].items():
                if level_head_reg.match(k):
                    tmp_list = level_data_reg.findall(v)
                    if len(tmp_list) != 1:
                        err = f"redis:{slave_addr} info 'RocksDB Level stats' format not correct,{k}:{v}"
                        logging.error(err)
                        raise Exception(err)
                    size01 = int(tmp_list[0][0])
                    rockdb_size += size01
            slave["data_size"] = rockdb_size
        new_slave_instances.append(slave)
    return new_slave_instances


def complete_redis_dts_kwargs_src_data(bk_biz_id: int, dts_copy_type: str, info: dict, act_kwargs: ActKwargs):
    """
    完善redis dts 源集群数据
    """
    src_cluster_data: dict = {}
    if dts_copy_type == DtsCopyType.USER_BUILT_TO_DBM:
        src_cluster_data["cluster_addr"] = info["src_cluster"]
        src_cluster_data["cluster_id"] = 0
        src_cluster_data["cluster_password"] = info["src_cluster_password"]
        src_cluster_data["redis_password"] = info["src_cluster_password"]
        src_cluster_data["cluster_type"] = info["src_cluster_type"]

        # 无法确定源集群的bk_cloud_id,此时以目的集群的为准
        cluster_info = get_cluster_info_by_id(bk_biz_id, int(info["dst_cluster"]))
        src_cluster_data["bk_cloud_id"] = cluster_info["bk_cloud_id"]
        src_cluster_data["cluster_city_name"] = cluster_info["cluster_city_name"]

        # 获取源集群的master信息做为迁移源实例
        master_instances, master_hosts = get_user_built_cluster_masters_data(
            src_cluster_data["cluster_addr"],
            src_cluster_data["cluster_password"],
            src_cluster_data["bk_cloud_id"],
            src_cluster_data["cluster_type"],
        )
        src_cluster_data["one_running_master"] = master_instances[0]
        src_cluster_data["slave_instances"] = master_instances
        src_cluster_data["slave_hosts"] = master_hosts
        src_cluster_data["slave_instances"] = get_redis_slaves_data_size(src_cluster_data)
    elif dts_copy_type == DtsCopyType.COPY_FROM_ROLLBACK_INSTANCE:
        src_cluster_data["cluster_addr"] = info["src_cluster"]
        src_cluster_data["cluster_id"] = 0
        recovery_time = datetime2str(info["recovery_time_point"])
        rollback_row = TbTendisRollbackTasks.objects.get(
            temp_cluster_proxy=info["src_cluster"], recovery_time_point=recovery_time, destroyed_status=0
        )

        proxy_password_bytes = ast.literal_eval(rollback_row.temp_proxy_password)
        redis_password_bytes = ast.literal_eval(rollback_row.temp_redis_password)
        src_cluster_data["cluster_password"] = base64.b64decode(proxy_password_bytes).decode("utf-8")
        src_cluster_data["redis_password"] = base64.b64decode(redis_password_bytes).decode("utf-8")
        src_cluster_data["cluster_type"] = rollback_row.prod_cluster_type

        cluster_info = get_cluster_info_by_id(bk_biz_id, int(info["dst_cluster"]))
        src_cluster_data["bk_cloud_id"] = cluster_info["bk_cloud_id"]
        src_cluster_data["cluster_city_name"] = cluster_info["cluster_city_name"]

        # 获取源集群的master信息做为迁移源实例
        master_instances, master_hosts = get_rollback_cluster_masters_data(rollback_row)
        src_cluster_data["one_running_master"] = master_instances[0]
        src_cluster_data["slave_instances"] = master_instances
        src_cluster_data["slave_hosts"] = master_hosts
        src_cluster_data["slave_instances"] = get_redis_slaves_data_size(src_cluster_data)
    else:
        cluster_info = get_cluster_info_by_id(bk_biz_id, int(info["src_cluster"]))
        src_cluster_data["bk_cloud_id"] = cluster_info["bk_cloud_id"]
        src_cluster_data["cluster_id"] = cluster_info["cluster_id"]
        src_cluster_data["cluster_addr"] = (
            cluster_info["cluster_domain"] + IP_PORT_DIVIDER + str(cluster_info["cluster_port"])
        )
        src_cluster_data["cluster_password"] = cluster_info["cluster_password"]
        src_cluster_data["cluster_type"] = cluster_info["cluster_type"]
        src_cluster_data["cluster_city_name"] = cluster_info["cluster_city_name"]
        src_cluster_data["redis_password"] = cluster_info["redis_password"]

        src_cluster_data["one_running_master"] = get_cluster_one_running_master(bk_biz_id, int(info["src_cluster"]))
        src_slave_instances, src_slave_hosts = get_dbm_cluster_slaves_data(bk_biz_id, int(info["src_cluster"]))
        src_cluster_data["slave_instances"] = src_slave_instances
        src_cluster_data["slave_hosts"] = src_slave_hosts
        src_cluster_data["slave_instances"] = get_redis_slaves_data_size(src_cluster_data)

    act_kwargs.cluster["src"] = src_cluster_data


def complete_dst_data_without_cluster_id(bk_biz_id: int, dst_cluster_type: str, info: dict, act_kwargs: ActKwargs):
    """
    未知 dst_cluster_id,完善redis dts 目的集群数据
    """
    dst_cluster_data: dict = {}
    dst_proxy_instances: list = []
    dst_cluster_data["cluster_id"] = 0
    dst_cluster_data["cluster_addr"] = info["dst_cluster"]
    dst_cluster_data["cluster_password"] = info["dst_cluster_password"]
    dst_cluster_data["cluster_type"] = dst_cluster_type
    # 目的集群的bk_cloud_id,此时以源集群的为准
    dst_cluster_data["bk_cloud_id"] = act_kwargs.cluster["src"]["bk_cloud_id"]
    dst_proxy_instances.append(
        {
            "addr": info["dst_cluster"],
            "status": InstanceStatus.RUNNING,
        }
    )
    dst_cluster_data["proxy_instances"] = dst_proxy_instances
    act_kwargs.cluster["dst"] = dst_cluster_data


def complete_dst_data_with_cluster_id(bk_biz_id: int, dst_cluster_id: int, act_kwargs: ActKwargs):
    """
    已知 dst_cluster_id,完善redis dts 目的集群数据
    """
    dst_cluster_data: dict = {}
    dst_proxy_instances: list = []
    dst_master_instances: list = []
    cluster_info = get_cluster_info_by_id(bk_biz_id, dst_cluster_id)
    dst_cluster_data["cluster_id"] = cluster_info["cluster_id"]
    dst_cluster_data["bk_cloud_id"] = cluster_info["bk_cloud_id"]
    dst_cluster_data["cluster_addr"] = (
        cluster_info["cluster_domain"] + IP_PORT_DIVIDER + str(cluster_info["cluster_port"])
    )
    dst_cluster_data["cluster_password"] = cluster_info["cluster_password"]
    dst_cluster_data["cluster_type"] = cluster_info["cluster_type"]
    dst_cluster_data["redis_password"] = cluster_info["redis_password"]

    cluster = Cluster.objects.get(id=dst_cluster_id)
    dst_cluster_data["major_version"] = cluster.major_version
    for proxy in cluster.proxyinstance_set.filter(status=InstanceStatus.RUNNING):
        dst_proxy_instances.append(
            {
                "addr": proxy.machine.ip + IP_PORT_DIVIDER + str(proxy.port),
                "status": proxy.status,
            }
        )
    for master in cluster.storageinstance_set.filter(instance_role=InstanceRole.REDIS_MASTER.value):
        dst_master_instances.append(
            {
                "ip": master.machine.ip,
                "port": master.port,
                "db_type": get_redis_type_by_cluster_type(cluster.cluster_type),
                "status": master.status,
                "data_size": 0,
                "kvstorecount": 1,
                "segment_start": -1,
                "segment_end": -1,
            }
        )
    dst_cluster_data["running_masters"] = dst_master_instances

    dst_cluster_data["proxy_instances"] = dst_proxy_instances
    act_kwargs.cluster["dst"] = dst_cluster_data


def complete_redis_dts_kwargs_dst_data(
    bk_biz_id: int, dts_copy_type: str, dst_cluster_type: str, info: dict, act_kwargs: ActKwargs
):
    """
    完善redis dts 目的集群数据
    """
    if dts_copy_type == DtsCopyType.COPY_TO_OTHER_SYSTEM.value:
        complete_dst_data_without_cluster_id(bk_biz_id, ClusterType.TendisRedisInstance.value, info, act_kwargs)
    elif dts_copy_type in [
        DtsBillType.REDIS_CLUSTER_SHARD_NUM_UPDATE.value,
        DtsBillType.REDIS_CLUSTER_TYPE_UPDATE.value,
    ]:
        dst_addr_pair = info["dst_cluster"].split(":")
        dst_domain = dst_addr_pair[0]
        cluster: Cluster = None
        try:
            cluster = Cluster.objects.get(bk_biz_id=bk_biz_id, immute_domain=dst_domain)
        except Cluster.DoesNotExist:
            complete_dst_data_without_cluster_id(bk_biz_id, dst_cluster_type, info, act_kwargs)
            return
        complete_dst_data_with_cluster_id(bk_biz_id, cluster.id, act_kwargs)
    else:
        complete_dst_data_with_cluster_id(bk_biz_id, int(info["dst_cluster"]), act_kwargs)


def get_etc_hosts_lines_and_ips(
    bk_biz_id: int, dts_copy_type: str, info: dict, dst_install_params: dict = None
) -> dict:
    """
    获取etc_hosts文件的内容和ip列表
    """
    etc_hosts_lines = ""  # 代表需要添加到 /etc/hosts 中的内容
    ip_list = set()  # 代表需要添加 /etc/hosts 的ip列表
    if dts_copy_type == DtsCopyType.USER_BUILT_TO_DBM.value:
        dst_cluster = Cluster.objects.get(bk_biz_id=bk_biz_id, id=int(info["dst_cluster"]))
        idx = 0
        for proxy_inst in dst_cluster.proxyinstance_set.filter(status=InstanceStatus.RUNNING):
            if idx == 0:
                etc_hosts_lines += "{} {}\n".format(proxy_inst.machine.ip, dst_cluster.immute_domain)
                idx = 1
            ip_list.add(proxy_inst.machine.ip)
    elif dts_copy_type == DtsCopyType.COPY_TO_OTHER_SYSTEM.value:
        src_cluster = Cluster.objects.get(bk_biz_id=bk_biz_id, id=int(info["src_cluster"]))
        for proxy_inst in src_cluster.proxyinstance_set.filter(status=InstanceStatus.RUNNING):
            etc_hosts_lines += "{} {}\n".format(proxy_inst.machine.ip, src_cluster.immute_domain)
            break
        for slave_inst in src_cluster.storageinstance_set.filter(
            status=InstanceStatus.RUNNING, instance_role=InstanceRole.REDIS_SLAVE.value
        ):
            ip_list.add(slave_inst.machine.ip)
    elif dts_copy_type in [
        DtsBillType.REDIS_CLUSTER_SHARD_NUM_UPDATE.value,
        DtsBillType.REDIS_CLUSTER_TYPE_UPDATE.value,
    ]:
        src_cluster = Cluster.objects.get(bk_biz_id=bk_biz_id, id=int(info["src_cluster"]))
        for proxy_inst in src_cluster.proxyinstance_set.filter(status=InstanceStatus.RUNNING):
            etc_hosts_lines += "{} {}\n".format(proxy_inst.machine.ip, src_cluster.immute_domain)
            break
        proxy_ip = dst_install_params["proxy"][0]["ip"]
        etc_hosts_lines += "{} {}\n".format(proxy_ip, dst_install_params["cluster_domain"])
        for slave_inst in src_cluster.storageinstance_set.filter(
            status=InstanceStatus.RUNNING, instance_role=InstanceRole.REDIS_SLAVE.value
        ):
            ip_list.add(slave_inst.machine.ip)
    elif dts_copy_type == DtsCopyType.COPY_FROM_ROLLBACK_INSTANCE.value:
        recovery_time = datetime2str(info["recovery_time_point"])
        rollback_task = TbTendisRollbackTasks.objects.get(
            temp_cluster_proxy=info["src_cluster"], recovery_time_point=recovery_time, destroyed_status=0
        )
        for master in rollback_task.temp_instance_range:
            ip_port = master.split(IP_PORT_DIVIDER)
            ip_list.add(ip_port[0])
        dst_cluster = Cluster.objects.get(bk_biz_id=bk_biz_id, id=int(info["dst_cluster"]))
        for proxy_inst in dst_cluster.proxyinstance_set.filter(status=InstanceStatus.RUNNING):
            etc_hosts_lines += "{} {}\n".format(proxy_inst.machine.ip, dst_cluster.immute_domain)
            break
    else:
        src_cluster = Cluster.objects.get(bk_biz_id=bk_biz_id, id=int(info["src_cluster"]))
        for proxy_inst in src_cluster.proxyinstance_set.filter(status=InstanceStatus.RUNNING):
            etc_hosts_lines += "{} {}\n".format(proxy_inst.machine.ip, src_cluster.immute_domain)
            break
        dst_cluster = Cluster.objects.get(bk_biz_id=bk_biz_id, id=int(info["dst_cluster"]))
        for proxy_inst in dst_cluster.proxyinstance_set.filter(status=InstanceStatus.RUNNING):
            etc_hosts_lines += "{} {}\n".format(proxy_inst.machine.ip, dst_cluster.immute_domain)
            break
        for slave_inst in src_cluster.storageinstance_set.filter(
            status=InstanceStatus.RUNNING, instance_role=InstanceRole.REDIS_SLAVE.value
        ):
            ip_list.add(slave_inst.machine.ip)
    for row in TendisDtsServer.objects.all():
        ip_list.add(row.ip)
    return {
        "etc_hosts_lines": etc_hosts_lines,
        "ip_list": list(ip_list),
    }


def is_in_full_transfer(row: TbTendisDtsTask) -> bool:
    """
    判断是否全量传输中
    """
    if row.src_dbtype == ClusterType.TendisTendisSSDInstance:
        if (
            row.task_type
            in [
                DtsTaskType.TENDISSSD_BACKUP,
                DtsTaskType.TENDISSSD_BACKUPFILE_FETCH,
                DtsTaskType.TENDISSSD_TREDISDUMP,
                DtsTaskType.TENDISSSD_CMDSIMPOTER,
            ]
            and row.status in [0, 1]
        ):
            return True
    if row.src_dbtype == ClusterType.TendisRedisInstance:
        if row.task_type == DtsTaskType.MAKE_CACHE_SYNC and "rdb" in row.message and row.status in [0, 1]:
            return True

    if row.src_dbtype == ClusterType.TendisTendisplusInsance:
        if row.task_type in [DtsTaskType.TENDISPLUS_MAKESYNC, DtsTaskType.TENDISPLUS_SENDBULK] and row.status in [
            0,
            1,
        ]:
            return True
    return False


def is_full_transfer_failed(row: TbTendisDtsTask) -> bool:
    """
    判断是否全量传输失败
    """
    if row.src_dbtype == ClusterType.TendisTendisSSDInstance:
        if (
            row.task_type
            in [
                DtsTaskType.TENDISSSD_BACKUP,
                DtsTaskType.TENDISSSD_BACKUPFILE_FETCH,
                DtsTaskType.TENDISSSD_TREDISDUMP,
                DtsTaskType.TENDISSSD_CMDSIMPOTER,
            ]
            and row.status == -1
        ):
            return True
    if row.src_dbtype == ClusterType.TendisRedisInstance:
        if row.task_type == DtsTaskType.MAKE_CACHE_SYNC and row.status == -1:
            return True

    if row.src_dbtype == ClusterType.TendisTendisplusInsance:
        if row.task_type in [DtsTaskType.TENDISPLUS_MAKESYNC, DtsTaskType.TENDISPLUS_SENDBULK] and row.status == -1:
            return True
    return False


def is_in_incremental_sync(row: TbTendisDtsTask) -> bool:
    """
    判断是否增量同步中
    """
    if row.src_dbtype == ClusterType.TendisTendisSSDInstance:
        if row.task_type in [DtsTaskType.TENDISSSD_MAKESYNC, DtsTaskType.TENDISSSD_WATCHOLDSYNC] and row.status in [
            0,
            1,
        ]:
            return True
    if row.src_dbtype == ClusterType.TendisRedisInstance:
        if row.task_type in [DtsTaskType.MAKE_CACHE_SYNC, DtsTaskType.WATCH_CACHE_SYNC] and row.status in [0, 1]:
            return True

    if row.src_dbtype == ClusterType.TendisTendisplusInsance:
        if row.task_type in [DtsTaskType.TENDISPLUS_SENDINCR] and row.status in [0, 1]:
            return True
    return False


def is_incremental_sync_failed(row: TbTendisDtsTask) -> bool:
    """
    判断是否增量同步失败
    """
    if row.src_dbtype == ClusterType.TendisTendisSSDInstance:
        if row.task_type in [DtsTaskType.TENDISSSD_MAKESYNC, DtsTaskType.TENDISSSD_WATCHOLDSYNC] and row.status == -1:
            return True
    if row.src_dbtype == ClusterType.TendisRedisInstance:
        if row.task_type == DtsTaskType.WATCH_CACHE_SYNC and row.status == -1:
            return True

    if row.src_dbtype == ClusterType.TendisTendisplusInsance:
        if row.task_type in [DtsTaskType.TENDISPLUS_SENDINCR] and row.status == -1:
            return True
    return False


def is_pending_execution(row: TbTendisDtsTask) -> bool:
    """
    判断是否待执行
    """
    if row.task_type == "" and row.status == 0:
        return True

    return False


def is_transfer_competed(row: TbTendisDtsTask) -> bool:
    """
    判断是否传输完成
    """
    if row.status == 2:
        return True
    return False


def is_transfer_terminated(row: TbTendisDtsTask) -> bool:
    """
    判断是否传输被终止
    """
    if row.sync_operate == DtsOperateType.FORCE_KILL_SUCC and row.status in [-1, 2]:
        return True
    return False


def dts_task_status(task_row: TbTendisDtsTask) -> str:
    """
    获取task任务状态
    """
    if is_pending_execution(task_row):
        return DtsSyncStatus.PENDING_EXECUTION.value
    if is_in_full_transfer(task_row):
        return DtsSyncStatus.IN_FULL_TRANSFER.value
    if is_full_transfer_failed(task_row):
        return DtsSyncStatus.FULL_TRANSFER_FAILED.value
    if is_in_incremental_sync(task_row):
        return DtsSyncStatus.IN_INCREMENTAL_SYNC.value
    if is_incremental_sync_failed(task_row):
        return DtsSyncStatus.INCREMENTAL_SYNC_FAILED.value
    if is_transfer_competed(task_row):
        return DtsSyncStatus.TRANSFER_COMPLETED.value
    if is_transfer_terminated(task_row):
        return DtsSyncStatus.TRANSFER_TERMINATED.value
    return DtsSyncStatus.UNKNOWN.value


def dts_job_cnt_and_status(job: TbTendisDTSJob) -> dict:
    """
    获取job 任务状态
    """
    ret = {}
    pending_exec_cnt = 0
    running_cnt = 0
    failed_cnt = 0
    success_cnt = 0
    transfer_completed_cnt = 0
    transfer_terminated_cnt = 0
    full_transfer_failed_cnt = 0
    incremental_sync_failed_cnt = 0
    full_transfer_running_cnt = 0
    incremental_sync_running_cnt = 0
    tasks = TbTendisDtsTask.objects.filter(
        Q(bill_id=job.bill_id) & Q(src_cluster=job.src_cluster) & Q(dst_cluster=job.dst_cluster)
    )
    for task in tasks:
        if is_pending_execution(task):
            pending_exec_cnt += 1
        elif task.task_type == DtsTaskType.TENDISSSD_BACKUP.value and task.status == 0:
            pending_exec_cnt += 1
        elif task.task_type == DtsTaskType.TENDISSSD_BACKUP.value and task.status == 1:
            running_cnt += 1
        elif task.task_type != DtsTaskType.TENDISSSD_BACKUP.value and (task.status == 0 or task.status == 1):
            running_cnt += 1
        elif task.status == -1:
            failed_cnt += 1
        elif task.status == 2:
            success_cnt += 1

        if is_transfer_competed(task):
            transfer_completed_cnt += 1
        elif is_transfer_terminated(task):
            transfer_terminated_cnt += 1
        elif is_full_transfer_failed(task):
            full_transfer_failed_cnt += 1
        elif is_incremental_sync_failed(task):
            incremental_sync_failed_cnt += 1
        elif is_in_full_transfer(task):
            full_transfer_running_cnt += 1
        elif is_in_incremental_sync(task):
            incremental_sync_running_cnt += 1
    ret["total_cnt"] = len(tasks)
    ret["pending_exec_cnt"] = pending_exec_cnt
    ret["running_cnt"] = running_cnt
    ret["failed_cnt"] = failed_cnt
    ret["success_cnt"] = success_cnt
    if pending_exec_cnt == len(tasks):
        ret["status"] = DtsSyncStatus.PENDING_EXECUTION.value
    elif transfer_completed_cnt == len(tasks):
        ret["status"] = DtsSyncStatus.TRANSFER_COMPLETED.value
    elif transfer_terminated_cnt == len(tasks):
        ret["status"] = DtsSyncStatus.TRANSFER_TERMINATED.value
    elif full_transfer_failed_cnt > 0:
        ret["status"] = DtsSyncStatus.FULL_TRANSFER_FAILED.value
    elif incremental_sync_failed_cnt > 0:
        ret["status"] = DtsSyncStatus.INCREMENTAL_SYNC_FAILED.value
    elif full_transfer_running_cnt > 0:
        ret["status"] = DtsSyncStatus.IN_FULL_TRANSFER.value
    elif incremental_sync_running_cnt > 0:
        ret["status"] = DtsSyncStatus.IN_INCREMENTAL_SYNC.value
    return ret
