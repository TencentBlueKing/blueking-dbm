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
import hashlib
import json
import logging.config
import re
from collections import defaultdict
from typing import Any, Dict, List, Tuple

from django.utils.translation import ugettext as _

from backend.components import DBConfigApi, DRSApi
from backend.components.dbconfig.constants import FormatType, LevelName, OpType, ReqType
from backend.configuration.constants import DBType
from backend.constants import IP_PORT_DIVIDER
from backend.db_meta.enums import ClusterType, InstanceRole, InstanceStatus
from backend.db_meta.models import Cluster
from backend.db_package.models import Package
from backend.db_services.redis.util import (
    is_predixy_proxy_type,
    is_redis_cluster_protocal,
    is_redis_instance_type,
    is_tendisplus_instance_type,
    is_tendisssd_instance_type,
    is_twemproxy_proxy_type,
)
from backend.flow.consts import (
    DEFAULT_CONFIG_CONFIRM,
    DEFAULT_DB_MODULE_ID,
    DEFAULT_REDIS_DBNUM,
    DEFAULT_TWEMPROXY_ADMIN_PORT_EXTRA,
    ConfigFileEnum,
    ConfigTypeEnum,
    MediumEnum,
    RedisCapacityUpdateType,
)
from backend.flow.utils.base.payload_handler import PayloadHandler
from backend.flow.utils.redis.redis_util import version_ge

logger = logging.getLogger("flow")


class TwemproxyBackendItem:
    def __init__(self, addr: str, app: str, seg_start: int, seg_end: int, weight: int):
        self.addr = addr
        self.app = app
        self.segment_start = seg_start
        self.segment_end = seg_end
        self.weight = weight

    # String 用于打印
    def __str__(self):
        return f"{self.addr} {self.app} {self.segment_start}-{self.segment_end} {self.weight}"

    # StringWithoutApp 不带app信息
    def string_without_app(self):
        return f"{self.addr} {self.segment_start}-{self.segment_end} {self.weight}"

    # StringWithoutWeight
    def string_without_weight(self):
        return f"{self.addr} {self.app} {self.segment_start}-{self.segment_end}"


def decode_twemproxy_backends(backends_str: str) -> Tuple[List[TwemproxyBackendItem], Dict[str, TwemproxyBackendItem]]:
    backend_list = []
    backend_addr_map = {}
    backends_str = backends_str.strip()
    lines = backends_str.split("\n")
    for line in lines:
        line = line.strip()
        list01 = line.split()
        if len(list01) != 4:
            err = f"twemproxy backend:{line} format not correct"
            raise ValueError(err)
        backend_item = TwemproxyBackendItem(
            addr=list01[0],
            app=list01[1],
            seg_start=int(list01[2].split("-")[0]),
            seg_end=int(list01[2].split("-")[1]),
            weight=int(list01[3]),
        )
        backend_list.append(backend_item)
        backend_addr_map[backend_item.addr] = backend_item
    return backend_list, backend_addr_map


class PredixyInfoServer:
    """
    predixy info server项
    """

    def __init__(self):
        self.server = ""
        self.role = ""
        self.group = ""
        self.dc = ""
        self.current_is_fail = 0
        self.connections = 0
        self.connect = 0
        self.requests = 0
        self.responses = 0
        self.send_bytes = 0
        self.recv_bytes = 0

    def __str__(self):
        return f"Server:{self.server} Role:{self.role} Group:{self.group} DC:{self.dc}"


