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

import random
import string
from collections import defaultdict
from itertools import chain

from django.utils.translation import gettext_lazy as _

from backend.components import DBConfigApi
from backend.components.dbconfig.constants import FormatType, LevelName
from backend.configuration.constants import DBPrivSecurityType
from backend.configuration.handlers.password import DBPasswordHandler
from backend.db_meta.enums import InstanceRole
from backend.db_meta.enums.cluster_type import ClusterType
from backend.db_meta.models import AppCache, Cluster, Spec, StorageInstanceTuple
from backend.flow.consts import DEFAULT_DB_MODULE_ID, ClusterRoleEnum, ConfigTypeEnum, RedisCapacityUpdateType
from backend.flow.utils.base.payload_handler import PayloadHandler
from backend.ticket.builders.common.base import IpSource
from backend.ticket.constants import SwitchConfirmType, TicketType
from backend.ticket.models import Ticket

# redis_cluster_apply 支持克隆申请的集群类型（均为带proxy层的架构）
REDIS_CLUSTER_APPLY_SUPPORTED_TYPES = [
    ClusterType.TendisTwemproxyRedisInstance,
    ClusterType.TwemproxyTendisSSDInstance,
    ClusterType.TendisPredixyRedisCluster,
    ClusterType.TendisPredixyTendisplusCluster,
    ClusterType.TendisPredixyTendisplusInstance,
]


def generate_custom_id():
    """生成格式: 6位数字_13位数字_6位数字"""
    part1 = "".join(random.choices(string.digits, k=6))
    part2 = "".join(random.choices(string.digits, k=13))
    part3 = "".join(random.choices(string.digits, k=6))
    return f"{part1}_{part2}_{part3}"


# 集群部署（克隆申请）
def redis_cluster_apply(request, bk_biz_id, cluster_domain, new_cluster_name, keep_source_password=False):
    """
    参照已有集群的部署参数，克隆申请一个新的redis集群
    new_cluster_name为新集群名，由调用方传入，不能与已有集群重名；机器来源固定为资源池，规格/分片数/组数/容灾级别/城市等均与原集群保持一致
    仅支持带proxy层的架构：TwemproxyRedisInstance、TwemproxyTendisSSDInstance、
    PredixyRedisCluster、PredixyTendisplusCluster、PredixyTendisplusInstance
    @param keep_source_password: 新集群的proxy密码是否与源集群保持一致，默认 False（生成新随机密码）；
                                 设置为 True 时将复用源集群的proxy密码；若源集群无proxy密码则回退到生成新随机密码
    """
    cluster_obj = Cluster.objects.get(bk_biz_id=bk_biz_id, immute_domain=cluster_domain)
    if cluster_obj.cluster_type not in REDIS_CLUSTER_APPLY_SUPPORTED_TYPES:
        return {
            "error": "集群类型{}暂不支持通过该工具克隆申请，仅支持: {}".format(
                cluster_obj.cluster_type, [t.value for t in REDIS_CLUSTER_APPLY_SUPPORTED_TYPES]
            )
        }

    if Cluster.objects.filter(
        bk_biz_id=bk_biz_id, cluster_type=cluster_obj.cluster_type, name=new_cluster_name
    ).exists():
        return {"error": "新集群名{}已存在，请更换".format(new_cluster_name)}

    proxy_ins_list = list(cluster_obj.proxyinstance_set.select_related("machine").all())
    if not proxy_ins_list:
        return {"error": "集群{}未找到proxy实例，无法获取部署参数".format(cluster_domain)}

    master_ins_list = list(
        cluster_obj.storageinstance_set.select_related("machine").filter(instance_role=InstanceRole.REDIS_MASTER.value)
    )
    if not master_ins_list:
        return {"error": "集群{}未找到master实例，无法获取部署参数".format(cluster_domain)}

    proxy_spec_id = proxy_ins_list[0].machine.spec_id
    proxy_count = len(proxy_ins_list)

    backend_spec_id = master_ins_list[0].machine.spec_id
    # 机器组数：master去重后的机器数
    master_ips = list(dict.fromkeys([ins.machine.ip for ins in master_ins_list]))
    group_num = len(master_ips)
    # 分片数：master实例总数
    shard_num = len(master_ins_list)
    if (
        cluster_obj.cluster_type
        in (
            ClusterType.TendisPredixyRedisCluster,
            ClusterType.TendisPredixyTendisplusCluster,
        )
        and shard_num < 3
    ):
        return {"error": "源集群分片数 {} < 3，无法克隆该类型集群".format(shard_num)}

    db_app_abbr = AppCache.get_app_attr(bk_biz_id, "db_app_abbr") or str(bk_biz_id)
    city_code = cluster_obj.region
    disaster_tolerance_level = cluster_obj.disaster_tolerance_level
    # proxy访问密码：若指定与源集群保持一致则复用源集群proxy密码，否则随机生成
    if keep_source_password:
        source_pwd_map = PayloadHandler.redis_get_cluster_password(cluster=cluster_obj)
        proxy_pwd = source_pwd_map.get("redis_proxy_password", "")
        if not proxy_pwd:
            # 源集群未取到proxy密码，回退到随机生成，避免单据因密码缺失无法继续
            proxy_pwd = DBPasswordHandler.get_random_password(security_type=DBPrivSecurityType.REDIS_PASSWORD)
    else:
        # 默认行为：随机生成，满足平台密码强度策略
        proxy_pwd = DBPasswordHandler.get_random_password(security_type=DBPrivSecurityType.REDIS_PASSWORD)

    # 规格详情，用于补充resource_spec的展示字段
    proxy_spec = Spec.objects.get(spec_id=proxy_spec_id)
    backend_spec = Spec.objects.get(spec_id=backend_spec_id)

    location_spec = {"city": city_code, "sub_zone_ids": []}
    ticket_param = {
        "bk_biz_id": bk_biz_id,
        "creator": request.user.username,
        "helpers": [],
        "remark": "mcp redis cluster apply(clone from {}) ticket".format(cluster_domain),
        "ticket_type": TicketType.REDIS_CLUSTER_APPLY,
        "details": {
            "bk_cloud_id": cluster_obj.bk_cloud_id,
            "cap_key": "",
            "proxy_port": 50000,
            "proxy_pwd": proxy_pwd,
            "db_app_abbr": db_app_abbr,
            "city_code": city_code,
            "disaster_tolerance_level": disaster_tolerance_level,
            "cluster_type": cluster_obj.cluster_type,
            "db_version": cluster_obj.major_version,
            "cluster_name": new_cluster_name,
            "cluster_alias": new_cluster_name,
            "ip_source": IpSource.RESOURCE_POOL.value,
            "cluster_shard_num": shard_num,
            "apply_clb": False,
            "apply_polaris": False,
            "resource_spec": {
                "proxy": {
                    "count": proxy_count,
                    "spec_id": proxy_spec_id,
                    "capacity": proxy_spec.capacity,
                    "cpu": proxy_spec.cpu,
                    "mem": proxy_spec.mem,
                    "qps": proxy_spec.qps,
                    "spec_name": proxy_spec.spec_name,
                    "storage_spec": proxy_spec.storage_spec,
                    "affinity": disaster_tolerance_level,
                    "location_spec": location_spec,
                    "spec_cluster_type": proxy_spec.spec_cluster_type,
                    "spec_machine_type": proxy_spec.spec_machine_type,
                },
                "backend_group": {
                    "affinity": disaster_tolerance_level,
                    "count": group_num,
                    "location_spec": location_spec,
                    "spec_id": backend_spec_id,
                    "spec_info": {
                        "cluster_capacity": backend_spec.capacity * group_num,
                        "cluster_shard_num": shard_num,
                        "machine_pair": group_num,
                        "qps": backend_spec.qps,
                        "spec_name": backend_spec.spec_name,
                    },
                },
            },
        },
    }
    tk = Ticket.create_ticket(**ticket_param)
    return {"bill_id": tk.pk, "bill_url": tk.url}