def decode_predixy_info_servers(info_str) -> List[PredixyInfoServer]:
    """
    解析predixy info servers
    """
    rets = []
    info_list = info_str.split("\n")
    item = PredixyInfoServer()
    for info_item in info_list:
        info_item = info_item.strip()
        if info_item.startswith("#"):
            continue
        if len(info_item) == 0:
            if item.server != "":
                rets.append(item)
                item = PredixyInfoServer()
            continue
        list01 = info_item.split(":", 1)
        if len(list01) < 2:
            continue
        if list01[0] == "Server":
            item.server = list01[1]
        elif list01[0] == "Role":
            item.role = list01[1]
        elif list01[0] == "Group":
            item.group = list01[1]
        elif list01[0] == "DC":
            item.dc = list01[1]
        elif list01[0] == "CurrentIsFail":
            item.current_is_fail = int(list01[1])
        elif list01[0] == "Connections":
            item.connections = int(list01[1])
        elif list01[0] == "Connect":
            item.connect = int(list01[1])
        elif list01[0] == "Requests":
            item.requests = int(list01[1])
        elif list01[0] == "Responses":
            item.responses = int(list01[1])
        elif list01[0] == "SendBytes":
            item.send_bytes = int(list01[1])
        elif list01[0] == "RecvBytes":
            item.recv_bytes = int(list01[1])
    return rets


def check_cluster_proxy_backends_consistent(cluster_id: int):
    cluster: Cluster = None
    try:
        cluster = Cluster.objects.get(id=cluster_id)
    except Cluster.DoesNotExist:
        raise Exception("src_cluster {} does not exist".format(cluster_id))

    passwd_ret = PayloadHandler.redis_get_password_by_cluster_id(cluster_id)
    proxy_addrs = []
    proxys_backend_md5 = []
    if is_twemproxy_proxy_type(cluster.cluster_type):
        # twemproxy 集群
        for proxy in cluster.proxyinstance_set.all():
            proxy_addrs.append(proxy.machine.ip + ":" + str(proxy.port + DEFAULT_TWEMPROXY_ADMIN_PORT_EXTRA))
        resp = DRSApi.twemproxy_rpc(
            {
                "addresses": proxy_addrs,
                "db_num": DEFAULT_REDIS_DBNUM,
                "password": "",
                "command": "get nosqlproxy servers",
                "bk_cloud_id": cluster.bk_cloud_id,
            }
        )
        for ele in resp:
            backends_ret, _ = decode_twemproxy_backends(ele["result"])
            sorted_backends = sorted(backends_ret, key=lambda x: x.segment_start)
            sorted_str = ""
            for bck in sorted_backends:
                sorted_str += bck.string_without_app() + "\n"
            # 求sorted_str的md5值
            md5 = hashlib.md5(sorted_str.encode("utf-8")).hexdigest()
            proxys_backend_md5.append(
                {
                    "proxy_addr": ele["address"],
                    "backend_md5": md5,
                }
            )
    elif is_predixy_proxy_type(cluster.cluster_type):
        # predixy 集群
        for proxy in cluster.proxyinstance_set.all():
            proxy_addrs.append(proxy.machine.ip + ":" + str(proxy.port))
        resp = DRSApi.redis_rpc(
            {
                "addresses": proxy_addrs,
                "db_num": DEFAULT_REDIS_DBNUM,
                "password": passwd_ret.get("redis_proxy_password"),
                "command": "info servers",
                "bk_cloud_id": cluster.bk_cloud_id,
            }
        )
        for ele in resp:
            backends_ret: list[PredixyInfoServer] = decode_predixy_info_servers(ele["result"])
            sorted_backends: list[PredixyInfoServer] = sorted(backends_ret, key=lambda x: x.server)
            sorted_str = ""
            for bck in sorted_backends:
                if bck.current_is_fail == 0:
                    sorted_str += bck.__str__() + "\n"
            # 求sorted_str的md5值
            md5 = hashlib.md5(sorted_str.encode("utf-8")).hexdigest()
            proxys_backend_md5.append(
                {
                    "proxy_addr": ele["address"],
                    "backend_md5": md5,
                }
            )
    # 检查md5是否一致
    sorted_md5 = sorted(proxys_backend_md5, key=lambda x: x["backend_md5"])
    if sorted_md5[0]["backend_md5"] != sorted_md5[-1]["backend_md5"]:
        logger.error(
            "proxy[{}->{}] backends is not same".format(sorted_md5[0]["proxy_addr"], sorted_md5[-1]["proxy_addr"])
        )
        raise Exception(
            "proxy[{}->{}] backends is not same".format(sorted_md5[0]["proxy_addr"], sorted_md5[-1]["proxy_addr"])
        )


def get_twemproxy_cluster_server_shards(bk_biz_id: int, cluster_id: int, other_to_master: dict) -> dict:
    """
    获取twemproxy集群的server_shards
    :param bk_biz_id: 业务id
    :param cluster_id: 集群id
    :param other_to_master: other实例 到 master实例的映射关系,格式为{a.a.a.a:30000 : b.b.b.b:30000}
    """
    cluster = Cluster.objects.get(id=cluster_id, bk_biz_id=bk_biz_id)
    if not is_twemproxy_proxy_type(cluster.cluster_type):
        return {}
    twemproxy_server_shards = defaultdict(dict)
    ipport_to_segment = {}
    for row in cluster.nosqlstoragesetdtl_set.all():
        ipport = row.instance.machine.ip + IP_PORT_DIVIDER + str(row.instance.port)
        ipport_to_segment[ipport] = row.seg_range

    for master_obj in cluster.storageinstance_set.filter(instance_role=InstanceRole.REDIS_MASTER.value):
        if master_obj.as_ejector and master_obj.as_ejector.first():
            slave_obj = master_obj.as_ejector.get().receiver
            master_ipport = master_obj.machine.ip + IP_PORT_DIVIDER + str(master_obj.port)
            slave_ipport = slave_obj.machine.ip + IP_PORT_DIVIDER + str(slave_obj.port)

            twemproxy_server_shards[master_obj.machine.ip][master_ipport] = ipport_to_segment[master_ipport]
            twemproxy_server_shards[slave_obj.machine.ip][slave_ipport] = ipport_to_segment[master_ipport]

    for other_ipport, master_ipport in other_to_master.items():
        if master_ipport not in ipport_to_segment:
            raise Exception(
                "master ipport {} not found seg_range, not belong cluster:{}??".format(
                    master_ipport, cluster.immute_domain
                )
            )
        other_list = other_ipport.split(IP_PORT_DIVIDER)
        other_ip = other_list[0]
        twemproxy_server_shards[other_ip][other_ipport] = ipport_to_segment[master_ipport]
    return twemproxy_server_shards


def set_backup_mode(immute_domain: str, bk_biz_id: str, namespace: str, value: str) -> Any:
    """
    设置备份备份方式
    """
    conf_items = [
        {
            "conf_name": "cache_backup_mode",
            "conf_value": value,
            "op_type": OpType.UPDATE,
        }
    ]
    data = DBConfigApi.upsert_conf_item(
        {
            "conf_file_info": {
                "conf_file": ConfigFileEnum.FullBackup.value,
                "conf_type": ConfigTypeEnum.Config.value,
                "namespace": namespace,
            },
            "conf_items": conf_items,
            "level_info": {"module": str(DEFAULT_DB_MODULE_ID)},
            "confirm": DEFAULT_CONFIG_CONFIRM,
            "req_type": ReqType.SAVE_AND_PUBLISH,
            "bk_biz_id": bk_biz_id,
            "level_name": LevelName.CLUSTER,
            "level_value": immute_domain,
        }
    )
    return data


def get_cache_backup_mode(bk_biz_id: int, cluster_id: int) -> str:
    """
    获取集群的cache_backup_mode
    :param bk_biz_id: 业务id
    :param cluster_id: 集群id
    """
    query_params = {
        "bk_biz_id": str(bk_biz_id),
        "level_name": LevelName.CLUSTER.value,
        "level_value": "",
        "level_info": {"module": str(DEFAULT_DB_MODULE_ID)},
        "conf_file": ConfigFileEnum.FullBackup.value,
        "conf_type": ConfigTypeEnum.Config.value,
        "namespace": ClusterType.TendisTwemproxyRedisInstance.value,
        "format": FormatType.MAP.value,
    }
    if cluster_id == 0:
        # 获取业务级别的配置
        query_params["level_name"] = LevelName.APP.value
        query_params["level_value"] = str(bk_biz_id)
        resp = DBConfigApi.query_conf_item(params=query_params)
        if resp["content"]:
            return resp["content"].get("cache_backup_mode", "")
    cluster: Cluster = None
    try:
        cluster = Cluster.objects.get(id=cluster_id, bk_biz_id=bk_biz_id)
    except Cluster.DoesNotExist:
        # 获取业务级别的配置
        query_params["level_name"] = LevelName.APP.value
        query_params["level_value"] = str(bk_biz_id)
        resp = DBConfigApi.query_conf_item(params=query_params)
        if resp["content"]:
            return resp["content"].get("cache_backup_mode", "")
    if not is_redis_instance_type(cluster.cluster_type):
        return ""
    # 获取集群级别的配置
    query_params["level_name"] = LevelName.CLUSTER.value
    query_params["level_value"] = cluster.immute_domain
    query_params["namespace"] = cluster.cluster_type
    try:
        resp = DBConfigApi.query_conf_item(params=query_params)
        if resp["content"]:
            return resp["content"].get("cache_backup_mode", "")
    except Exception:
        return "aof"