# 主从克隆申请：参照已有主从，克隆申请一个新的redis主从
REDIS_INS_APPLY_SUPPORTED_TYPES = [ClusterType.TendisRedisInstance]


def _get_redis_databases(cluster: Cluster) -> int:
    """读取源 redis 主从集群配置里的 databases（db 数量），读不到时回退到默认 16"""
    try:
        resp = DBConfigApi.query_conf_item(
            params={
                "bk_biz_id": str(cluster.bk_biz_id),
                "level_name": LevelName.CLUSTER.value,
                "level_value": cluster.immute_domain,
                "level_info": {"module": str(DEFAULT_DB_MODULE_ID)},
                "conf_file": cluster.major_version,
                "conf_type": ConfigTypeEnum.DBConf.value,
                "namespace": cluster.cluster_type,
                "format": FormatType.MAP.value,
            }
        )
        return int(resp.get("content", {}).get("databases", 16))
    except Exception:  # noqa: BLE001
        return 16


def redis_ins_apply(
    request,
    bk_biz_id,
    cluster_domain,
    new_cluster_name,
    spec_id=None,
    keep_source_password=False,
    master_ip=None,
):
    """
    参照已有主从，克隆申请一个新的redis主从（TendisRedisInstance, REDIS_INS_APPLY）

    新集群的单据参数（db_version/port/容灾级别/城市/db数量）与克隆目标实例保持一致。
    @param spec_id: 全新机器部署（资源池）时使用的机器规格id；当传入 master_ip 走追加部署模式时本参数忽略
    @param keep_source_password: 新集群的redis密码是否与源集群保持一致，默认 False（生成新随机密码）；
                                 设置为 True 时将复用源集群的redis密码；若源集群无redis密码则回退到生成新随机密码
    @param master_ip: 可选，cluster_domain集群下某个已有master的IP。传入时走"追加部署"（append_apply），
                      在该master及其对应slave所在的主机对上追加部署新的redis主从实例，不占用新机器；
                      不传时默认使用资源池全新机器部署
    """
    cluster_obj = Cluster.objects.get(bk_biz_id=bk_biz_id, immute_domain=cluster_domain)
    if cluster_obj.cluster_type not in REDIS_INS_APPLY_SUPPORTED_TYPES:
        return {
            "error": "集群类型{}暂不支持通过该工具克隆申请主从，仅支持: {}".format(
                cluster_obj.cluster_type, [t.value for t in REDIS_INS_APPLY_SUPPORTED_TYPES]
            )
        }

    if Cluster.objects.filter(
        bk_biz_id=bk_biz_id, cluster_type=cluster_obj.cluster_type, name=new_cluster_name
    ).exists():
        return {"error": "新集群名{}已存在，请更换".format(new_cluster_name)}

    master_ins_list = list(
        cluster_obj.storageinstance_set.select_related("machine").filter(instance_role=InstanceRole.REDIS_MASTER.value)
    )
    if not master_ins_list:
        return {"error": "集群{}未找到master实例，无法获取部署参数".format(cluster_domain)}

    db_app_abbr = AppCache.get_app_attr(bk_biz_id, "db_app_abbr") or str(bk_biz_id)
    city_code = cluster_obj.region
    disaster_tolerance_level = cluster_obj.disaster_tolerance_level

    # redis访问密码：若指定与源集群保持一致则复用源集群redis密码，否则随机生成
    if keep_source_password:
        source_pwd_map = PayloadHandler.redis_get_cluster_password(cluster=cluster_obj)
        redis_pwd = source_pwd_map.get("redis_password", "")
        if not redis_pwd:
            redis_pwd = DBPasswordHandler.get_random_password(security_type=DBPrivSecurityType.REDIS_PASSWORD)
    else:
        redis_pwd = DBPasswordHandler.get_random_password(security_type=DBPrivSecurityType.REDIS_PASSWORD)

    # 克隆目标实例的 db 数量，保持与源集群一致
    databases = _get_redis_databases(cluster_obj)

    # 新集群的单据参数与源集群保持一致
    details = {
        "bk_cloud_id": cluster_obj.bk_cloud_id,
        "city_code": city_code,
        "cluster_type": cluster_obj.cluster_type,
        "db_app_abbr": db_app_abbr,
        "disaster_tolerance_level": disaster_tolerance_level,
        "redis_pwd": redis_pwd,
        "append_apply": False,
    }

    if master_ip:
        # 追加部署模式：master_ip 必须是 cluster_domain 现有的某个master，
        # 在其与对应slave所在的主机对上追加部署新的redis主从实例（不占用新机器）
        master_ip_map = {ins.machine.ip: ins for ins in master_ins_list}
        master_ins = master_ip_map.get(master_ip)
        if not master_ins:
            return {
                "error": "master_ip {} 不属于集群{}的master实例，请从以下master中选择一个: {}".format(
                    master_ip, cluster_domain, list(master_ip_map.keys())
                )
            }
        slave_tuple = (
            StorageInstanceTuple.objects.select_related("receiver__machine").filter(ejector=master_ins).first()
        )
        if not slave_tuple:
            return {"error": "未找到master {} 对应的slave实例，无法追加部署".format(master_ip)}
        slave_machine = slave_tuple.receiver.machine
        master_machine = master_ins.machine

        backend_group = {
            "master": {
                "ip": master_machine.ip,
                "bk_cloud_id": master_machine.bk_cloud_id,
                "bk_host_id": master_machine.bk_host_id,
            },
            "slave": {
                "ip": slave_machine.ip,
                "bk_cloud_id": slave_machine.bk_cloud_id,
                "bk_host_id": slave_machine.bk_host_id,
            },
        }
        details.update(
            ip_source=IpSource.MANUAL_INPUT.value,
            append_apply=True,
            infos=[{"cluster_name": new_cluster_name, "databases": databases, "backend_group": backend_group}],
        )
    else:
        # 默认：资源池全新机器部署，port/db_version 仅资源池模式需要（追加部署由master实例反推，无需指定）
        if not spec_id:
            return {"error": "全新机器部署模式需要传入 spec_id（机器规格id）"}
        backend_spec = Spec.objects.get(spec_id=spec_id)
        details.update(
            ip_source=IpSource.RESOURCE_POOL.value,
            port=cluster_obj.access_port,
            db_version=cluster_obj.major_version,
            infos=[{"cluster_name": new_cluster_name, "databases": databases}],
            resource_spec={
                "backend_group": {
                    "count": 1,
                    "spec_id": spec_id,
                    "cpu": backend_spec.cpu,
                    "mem": backend_spec.mem,
                    "qps": backend_spec.qps,
                    "capacity": backend_spec.capacity,
                    "spec_name": backend_spec.spec_name,
                    "storage_spec": backend_spec.storage_spec,
                    "affinity": disaster_tolerance_level,
                    "labels": [],
                    "label_names": [],
                    "location_spec": {"city": city_code, "sub_zone_ids": []},
                }
            },
        )

    ticket_param = {
        "bk_biz_id": bk_biz_id,
        "creator": request.user.username,
        "helpers": [],
        "remark": "mcp redis ins apply(clone from {}) ticket".format(cluster_domain),
        "ticket_type": TicketType.REDIS_INS_APPLY,
        "details": details,
    }
    tk = Ticket.create_ticket(**ticket_param)
    return {"bill_id": tk.pk, "bill_url": tk.url}