def get_storage_versions_by_cluster_type(cluster_type: str) -> list:
    """
    根据 cluster_type 返回对应存储主版本
    如: cluster_type==ClusterType.TendisPredixyRedisCluster
    返回结果 ['Redis-7', 'Redis-6', 'Redis-5', 'Redis-4t', 'Redis-4', 'Redis-3', 'Redis-2']
    """
    if is_redis_instance_type(cluster_type):
        ret = Package.objects.filter(db_type=DBType.Redis.value, pkg_type=MediumEnum.Redis.value).values_list(
            "version", flat=True
        )
        return list(ret)
    elif is_tendisplus_instance_type(cluster_type):
        ret = Package.objects.filter(db_type=DBType.Redis.value, pkg_type=MediumEnum.TendisPlus.value).values_list(
            "version", flat=True
        )
        return list(ret)
    elif is_tendisssd_instance_type(cluster_type):
        ret = Package.objects.filter(db_type=DBType.Redis.value, pkg_type=MediumEnum.TendisSsd.value).values_list(
            "version", flat=True
        )
        return list(ret)
    raise Exception(_("集群类型:{} 不是一个 redis 集群类型?").format(cluster_type))


def get_storage_version_names_by_cluster_type(cluster_type: str, trimSuffix: bool = False) -> list:
    """
    根据 cluster_type 返回对应存储详细版本
    如: cluster_type==ClusterType.TendisPredixyRedisCluster
    返回结果 ['redis-7.2.3.tar.gz','redis-6.2.14.tar.gz']

    trimSuffix默认为False,如果trimSuffix==True,则返回结果 ['redis-7.2.3','redis-6.2.14']
    """
    versions = []
    if is_redis_instance_type(cluster_type):
        ret = Package.objects.filter(db_type=DBType.Redis.value, pkg_type=MediumEnum.Redis.value).values_list(
            "name", flat=True
        )
        versions = list(ret)
    elif is_tendisplus_instance_type(cluster_type):
        ret = Package.objects.filter(db_type=DBType.Redis.value, pkg_type=MediumEnum.TendisPlus.value).values_list(
            "name", flat=True
        )
        versions = list(ret)
    elif is_tendisssd_instance_type(cluster_type):
        ret = Package.objects.filter(db_type=DBType.Redis.value, pkg_type=MediumEnum.TendisSsd.value).values_list(
            "name", flat=True
        )
        versions = list(ret)
    else:
        raise Exception(_("集群类型:{} 不是一个 redis 集群类型?").format(cluster_type))

    if trimSuffix:
        versions = [version.replace(".tar.gz", "") for version in versions]
        versions = [version.replace(".tgz", "") for version in versions]
    return versions