# 集群扩容
def redis_general_scale_down(request, bk_biz_id, cluster_domain, target_group_num):
    cluster_obj = Cluster.objects.get(bk_biz_id=bk_biz_id, immute_domain=cluster_domain)
    if cluster_obj.cluster_type in [ClusterType.TendisPredixyTendisplusCluster, ClusterType.TendisPredixyRedisCluster]:
        return predixy_tendisplus_rediscluster_scale_down(request, bk_biz_id, cluster_domain, target_group_num)
    elif cluster_obj.cluster_type in [
        ClusterType.TendisTwemproxyRedisInstance,
        ClusterType.TwemproxyTendisSSDInstance,
    ]:
        return twemproxy_ssd_cache_scale_down(request, bk_biz_id, cluster_domain, target_group_num)
    else:
        return {"error": "redis_cluster_scale_down tools not support {}".format(cluster_obj.cluster_type)}


def predixy_tendisplus_rediscluster_scale_down(request, bk_biz_id, cluster_domain, target_group_num):
    """
    predixy集群slot迁移扩缩容。 单机分片数不变。
    """
    if target_group_num < 3:
        return {"error": "redis_cluster_scale_down target_group_num must >= 3"}
    # tendisplus分片扩缩容， 对应单据：集群分片变更（Slot迁移）
    cluster_obj = Cluster.objects.get(bk_biz_id=bk_biz_id, immute_domain=cluster_domain)
    storageinstance_set = cluster_obj.storageinstance_set.filter(instance_role=InstanceRole.REDIS_MASTER.value).all()

    master_ips = []
    spec_id = 0
    for st in storageinstance_set:
        ip = st.machine.ip
        if ip not in master_ips:
            master_ips.append(ip)
            spec_id = st.machine.spec_id
    spec_mem = int(Spec.objects.get(spec_id=spec_id).get_spec_info().get("mem", {}).get("min", 0))

    current_group_num = len(master_ips)
    current_shard_num = len(storageinstance_set)
    target_shard_num = target_group_num * current_shard_num / current_group_num

    current_capacity = current_group_num * spec_mem
    future_capacity = target_group_num * spec_mem
    infos = []
    # 扩容
    if target_group_num > current_group_num:
        ticket_type = TicketType.REDIS_SHARD_ADD
        # 扩容组数
        count = target_group_num - current_group_num
        #
        infos = [
            {
                "bk_cloud_id": cluster_obj.bk_cloud_id,
                "capacity": current_capacity,
                "cluster_id": cluster_obj.id,
                "db_version": cluster_obj.major_version,
                "future_capacity": future_capacity,
                "group_num": target_group_num,
                "resource_spec": {
                    "backend_group": {"count": count, "label_names": [], "labels": [], "spec_id": spec_id}
                },
                "row_key": generate_custom_id(),
                "shard_num": target_shard_num,
                "update_mode": RedisCapacityUpdateType.SLOT_MIGRATE_UP,
            }
        ]
    # 缩容
    else:
        ticket_type = TicketType.REDIS_SHARD_REDUCE
        infos = [
            {
                "bk_cloud_id": cluster_obj.bk_cloud_id,
                "capacity": current_capacity,
                "cluster_id": cluster_obj.id,
                "current_group_num": current_group_num,
                "db_version": cluster_obj.major_version,
                "future_capacity": future_capacity,
                "group_num": target_group_num,
                "row_key": generate_custom_id(),
                "shard_num": target_shard_num,
                "spec_id": spec_id,
                "update_mode": RedisCapacityUpdateType.SLOT_MIGRATE_DOWN,
            }
        ]

    ticket_param = {
        "bk_biz_id": bk_biz_id,
        "creator": request.user.username,
        "helpers": [],
        "remark": "mcp {} scale ticket".format(cluster_obj.cluster_type),
        "ticket_type": ticket_type,
        "details": {
            # 扩容
            "infos": infos,
            "ip_source": IpSource.RESOURCE_POOL.value,
        },
    }
    tk = Ticket.create_ticket(**ticket_param)
    return {"bill_id": tk.pk, "bill_url": tk.url}


def twemproxy_ssd_cache_scale_down(request, bk_biz_id, cluster_domain, target_group_num):
    """
    twemproxy集群容量变更。 总分片数不变
    """
    cluster_obj = Cluster.objects.get(bk_biz_id=bk_biz_id, immute_domain=cluster_domain)
    master_ins = cluster_obj.storageinstance_set.filter(instance_role=InstanceRole.REDIS_MASTER.value).all()

    master_ips = []
    spec_id_statistics = defaultdict(int)
    target_spec_id = ""
    max_spec_id_count = 0
    backend_hosts = []
    for ins in master_ins:
        # 整个集群里的spec_id可能不一样？选用数量最多的那个
        spec_id = ins.machine.spec_id
        spec_id_statistics[spec_id] += 1
        if spec_id_statistics[spec_id] > max_spec_id_count:
            target_spec_id = spec_id

        if ins.machine.ip not in master_ips:
            master_ips.append(ins.machine.ip)
            backend_hosts.append(
                {
                    "ip": ins.machine.ip,
                    "bk_biz_id": bk_biz_id,
                    "bk_host_id": ins.machine.bk_host_id,
                    "bk_cloud_id": cluster_obj.bk_cloud_id,
                }
            )

            slave = StorageInstanceTuple.objects.get(ejector=ins).receiver
            backend_hosts.append(
                {
                    "ip": slave.machine.ip,
                    "bk_biz_id": bk_biz_id,
                    "bk_host_id": slave.machine.bk_host_id,
                    "bk_cloud_id": cluster_obj.bk_cloud_id,
                }
            )

    current_group_num = len(master_ips)
    shard_num = len(master_ins)

    # 如果是扩容,不需要替换机器
    if target_group_num > current_group_num:
        update_mode = RedisCapacityUpdateType.KEEP_CURRENT_MACHINES
        need_apply_machine_group_count = target_group_num - len(master_ips)
        # 扩容置空
        backend_hosts = []
    # 如果是缩容，需要将当前机器下架
    else:
        update_mode = RedisCapacityUpdateType.ALL_MACHINES_REPLACE
        need_apply_machine_group_count = target_group_num

    spec_info = Spec.objects.get(spec_id=target_spec_id)
    spec_mem = int(spec_info.get_spec_info().get("mem", {}).get("min", 0))
    current_capacity = current_group_num * spec_mem
    future_capacity = target_group_num * spec_mem

    ticket_param = {
        "bk_biz_id": bk_biz_id,
        "creator": request.user.username,
        "helpers": [],
        "remark": "mcp {} scale ticket".format(cluster_obj.cluster_type),
        "ticket_type": TicketType.REDIS_SCALE_UPDOWN,
        "details": {
            "infos": [
                {
                    "bk_cloud_id": cluster_obj.bk_cloud_id,
                    "capacity": current_capacity,
                    "cluster_id": cluster_obj.id,
                    "db_version": cluster_obj.major_version,
                    "display_info": {
                        # "cluster_capacity": 14,
                        "cluster_shard_num": shard_num,
                        "cluster_spec": spec_info.to_dict(),
                        # "cluster_stats": {
                        #     "used": 68100520,
                        #     "total": 15334772736,
                        #     "in_use": 0.44
                        # },
                        "machine_pair_cnt": current_group_num,
                    },
                    "future_capacity": future_capacity,
                    "group_num": target_group_num,
                    "old_nodes": {"backend_hosts": backend_hosts},
                    "online_switch_type": SwitchConfirmType.USER_CONFIRM,
                    "resource_spec": {
                        "backend_group": {
                            "affinity": cluster_obj.disaster_tolerance_level,
                            "count": need_apply_machine_group_count,
                            "label_names": [],
                            "labels": [],
                            "spec_id": target_spec_id,
                        }
                    },
                    "shard_num": shard_num,
                    "update_mode": update_mode,
                }
            ],
            "ip_source": IpSource.RESOURCE_POOL.value,
        },
    }
    tk = Ticket.create_ticket(**ticket_param)
    return {"bill_id": tk.pk, "bill_url": tk.url}