def get_cluster_storage_versions_for_upgrade(cluster_id: int) -> list:
    """
    获取集群可升级到的存储版本
    """
    cluster = Cluster.objects.get(id=cluster_id)
    online_redis_ver = get_cluster_redis_version(cluster_id=cluster_id)
    versions = []
    if is_redis_instance_type(cluster.cluster_type):
        ret = Package.objects.filter(db_type=DBType.Redis.value, pkg_type=MediumEnum.Redis.value).values_list(
            "name", flat=True
        )
        for version in ret:
            if version_ge(version, online_redis_ver):
                versions.append(version)
    elif is_tendisplus_instance_type(cluster.cluster_type):
        ret = Package.objects.filter(db_type=DBType.Redis.value, pkg_type=MediumEnum.TendisPlus.value).values_list(
            "name", flat=True
        )
        for version in ret:
            if version_ge(version, online_redis_ver):
                versions.append(version)
    elif is_tendisssd_instance_type(cluster.cluster_type):
        versions.append(online_redis_ver)
    versions = [version.replace(".tar.gz", "") for version in versions]
    versions = [version.replace(".tgz", "") for version in versions]
    return versions


def get_major_version_by_version_name(name: str) -> str:
    """
    根据 name 返回对应主版本
    如: name=='redis-6.2.14'
    返回结果 'Redis-6'
    如: name=='predixy-1.4.0'
    返回结果 'Predixy-latest'
    """
    row = Package.objects.filter(
        db_type=DBType.Redis.value,
        pkg_type__in=(
            MediumEnum.Redis.value,
            MediumEnum.TendisPlus.value,
            MediumEnum.TendisSsd.value,
            MediumEnum.Predixy.value,
            MediumEnum.Twemproxy.value,
        ),
        name__startswith=name,
    ).first()
    if not row:
        return ""
    return row.version


def get_proxy_version_names_by_cluster_type(cluster_type: str, trimSuffix: bool = False) -> list:
    """
    根据 cluster_type 返回对应proxy详细版本
    如: cluster_type==ClusterType.TendisPredixyRedisCluster
    返回结果 ['predixy-1.4.0.tar.gz']

    trimSuffix默认为False,如果trimSuffix==True,则返回结果 ['predixy-1.4.0']
    """
    versions = []
    if is_predixy_proxy_type(cluster_type):
        ret = Package.objects.filter(db_type=DBType.Redis.value, pkg_type=MediumEnum.Predixy.value).values_list(
            "name", flat=True
        )
        versions = list(ret)
    elif is_twemproxy_proxy_type(cluster_type):
        ret = Package.objects.filter(db_type=DBType.Redis.value, pkg_type=MediumEnum.Twemproxy.value).values_list(
            "name", flat=True
        )
        versions = list(ret)
    else:
        raise Exception(_("集群类型:{} 不是一个 redis 集群类型?").format(cluster_type))

    if trimSuffix:
        versions = [version.replace(".tar.gz", "") for version in versions]
        versions = [version.replace(".tgz", "") for version in versions]
    return versions


def get_cluster_proxy_version_for_upgrade(cluster_id: int) -> list:
    """
    获取集群可升级到的proxy版本
    """
    cluster = Cluster.objects.get(id=cluster_id)
    return get_proxy_version_names_by_cluster_type(cluster.cluster_type, True)


def get_twemproxy_cluster_hash_tag(cluster_type: str, cluster_id: int) -> str:
    """
    获取twemproxy集群的hash_tag值
    如果集群类型不是twemproxy集群,则返回空字符串
    """
    if cluster_type and (not is_twemproxy_proxy_type(cluster_type)):
        return ""
    try:
        cluster = Cluster.objects.get(id=cluster_id)
        if not is_twemproxy_proxy_type(cluster.cluster_type):
            return ""
        resp = DBConfigApi.query_conf_item(
            params={
                "bk_biz_id": str(cluster.bk_biz_id),
                "level_name": LevelName.CLUSTER,
                "level_value": cluster.immute_domain,
                "level_info": {"module": str(DEFAULT_DB_MODULE_ID)},
                "conf_file": cluster.proxy_version,
                "conf_type": ConfigTypeEnum.ProxyConf,
                "namespace": cluster.cluster_type,
                "format": "map",
            }
        )
        if resp["content"]:
            return resp["content"].get("hash_tag", "")
    except Exception:
        return ""