def redis_cluster_cutoff(request, bk_biz_id, cluster_domain, cutoff_ips):
    cluster_obj = Cluster.objects.get(bk_biz_id=bk_biz_id, immute_domain=cluster_domain)
    cutoff_role_list = []
    spec_info_list = []
    count = len(cutoff_ips)
    resource_spec = {}
    spec_id = ""
    # 校验
    cutoff_ip = cutoff_ips[0]
    if cluster_obj.proxyinstance_set.filter(machine__ip=cutoff_ip):
        cutoff_role = "proxy"
        for ip in cutoff_ips:
            ins = cluster_obj.proxyinstance_set.filter(machine__ip=ip).first()
            if not ins:
                return {"error": "{} 与 {}不是相同角色".format(ip, cutoff_ip)}
            cutoff_role_list.append({"bk_host_id": ins.machine.bk_host_id, "ip": ip, "spec_id": ins.machine.spec_id})
            spec_info = Spec.objects.get(spec_id=ins.machine.spec_id).get_spec_info()
            spec_info["count"] = cluster_obj.proxyinstance_set.count()
            spec_info_list.append({"bk_host_id": ins.machine.bk_host_id, "ip": ip, "spec": spec_info})
            spec_id = ins.machine.spec_id
        resource_spec = {"new_proxy": {"count": count, "label_names": [], "labels": [], "spec_id": spec_id}}
    elif cluster_obj.storageinstance_set.filter(instance_role=InstanceRole.REDIS_MASTER.value).filter(
        machine__ip=cutoff_ip
    ):
        cutoff_role = "redis_master"
        for ip in cutoff_ips:
            ins = (
                cluster_obj.storageinstance_set.filter(instance_role=InstanceRole.REDIS_MASTER.value)
                .filter(machine__ip=ip)
                .first()
            )
            if not ins:
                return {"error": "{} 与 {}不是相同角色".format(ip, cutoff_ip)}
            cutoff_role_list.append({"bk_host_id": ins.machine.bk_host_id, "ip": ip, "spec_id": ins.machine.spec_id})
            spec_info = Spec.objects.get(spec_id=ins.machine.spec_id).get_spec_info()
            # 这个count应该没什么用,先直接填充，避免因为缺少这个东西报错
            spec_info["count"] = count
            spec_info_list.append({"bk_host_id": ins.machine.bk_host_id, "ip": ip, "spec": spec_info})
            # 补充slave
            slave = StorageInstanceTuple.objects.get(ejector=ins).receiver
            spec_info = Spec.objects.get(spec_id=slave.machine.spec_id).get_spec_info()
            spec_info["count"] = count
            spec_info_list.append({"bk_host_id": slave.machine.bk_host_id, "ip": slave.machine.ip, "spec": spec_info})
            spec_id = ins.machine.spec_id
        resource_spec = {"backend_group": {"count": count, "label_names": [], "labels": [], "spec_id": spec_id}}
    elif cluster_obj.storageinstance_set.filter(instance_role=InstanceRole.REDIS_SLAVE.value).filter(
        machine__ip=cutoff_ip
    ):
        cutoff_role = "redis_slave"
        resource_spec_map = defaultdict(dict)
        for ip in cutoff_ips:
            ins = (
                cluster_obj.storageinstance_set.filter(instance_role=InstanceRole.REDIS_SLAVE.value)
                .filter(machine__ip=ip)
                .first()
            )
            if not ins:
                return {"error": "{} 与 {}不是相同角色".format(ip, cutoff_ip)}
            cutoff_role_list.append({"bk_host_id": ins.machine.bk_host_id, "ip": ip, "spec_id": ins.machine.spec_id})
            spec_info = Spec.objects.get(spec_id=ins.machine.spec_id).get_spec_info()
            spec_info["count"] = count
            spec_info_list.append({"bk_host_id": ins.machine.bk_host_id, "ip": ip, "spec": spec_info})
            resource_spec_map[f"redis_slave_{ip}"] = {
                "count": 1,
                "label_names": [],
                "labels": [],
                "spec_id": ins.machine.spec_id,
            }
        resource_spec = dict(resource_spec_map)
    else:
        return {"error": "{} 不属于集群 {}".format(cutoff_ip, cluster_obj.immute_domain)}
    ticket_param = {
        "bk_biz_id": bk_biz_id,
        "creator": request.user.username,
        "helpers": [],
        "remark": "mcp {}-{} cutoff".format(cutoff_role, cutoff_ips),
        "ticket_type": TicketType.REDIS_CLUSTER_CUTOFF,
        "details": {
            "infos": [
                {
                    "bk_cloud_id": cluster_obj.bk_cloud_id,
                    "cluster_ids": [cluster_obj.id],
                    "switch_role": cutoff_role,
                    cutoff_role: cutoff_role_list,
                    # 页面展示
                    "old_nodes": {cutoff_role: spec_info_list},
                    "resource_spec": resource_spec,
                }
            ],
            "ip_source": IpSource.RESOURCE_POOL.value,
        },
    }
    tk = Ticket.create_ticket(**ticket_param)
    return {"bill_id": tk.pk, "bill_url": tk.url}


def redis_proxy_reduce(request, bk_biz_id, cluster_domain, proxy_change_count):
    cluster_obj = Cluster.objects.get(bk_biz_id=bk_biz_id, immute_domain=cluster_domain)
    cluster_id = cluster_obj.id
    cluster_proxy_count = cluster_obj.proxyinstance_set.count()
    count = cluster_proxy_count - proxy_change_count
    ticket_param = {
        "bk_biz_id": bk_biz_id,
        "creator": request.user.username,
        "helpers": [],
        "remark": "mcp proxy reduce ticket",
        "ticket_type": TicketType.REDIS_PROXY_SCALE_DOWN,
        "details": {
            "infos": [{"cluster_id": cluster_id, "online_switch_type": "user_confirm", "target_proxy_count": count}],
        },
    }
    tk = Ticket.create_ticket(**ticket_param)
    return {"bill_id": tk.pk, "bill_url": tk.url}


def redis_proxy_reduce_by_ip(request, bk_biz_id, cluster_domain, reduce_ips):
    cluster_obj = Cluster.objects.get(bk_biz_id=bk_biz_id, immute_domain=cluster_domain)
    cluster_id = cluster_obj.id
    proxys = cluster_obj.proxyinstance_set.all()
    count = len(proxys) - len(reduce_ips)
    remark = r"mcp proxy {} reduce ticket".format(reduce_ips)
    if count < 2:
        return {"error": _("缩容后集群proxy小于2，不满足亲和度要求")}
    # 获取主机相关的数据
    proxy_reduced_hosts = []
    for proxy in proxys:
        machine = proxy.machine
        if machine.ip in reduce_ips:
            proxy_reduced_hosts.append(
                {
                    "ip": machine.ip,
                    "bk_biz_id": machine.bk_biz_id,
                    "bk_host_id": machine.bk_host_id,
                    "bk_cloud_id": machine.bk_cloud_id,
                }
            )
    # 检查是否存在传入的IP与集群对应不上的
    if len(reduce_ips) != len(proxy_reduced_hosts):
        for proxy in proxy_reduced_hosts:
            reduce_ips.remove(proxy["ip"])
        return {"error": _("存在不属于集群{}的proxy{}".format(cluster_domain, reduce_ips))}
    ticket_param = {
        "bk_biz_id": bk_biz_id,
        "creator": request.user.username,
        "helpers": [],
        "remark": remark,
        "ticket_type": TicketType.REDIS_PROXY_SCALE_DOWN,
        "details": {
            "infos": [
                {
                    "old_nodes": {"proxy_reduced_hosts": proxy_reduced_hosts},
                    "cluster_id": cluster_id,
                    "online_switch_type": "user_confirm",
                    "target_proxy_count": count,
                }
            ],
        },
    }
    tk = Ticket.create_ticket(**ticket_param)
    return {"bill_id": tk.pk, "bill_url": tk.url}


def redis_proxy_increase(request, bk_biz_id, cluster_domain, proxy_change_count):
    cluster_obj = Cluster.objects.get(bk_biz_id=bk_biz_id, immute_domain=cluster_domain)
    cluster_id = cluster_obj.id
    proxys = cluster_obj.proxyinstance_set.all()
    # 获取spec_id
    spec_id = cluster_obj.proxyinstance_set.first().machine.spec_id
    ticket_param = {
        "bk_biz_id": bk_biz_id,
        "creator": request.user.username,
        "helpers": [],
        "remark": "mcp proxy increase ticket",
        "ticket_type": TicketType.REDIS_PROXY_SCALE_UP,
        "details": {
            "infos": [
                {
                    "bk_cloud_id": cluster_obj.bk_cloud_id,
                    "cluster_id": cluster_id,
                    "resource_spec": {"proxy": {"count": proxy_change_count, "spec_id": spec_id}},
                    # 用于前端展示的参数
                    "current_proxy_num": len(proxys),
                    "target_proxy_count": len(proxys) + proxy_change_count,
                }
            ],
            "ip_source": IpSource.RESOURCE_POOL.value,
            "shrink_type": "QUANTITY",
        },
    }

    tk = Ticket.create_ticket(**ticket_param)
    return {"bill_id": tk.pk, "bill_url": tk.url}


def redis_full_backup(request, bk_biz_id, cluster_domain, backup_type, target):
    cluster_obj = Cluster.objects.get(bk_biz_id=bk_biz_id, immute_domain=cluster_domain)
    cluster_id = cluster_obj.id
    ticket_param = {
        "bk_biz_id": bk_biz_id,
        "ticket_type": TicketType.REDIS_BACKUP,
        "creator": request.user.username,
        "helpers": [],
        "remark": "mcp backup ticket",
        "details": {
            "rules": [
                {"backup_type": backup_type, "cluster_id": cluster_id, "domain": cluster_domain, "target": target}
            ]
        },
    }
    tk = Ticket.create_ticket(**ticket_param)
    return {"bill_id": tk.pk, "bill_url": tk.url}