def get_online_twemproxy_version(ip: str, port: int, bk_cloud_id: int) -> str:
    """
    连接twemproxy执行 stats 获取版本信息
    返回结果示例: 0.4.1-rc-v0.28
    """
    admin_port = port + DEFAULT_TWEMPROXY_ADMIN_PORT_EXTRA
    resp = DRSApi.twemproxy_rpc(
        {
            "addresses": [f"{ip}:{admin_port}"],
            "db_num": DEFAULT_REDIS_DBNUM,
            "password": "",
            "command": "stats",
            "bk_cloud_id": bk_cloud_id,
        }
    )
    if not resp or len(resp) == 0:
        return ""
    version_str = json.loads(resp[0]["result"])["version"]
    version_str = "twemproxy-" + version_str.replace("rc-", "")
    version_str = version_str.replace("v0.", "v")
    return version_str


def get_online_predixy_version(ip: str, port: int, bk_cloud_id: int, proxy_password: str) -> str:
    """
    连接predixy执行 info Proxy 获取版本信息
    返回结果示例: 1.4.0
    """
    resp = DRSApi.redis_rpc(
        {
            "addresses": [f"{ip}:{port}"],
            "db_num": DEFAULT_REDIS_DBNUM,
            "password": proxy_password,
            "command": "info Proxy",
            "bk_cloud_id": bk_cloud_id,
        }
    )
    if not resp or len(resp) == 0:
        return ""
    for line in resp[0]["result"].split("\n"):
        if line.startswith("Version:"):
            return "predixy-" + line.split(":")[1]
    return ""


def get_online_redis_version(ip: str, port: int, bk_cloud_id: int, redis_password: str) -> str:
    """
    连接redis 连接rediso server 获取版本信息
    返回结果示例: Redis v=6.2.5 sha=00000000:0 malloc=jemalloc-5.1.0 bits=64 build=973eacbbcafaadec
    """
    resp = DRSApi.redis_rpc(
        {
            "addresses": [f"{ip}:{port}"],
            "db_num": DEFAULT_REDIS_DBNUM,
            "password": redis_password,
            "command": "INFO SERVER",
            "bk_cloud_id": bk_cloud_id,
        }
    )
    if not resp or len(resp) == 0:
        return ""
    result = resp[0].get("result")
    version_str = re.search(r"redis_version:(.*)\r\n", result).group(1)
    if version_str.find("-TRedis-") > 0:
        version_str = version_str.replace("TRedis", "rocksdb")
        return "redis-" + version_str
    elif version_str.find("-rocksdb-") > 0:
        return "tendisplus-" + version_str
    else:
        return "redis-" + version_str


def get_cluster_proxy_version(cluster_id: int) -> list:
    """
    获取redis cluster proxy版本列表
    """
    cluster = Cluster.objects.get(id=cluster_id)
    versions = set()
    passwd_ret = PayloadHandler.redis_get_password_by_cluster_id(cluster_id)
    if is_predixy_proxy_type(cluster.cluster_type):
        for proxy in cluster.proxyinstance_set.filter(status=InstanceStatus.RUNNING):
            versions.add(
                get_online_predixy_version(
                    proxy.machine.ip, proxy.port, cluster.bk_cloud_id, passwd_ret.get("redis_proxy_password")
                )
            )
    elif is_twemproxy_proxy_type(cluster.cluster_type):
        for proxy in cluster.proxyinstance_set.filter(status=InstanceStatus.RUNNING):
            versions.add(get_online_twemproxy_version(proxy.machine.ip, proxy.port, cluster.bk_cloud_id))
    return list(versions)


def get_cluster_redis_version(cluster_id: int) -> str:
    """
    获取redis cluster redis版本
    """
    cluster = Cluster.objects.get(id=cluster_id)
    passwd_ret = PayloadHandler.redis_get_password_by_cluster_id(cluster_id)
    one_running_master = cluster.storageinstance_set.filter(
        instance_role=InstanceRole.REDIS_MASTER.value, status=InstanceStatus.RUNNING
    ).first()
    if not one_running_master:
        raise Exception(_("redis集群 {} 没有running_master??").format(cluster.immute_domain))
    return get_online_redis_version(
        one_running_master.machine.ip, one_running_master.port, cluster.bk_cloud_id, passwd_ret.get("redis_password")
    )