def redis_flush_db(request, bk_biz_id, cluster_domain, is_force, is_backup):
    cluster_obj = Cluster.objects.get(bk_biz_id=bk_biz_id, immute_domain=cluster_domain)
    cluster_id = cluster_obj.id
    cluster_type = cluster_obj.cluster_type
    ticket_param = {
        "bk_biz_id": bk_biz_id,
        "ticket_type": TicketType.REDIS_PURGE,
        "creator": request.user.username,
        "helpers": [],
        "remark": "mcp redis flushdb ticket",
        "details": {
            "rules": [
                {
                    "force": is_force,
                    "backup": is_backup,
                    "domain": cluster_domain,
                    "db_list": [],
                    "flushall": True,
                    "cluster_id": cluster_id,
                    "cluster_type": cluster_type,
                }
            ]
        },
    }

    tk = Ticket.create_ticket(**ticket_param)
    return {"bill_id": tk.pk, "bill_url": tk.url}


def redis_extract_key(request, bk_biz_id, cluster_domain, white_regex, black_regex):
    cluster_obj = Cluster.objects.get(bk_biz_id=bk_biz_id, immute_domain=cluster_domain)
    cluster_id = cluster_obj.id
    ticket_param = {
        "bk_biz_id": bk_biz_id,
        "ticket_type": TicketType.REDIS_KEYS_EXTRACT,
        "creator": request.user.username,
        "helpers": [],
        "remark": "mcp redis extract key ticket",
        "details": {
            "rules": [
                {
                    "domain": cluster_domain,
                    "cluster_id": cluster_id,
                    "black_regex": black_regex,
                    "white_regex": white_regex,
                }
            ]
        },
    }

    tk = Ticket.create_ticket(**ticket_param)
    return {"bill_id": tk.pk, "bill_url": tk.url}


def redis_delete_key_by_regex(request, bk_biz_id, cluster_domain, white_regex, black_regex, delete_rate):
    cluster_obj = Cluster.objects.get(bk_biz_id=bk_biz_id, immute_domain=cluster_domain)
    cluster_id = cluster_obj.id
    ticket_param = {
        "bk_biz_id": bk_biz_id,
        "ticket_type": TicketType.REDIS_KEYS_DELETE,
        "creator": request.user.username,
        "helpers": [],
        "remark": "mcp redis delete key ticket",
        "details": {
            "delete_type": "regex",
            "rules": [
                {
                    "domain": cluster_domain,
                    "delete_rate": delete_rate,
                    "cluster_id": cluster_id,
                    "black_regex": black_regex,
                    "white_regex": white_regex,
                }
            ],
        },
    }

    tk = Ticket.create_ticket(**ticket_param)
    return {"bill_id": tk.pk, "bill_url": tk.url}


def redis_reinstall_dbmon(request, bk_biz_id, cluster_domain):
    cluster_obj = Cluster.objects.get(bk_biz_id=bk_biz_id, immute_domain=cluster_domain)
    cluster_id = cluster_obj.id
    ticket_param = {
        "bk_biz_id": bk_biz_id,
        "ticket_type": TicketType.REDIS_CLUSTER_REINSTALL_DBMON,
        "creator": request.user.username,
        "helpers": [],
        "remark": "mcp redis reinstall dbmon ticket",
        "details": {
            "is_stop": False,
            "bk_cloud_id": cluster_obj.bk_cloud_id,
            "restart_exporter": True,
            "cluster_ids": [cluster_id],
        },
    }

    tk = Ticket.create_ticket(**ticket_param)
    return {"bill_id": tk.pk, "bill_url": tk.url}


def redis_version_update_online(request, bk_biz_id, cluster_domain, node_type, target_version):
    cluster_obj = Cluster.objects.get(bk_biz_id=bk_biz_id, immute_domain=cluster_domain)
    # 为了前端展示获取
    current_versions = set()
    ips = set()
    if node_type == ClusterRoleEnum.BACKEND:
        update_instance = cluster_obj.storageinstance_set.all()
    else:
        update_instance = cluster_obj.proxyinstance_set.all()

    for ins in update_instance:
        current_versions.add(ins.version)
        ips.add(ins.machine.ip)
    current_versions = list(current_versions)

    target_versions = [{"ip": ip, "version": target_version} for ip in ips]

    ticket_param = {
        "bk_biz_id": bk_biz_id,
        "creator": request.user.username,
        "helpers": [],
        "remark": "mcp redis version update ticket",
        "ticket_type": TicketType.REDIS_VERSION_UPDATE_ONLINE,
        "details": {
            "infos": [
                {
                    "cluster_id": cluster_obj.id,
                    "current_versions": current_versions,
                    "node_type": node_type,
                    "slave_current_versions": [],
                    "target_versions": target_versions,
                }
            ],
            "update_type": "cluster",
        },
    }

    tk = Ticket.create_ticket(**ticket_param)
    return {"bill_id": tk.pk, "bill_url": tk.url}


def redis_load_modules(request, bk_biz_id, cluster_domain, modules):
    cluster_obj = Cluster.objects.get(bk_biz_id=bk_biz_id, immute_domain=cluster_domain)
    ticket_param = {
        "bk_biz_id": bk_biz_id,
        "ticket_type": TicketType.REDIS_CLUSTER_LOAD_MODULES,
        "creator": request.user.username,
        "helpers": [],
        "remark": "mcp redis load modules ticket",
        "details": {
            "infos": [
                {"cluster_id": cluster_obj.id, "db_version": cluster_obj.major_version, "load_modules": modules}
            ],
            "bk_cloud_id": cluster_obj.bk_cloud_id,
        },
    }

    tk = Ticket.create_ticket(**ticket_param)
    return {"bill_id": tk.pk, "bill_url": tk.url}


def redis_hotkey_analysis(request, bk_biz_id, cluster_domain, analysis_time, ins):
    cluster_obj = Cluster.objects.get(bk_biz_id=bk_biz_id, immute_domain=cluster_domain)

    # 检查ins是否都属于这个集群
    errmsg = []
    cluster_ins = [
        "{}:{}".format(e.machine.ip, e.port)
        for e in chain(cluster_obj.storageinstance_set.all(), cluster_obj.proxyinstance_set.all())
    ]
    errmsg.extend(f"{i}不属于集群{cluster_domain}\n" for i in ins if i not in cluster_ins)
    if len(errmsg) != 0:
        return {"error": str(errmsg)}

    # 如果传参为空，则为所有proxy
    if len(ins) == 0:
        ins = ["{}:{}".format(e.machine.ip, e.port) for e in cluster_obj.proxyinstance_set.all()]

    ticket_param = {
        "bk_biz_id": bk_biz_id,
        "creator": request.user.username,
        "helpers": [],
        "remark": "mcp redis analysis hot key ticket",
        "ticket_type": TicketType.REDIS_HOT_KEY_ANALYSIS,
        "details": {
            "analysis_time": analysis_time,
            "bk_cloud_id": cluster_obj.bk_cloud_id,
            "infos": [
                {
                    "cluster_id": cluster_obj.id,
                    "cluster_type": ClusterType.TendisTwemproxyRedisInstance,
                    "immute_domain": cluster_domain,
                    "ins": ins,
                    # "record_id"
                }
            ],
        },
    }

    tk = Ticket.create_ticket(**ticket_param)
    return {"bill_id": tk.pk, "bill_url": tk.url}


def redis_memory_analysis(request, bk_biz_id, cluster_domain, ins):
    cluster_obj = Cluster.objects.get(bk_biz_id=bk_biz_id, immute_domain=cluster_domain)

    # 检查ins是否都属于这个集群
    errmsg = []
    cluster_ins = [
        "{}:{}".format(e.machine.ip, e.port)
        for e in chain(cluster_obj.storageinstance_set.all(), cluster_obj.proxyinstance_set.all())
    ]
    errmsg.extend(f"{i}不属于集群{cluster_domain}\n" for i in ins if i not in cluster_ins)
    if len(errmsg) != 0:
        return {"error": str(errmsg)}

    ticket_param = {
        "bk_biz_id": bk_biz_id,
        "creator": request.user.username,
        "helpers": [],
        "remark": "mcp redis memory analysis ticket",
        "ticket_type": TicketType.REDIS_KEYSTAT,
        "details": {
            "bk_cloud_id": cluster_obj.bk_cloud_id,
            "analysis_time": 0,
            "infos": [
                {
                    "ins": [{"addr": n} for n in ins],
                    "delimiter": "#@_-",
                    "cluster_id": cluster_obj.id,
                    "cluster_type": cluster_obj.cluster_type,
                    "immute_domain": cluster_obj.immute_domain,
                    "check_last_visit": True,
                }
            ],
        },
    }

    tk = Ticket.create_ticket(**ticket_param)
    return {"bill_id": tk.pk, "bill_url": tk.url}


def redis_master_slave_switch(request, bk_biz_id, cluster_domain, master_ips):
    """Redis集群主从切换（高危操作）"""
    cluster_obj = Cluster.objects.get(bk_biz_id=bk_biz_id, immute_domain=cluster_domain)

    # 去重，避免重复 IP 重复提单
    unique_master_ips = list(dict.fromkeys(master_ips))

    # 一次性批量查询集群下所有指定 master IP 对应的主从实例对，避免 N+1 查询
    slave_tuples = StorageInstanceTuple.objects.select_related("ejector__machine", "receiver__machine").filter(
        ejector__cluster=cluster_obj,
        ejector__instance_role=InstanceRole.REDIS_MASTER.value,
        ejector__machine__ip__in=unique_master_ips,
    )

    # 构建 master_ip -> slave_ip 映射
    master_slave_map = {tuple_obj.ejector.machine.ip: tuple_obj.receiver.machine.ip for tuple_obj in slave_tuples}

    # 一次性校验所有缺失的 IP，提供更友好的错误信息
    missing_ips = [ip for ip in unique_master_ips if ip not in master_slave_map]
    if missing_ips:
        raise ValueError(f"集群 {cluster_domain} 中无法找到以下 master IP 对应的主从关系: {missing_ips}")

    # 构建主从切换信息
    switch_infos = [
        {"redis_master": master_ip, "redis_slave": master_slave_map[master_ip]} for master_ip in unique_master_ips
    ]

    ticket_param = {
        "bk_biz_id": bk_biz_id,
        "creator": request.user.username,
        "helpers": [],
        "remark": "mcp redis master slave switch ticket (高危操作)",
        "ticket_type": TicketType.REDIS_MASTER_SLAVE_SWITCH,
        "details": {
            "infos": [
                {
                    "cluster_ids": [cluster_obj.id],
                    "pairs": switch_infos,
                    "online_switch_type": "user_confirm",
                }
            ],
        },
    }

    tk = Ticket.create_ticket(**ticket_param)
    return {"bill_id": tk.pk, "bill_url": tk.url}