def get_cluster_capacity_info(cluster_id: int) -> Tuple[str, int, str, int, int]:
    """
    获取集群当前容量信息
    参数:
    - cluster_id: 集群id
    返回:
    - storage_version: 存储层版本
    - storage_spec_id: 规格id
    - storage_spec_str: 规格
    - machine_group_count: 机器组数量
    - shards_num: 分片数量
    """
    cluster = Cluster.objects.get(id=cluster_id)

    storage_machine = cluster.storageinstance_set.first().machine
    # master_insts 代表当前集群分片数
    master_insts = cluster.storageinstance_set.filter(
        instance_role=InstanceRole.REDIS_MASTER.value, status=InstanceStatus.RUNNING
    )
    # 当前master机器台数,代表当前集群机器组数
    master_machines = set()
    for storage_inst in master_insts:
        master_machines.add(storage_inst.machine.ip)
    storage_version = get_cluster_redis_version(cluster_id)
    storage_spec_id = storage_machine.spec_id
    storage_spec_str = storage_machine.spec_config["name"]
    machine_group_count = len(master_machines)
    shards_num = len(master_insts)
    return storage_version, storage_spec_id, storage_spec_str, machine_group_count, shards_num


def get_cluster_capacity_update_required_info(
    cluster_id: int, new_storage_version: str, new_spec_id: str, new_machine_group_count: int, new_shards_num: int
) -> Tuple[str, int, int, str]:
    """
    获取集群容量变更所需信息

    参数:
    - cluster_id: 集群id
    - new_storage_version: 存储版本
    - new_spec_id: 规格id
    - new_machine_group_count: 机器组数量
    - new_shards_num: 新的分片数量
    返回:
    - capacity_update_type: 容量变更类型,原地变更(keep_current_machines)、替换变更(all_machines_replace)
    - require_spec_id 真实申请机器规格id
    - require_machine_group_count  真实需要申请的自己组数
    - err_msg 错误信息
    """
    # 默认替换变更,机器全部重新申请
    capacity_update_type = RedisCapacityUpdateType.ALL_MACHINES_REPLACE.value
    require_spec_id = new_spec_id
    require_machine_group_count = new_machine_group_count
    err_msg = ""

    cluster = Cluster.objects.get(id=cluster_id)

    storage_machine = cluster.storageinstance_set.first().machine
    if storage_machine.spec_id != new_spec_id:
        # 规格变了,替换变更
        return capacity_update_type, require_spec_id, require_machine_group_count, err_msg

    # master_insts 代表当前集群分片数
    master_insts = cluster.storageinstance_set.filter(
        instance_role=InstanceRole.REDIS_MASTER.value, status=InstanceStatus.RUNNING
    )
    # 当前master机器台数,代表当前集群机器组数
    master_machines = set()
    for storage_inst in master_insts:
        master_machines.add(storage_inst.machine.ip)

    if not is_tendisplus_instance_type(cluster_type=cluster.cluster_type):
        # 不是TendisPlus集群,分片数和以前保持一致
        new_shards_num = len(master_insts)

    if new_shards_num % new_machine_group_count != 0:
        # 分片数不能被机器组数整除,说明用户填入的分片数有问题
        err_msg = _("分片数 不能被 机器组数 整除")
        require_spec_id = 0
        require_machine_group_count = 0
        return capacity_update_type, require_spec_id, require_machine_group_count, err_msg

    if len(master_insts) == new_shards_num and len(master_machines) == new_machine_group_count:
        # 集群机器规格、分片数、机器组数都没变,只是版本变了
        require_spec_id = 0
        require_machine_group_count = 0
        err_msg = _("集群机器规格、分片数、机器组数都没变,只是版本变了.请使用 版本升级 单据")
        return capacity_update_type, require_spec_id, require_machine_group_count, err_msg

    is_cluster_version_need_upgrade = False
    major_version_names = get_storage_versions_by_cluster_type(cluster.cluster_type)
    if new_storage_version in major_version_names:
        # 用户填入的是大版本号,Redis-6、Redis-5等
        # 大版本变了,替换变更
        if cluster.major_version != new_storage_version:
            is_cluster_version_need_upgrade = True
    else:
        # 用户填入的是详细版本号,redis-6.2.14、redis-5.0.11等
        # 详细版本变了,替换变更
        cluster_version = get_cluster_redis_version(cluster_id)
        if cluster_version != new_storage_version:
            is_cluster_version_need_upgrade = True

    if is_cluster_version_need_upgrade:
        if new_shards_num == len(master_insts):
            return capacity_update_type, require_spec_id, require_machine_group_count, err_msg
        else:
            err_msg = _("集群版本变更时,分片数不能变,请先使用 版本升级 单据")
            require_spec_id = 0
            require_machine_group_count = 0
            return capacity_update_type, require_spec_id, require_machine_group_count, err_msg

    # 执行到这里,说明用户填入的版本号和当前集群版本号一致,规格id也一致
    if len(master_insts) == new_shards_num and len(master_machines) == new_machine_group_count:
        # 集群规格没变、版本没变、分片数没变、机器组数没变, 无需变更
        err_msg = _("当前集群规格、版本、分片数、机器组数均已满足,无需变更")
        require_spec_id = 0
        require_machine_group_count = 0
        return capacity_update_type, require_spec_id, require_machine_group_count, err_msg

    if is_redis_cluster_protocal(cluster_type=cluster.cluster_type) and new_machine_group_count < 3:
        # redis 集群协议类型,机器组数不能小于3
        err_msg = _("redis 集群协议类型,机器组数不能小于3")
        require_spec_id = 0
        require_machine_group_count = 0
        return capacity_update_type, require_spec_id, require_machine_group_count, err_msg

    if new_shards_num == len(master_insts):
        # 无论什么集群类型,集群分片数没变,走这个逻辑
        if new_machine_group_count > len(master_machines):
            # 机器数 变多,原地变更,通过实例部分迁移方式完成
            capacity_update_type = RedisCapacityUpdateType.KEEP_CURRENT_MACHINES.value
            require_machine_group_count = new_machine_group_count - len(master_machines)
            return capacity_update_type, require_spec_id, require_machine_group_count, err_msg
        elif new_machine_group_count < len(master_machines):
            # 机器数 变少,替换变更,全部替换机器
            capacity_update_type = RedisCapacityUpdateType.ALL_MACHINES_REPLACE.value
            require_machine_group_count = new_machine_group_count
            return capacity_update_type, require_spec_id, require_machine_group_count, err_msg

    if is_tendisplus_instance_type(cluster_type=cluster.cluster_type):
        # tendisplus集群
        if new_shards_num > len(master_insts):
            # tendislus集群,分片数变多
            if new_machine_group_count <= len(master_machines):
                # 机器数不变 or 变少，报错
                require_spec_id = 0
                require_machine_group_count = 0
                err_msg = _("tendisplus集群 分片数变多,不允许机器数不变 or 变少。如果有需要,请使用 集群分片数变更 单据")
                return capacity_update_type, require_spec_id, require_machine_group_count, err_msg
            else:
                # 机器数变多
                capacity_update_type = RedisCapacityUpdateType.KEEP_CURRENT_MACHINES.value
                require_machine_group_count = new_machine_group_count - len(master_machines)
                return capacity_update_type, require_spec_id, require_machine_group_count, err_msg
        elif new_shards_num < len(master_insts):
            # tendislus集群,分片数变少
            if new_machine_group_count > len(master_machines):
                # 机器数 变多，报错
                require_spec_id = 0
                require_machine_group_count = 0
                err_msg = _("tendisplus集群 分片数变少,不允许机器数 变多。如果有需要,请使用 集群分片数变更 单据")
                return capacity_update_type, require_spec_id, require_machine_group_count, err_msg
            else:
                # 机器数不变 or 变少,不需要申请机器
                capacity_update_type = RedisCapacityUpdateType.KEEP_CURRENT_MACHINES.value
                require_machine_group_count = 0
                require_spec_id = 0
                return capacity_update_type, require_spec_id, require_machine_group_count, err_msg
