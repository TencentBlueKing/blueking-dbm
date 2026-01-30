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
from typing import Dict

from django.utils.crypto import get_random_string

from backend.configuration.constants import DBPrivSecurityType
from backend.configuration.handlers.password import DBPasswordHandler
from backend.db_meta.enums import InstanceRole
from backend.db_meta.models import Cluster, Spec
from backend.ticket.builders.common.base import IpSource
from backend.ticket.constants import TicketType
from backend.ticket.models import Ticket


def submit_kafka_scale_up_bill(
    bk_biz_id: int,
    cluster_domain: str,
    ip_source: str,
    nodes: Dict = None,
    resource_spec: Dict = None,
    creator: str = "mcp_user",
) -> Dict:
    """
    提交Kafka集群扩容单据

    Args:
        bk_biz_id: 业务ID
        cluster_domain: 集群域名
        ip_source: 主机来源 (resource_pool 或 manual_input)
        nodes: 节点列表，当ip_source为manual_input时使用
        resource_spec: 资源池规格，当ip_source为resource_pool时使用
        creator: 创建者用户名

    Returns:
        包含单据ID和单据URL的字典
    """
    cluster_obj = Cluster.objects.get(bk_biz_id=bk_biz_id, immute_domain=cluster_domain)
    cluster_id = cluster_obj.id

    ext_info = None

    # 当 ip_source 为 resource_pool 时，获取第一个 broker 的 spec_id 用于资源池申请
    if ip_source == IpSource.RESOURCE_POOL.value:
        broker_instance = cluster_obj.storageinstance_set.filter(instance_role=InstanceRole.BROKER.value).first()
        if broker_instance:
            # 如果用户传入的 resource_spec 里没有 spec_id，补充默认的 spec_id
            if resource_spec and "broker" in resource_spec:
                if "spec_id" not in resource_spec["broker"]:
                    resource_spec["broker"]["spec_id"] = broker_instance.machine.spec_id
                # 补充默认的 affinity 和 location_spec 字段，用于页面展示详细扩容信息
                if "affinity" not in resource_spec["broker"]:
                    resource_spec["broker"]["affinity"] = "MAX_EACH_ZONE_EQUAL"
                if "location_spec" not in resource_spec["broker"]:
                    resource_spec["broker"]["location_spec"] = {
                        "city": cluster_obj.region or "default",
                        "sub_zone_ids": cluster_obj.zone_list or [],
                    }
                # 补充 labels 和 label_names 字段
                if "labels" not in resource_spec["broker"]:
                    resource_spec["broker"]["labels"] = []
                if "label_names" not in resource_spec["broker"]:
                    resource_spec["broker"]["label_names"] = []

                # 计算 ext_info：扩容磁盘信息和主机数
                count = resource_spec["broker"].get("count", 1)
                spec_id = resource_spec["broker"].get("spec_id")
                total_hosts = cluster_obj.storageinstance_set.filter(instance_role=InstanceRole.BROKER.value).count()

                expansion_disk = 0
                if spec_id:
                    try:
                        spec_obj = Spec.objects.get(spec_id=spec_id)
                        # 计算规格的磁盘总容量（所有挂载点的min之和）
                        expansion_disk = sum(disk_spec.get("min", 0) for disk_spec in spec_obj.storage_spec) * count
                    except Spec.DoesNotExist:
                        pass

                ext_info = {
                    "broker": {
                        "total_hosts": total_hosts,
                        "expansion_disk": expansion_disk,
                        "total_disk": None,  # 当前集群磁盘，暂时不计算
                    }
                }

    # 构建单据参数
    ticket_param = {
        "bk_biz_id": bk_biz_id,
        "ticket_type": TicketType.KAFKA_SCALE_UP,
        "creator": creator,
        "helpers": [],
        "remark": "mcp kafka scale up ticket",
        "details": {
            "cluster_id": cluster_id,
            "ip_source": ip_source,
        },
    }

    # 根据主机来源添加不同的参数
    if ip_source == IpSource.RESOURCE_POOL.value:
        ticket_param["details"]["resource_spec"] = resource_spec
        if ext_info:
            ticket_param["details"]["ext_info"] = ext_info
    elif ip_source == IpSource.MANUAL_INPUT.value:
        ticket_param["details"]["nodes"] = nodes

    # 创建单据
    tk = Ticket.create_ticket(**ticket_param)

    return {"bill_id": tk.pk, "bill_url": tk.url}


def submit_kafka_shrink_bill(
    bk_biz_id: int,
    cluster_domain: str,
    nodes: Dict,
    creator: str = "mcp_user",
) -> Dict:
    """
    提交Kafka集群缩容单据

    Args:
        bk_biz_id: 业务ID
        cluster_domain: 集群域名
        nodes: 需要缩容的节点列表，格式为 {"broker": [{"ip": "xxx", "bk_host_id": xxx, "bk_cloud_id": xxx}]}
        creator: 创建者用户名

    Returns:
        包含单据ID和单据URL的字典
    """
    cluster_obj = Cluster.objects.get(bk_biz_id=bk_biz_id, immute_domain=cluster_domain)
    cluster_id = cluster_obj.id

    # 计算 ext_info：缩容磁盘信息
    shrink_disk = 0
    total_hosts = cluster_obj.storageinstance_set.filter(instance_role=InstanceRole.BROKER.value).count()

    # 计算缩容节点的磁盘容量
    from backend.db_meta.models import Machine, Spec

    shrink_host_ids = [node["bk_host_id"] for broker_nodes in nodes.values() for node in broker_nodes]
    shrink_machines = Machine.objects.filter(bk_host_id__in=shrink_host_ids)
    for machine in shrink_machines:
        if machine.spec_id:
            try:
                spec_obj = Spec.objects.get(spec_id=machine.spec_id)
                # 计算规格的磁盘总容量（所有挂载点的min之和）
                shrink_disk += sum(disk_spec.get("min", 0) for disk_spec in spec_obj.storage_spec or [])
            except Spec.DoesNotExist:
                pass

    # 计算当前集群总磁盘容量
    total_disk = 0
    all_broker_machines = Machine.objects.filter(
        bk_host_id__in=cluster_obj.storageinstance_set.filter(instance_role=InstanceRole.BROKER.value).values_list(
            "machine__bk_host_id", flat=True
        )
    )
    for machine in all_broker_machines:
        if machine.spec_id:
            try:
                spec_obj = Spec.objects.get(spec_id=machine.spec_id)
                total_disk += sum(disk_spec.get("min", 0) for disk_spec in spec_obj.storage_spec or [])
            except Spec.DoesNotExist:
                pass

    ext_info = {
        "broker": {
            "total_hosts": total_hosts,
            "shrink_disk": shrink_disk,
            "total_disk": total_disk,
        }
    }

    # 构建单据参数
    ticket_param = {
        "bk_biz_id": bk_biz_id,
        "ticket_type": TicketType.KAFKA_SHRINK,
        "creator": creator,
        "helpers": [],
        "remark": "mcp kafka shrink ticket",
        "details": {
            "cluster_id": cluster_id,
            "old_nodes": nodes,
            "ext_info": ext_info,
        },
    }

    # 创建单据
    tk = Ticket.create_ticket(**ticket_param)

    return {"bill_id": tk.pk, "bill_url": tk.url}


def submit_kafka_replace_bill(
    bk_biz_id: int,
    cluster_domain: str,
    old_nodes: Dict,
    ip_source: str,
    new_nodes: Dict = None,
    resource_spec: Dict = None,
    creator: str = "mcp_user",
) -> Dict:
    """
    提交Kafka集群替换单据

    Args:
        bk_biz_id: 业务ID
        cluster_domain: 集群域名
        old_nodes: 旧节点列表，格式为 {"broker": [{"ip": "xxx", "bk_host_id": xxx, "bk_cloud_id": xxx}]}
        ip_source: 主机来源 (resource_pool 或 manual_input)
        new_nodes: 新节点列表，当ip_source为manual_input时使用
        resource_spec: 资源池规格，当ip_source为resource_pool时使用
        creator: 创建者用户名

    Returns:
        包含单据ID和单据URL的字典
    """
    cluster_obj = Cluster.objects.get(bk_biz_id=bk_biz_id, immute_domain=cluster_domain)
    cluster_id = cluster_obj.id

    # 当 ip_source 为 resource_pool 时，获取第一个 broker 的 spec_id 用于资源池申请
    if ip_source == IpSource.RESOURCE_POOL.value:
        # 如果 resource_spec 为 None，初始化它
        if resource_spec is None:
            resource_spec = {}

        broker_instance = cluster_obj.storageinstance_set.filter(instance_role=InstanceRole.BROKER.value).first()
        if broker_instance:
            # 确保 resource_spec 有 broker 键
            if "broker" not in resource_spec:
                resource_spec["broker"] = {}

            # 如果用户传入的 resource_spec 里没有 spec_id，补充默认的 spec_id
            if "spec_id" not in resource_spec["broker"]:
                resource_spec["broker"]["spec_id"] = broker_instance.machine.spec_id
            # 补充默认的 affinity 和 location_spec 字段
            if "affinity" not in resource_spec["broker"]:
                resource_spec["broker"]["affinity"] = "MAX_EACH_ZONE_EQUAL"
            if "location_spec" not in resource_spec["broker"]:
                resource_spec["broker"]["location_spec"] = {
                    "city": cluster_obj.region or "default",
                    "sub_zone_ids": cluster_obj.zone_list or [],
                }
            # 补充 labels 和 label_names 字段
            if "labels" not in resource_spec["broker"]:
                resource_spec["broker"]["labels"] = []
            if "label_names" not in resource_spec["broker"]:
                resource_spec["broker"]["label_names"] = []

    # 构建单据参数
    ticket_param = {
        "bk_biz_id": bk_biz_id,
        "ticket_type": TicketType.KAFKA_REPLACE,
        "creator": creator,
        "helpers": [],
        "remark": "mcp kafka replace ticket",
        "details": {
            "cluster_id": cluster_id,
            "old_nodes": old_nodes,
            "ip_source": ip_source,
        },
    }

    # 根据主机来源添加不同的参数
    if ip_source == IpSource.RESOURCE_POOL.value:
        ticket_param["details"]["resource_spec"] = resource_spec
    elif ip_source == IpSource.MANUAL_INPUT.value:
        ticket_param["details"]["new_nodes"] = new_nodes

    # 创建单据
    tk = Ticket.create_ticket(**ticket_param)

    return {"bill_id": tk.pk, "bill_url": tk.url}


def submit_kafka_rebalance_bill(
    bk_biz_id: int,
    cluster_domain: str,
    topics: list,
    throttle_rate: int,
    target_ips: list = None,
    creator: str = "mcp_user",
) -> Dict:
    """
    提交Kafka集群Topic均衡单据

    Args:
        bk_biz_id: 业务ID
        cluster_domain: 集群域名
        topics: 需要均衡的topic列表
        throttle_rate: 均衡速率 (bytes/s)
        target_ips: 目标broker IP列表（可选），指定将数据均衡到这些IP所在的broker节点，不传则均衡到所有broker
        creator: 创建者用户名

    Returns:
        包含单据ID和单据URL的字典
    """
    cluster_obj = Cluster.objects.get(bk_biz_id=bk_biz_id, immute_domain=cluster_domain)
    cluster_id = cluster_obj.id

    # 获取所有 broker 实例
    broker_instances = cluster_obj.storageinstance_set.filter(instance_role=InstanceRole.BROKER.value)

    # 如果指定了目标IP，只选择这些IP对应的broker
    if target_ips:
        broker_instances = broker_instances.filter(machine__ip__in=target_ips)

    # 构建 instance_list 格式: [{"bk_cloud_id": xxx, "ip": "xxx", "bk_host_id": xxx, "port": xxx}]
    instance_list = []
    for broker in broker_instances:
        instance_list.append(
            {
                "bk_cloud_id": cluster_obj.bk_cloud_id,
                "ip": broker.machine.ip,
                "bk_host_id": broker.machine.bk_host_id,
                "port": broker.port,
            }
        )

    # 构建 instance_info (用于前端展示)
    instance_info = []
    for broker in broker_instances:
        instance_info.append(
            {
                "ip": broker.machine.ip,
                "bk_host_id": broker.machine.bk_host_id,
                "bk_cloud_id": cluster_obj.bk_cloud_id,
                "port": broker.port,
                "instance_id": broker.id,
            }
        )

    # 构建单据参数
    ticket_param = {
        "bk_biz_id": bk_biz_id,
        "ticket_type": TicketType.KAFKA_REBALANCE,
        "creator": creator,
        "helpers": [],
        "remark": "mcp kafka rebalance ticket",
        "details": {
            "cluster_id": cluster_id,
            "topics": topics,
            "throttle_rate": throttle_rate,
            "instance_list": instance_list,
            "instance_info": instance_info,
        },
    }

    # 创建单据
    tk = Ticket.create_ticket(**ticket_param)

    return {"bill_id": tk.pk, "bill_url": tk.url}


def submit_kafka_reboot_bill(
    bk_biz_id: int,
    cluster_domain: str,
    instance_list: list,
    creator: str = "mcp_user",
) -> Dict:
    """
    提交Kafka实例重启单据

    Args:
        bk_biz_id: 业务ID
        cluster_domain: 集群域名
        instance_list: 需要重启的实例列表，格式为 [{"ip": "xxx", "port": xxx, "instance_id": xxx, "bk_host_id": xxx, "bk_cloud_id": xxx}]
        creator: 创建者用户名

    Returns:
        包含单据ID和单据URL的字典
    """
    cluster_obj = Cluster.objects.get(bk_biz_id=bk_biz_id, immute_domain=cluster_domain)
    cluster_id = cluster_obj.id

    # 构建单据参数
    ticket_param = {
        "bk_biz_id": bk_biz_id,
        "ticket_type": TicketType.KAFKA_REBOOT,
        "creator": creator,
        "helpers": [],
        "remark": "mcp kafka reboot ticket",
        "details": {
            "cluster_id": cluster_id,
            "instance_list": instance_list,
        },
    }

    # 创建单据
    tk = Ticket.create_ticket(**ticket_param)

    return {"bill_id": tk.pk, "bill_url": tk.url}


def submit_kafka_disable_bill(
    bk_biz_id: int,
    cluster_domain: str,
    creator: str = "mcp_user",
) -> Dict:
    """
    提交Kafka集群禁用单据

    Args:
        bk_biz_id: 业务ID
        cluster_domain: 集群域名
        creator: 创建者用户名

    Returns:
        包含单据ID和单据URL的字典
    """
    cluster_obj = Cluster.objects.get(bk_biz_id=bk_biz_id, immute_domain=cluster_domain)
    cluster_id = cluster_obj.id

    # 构建单据参数
    ticket_param = {
        "bk_biz_id": bk_biz_id,
        "ticket_type": TicketType.KAFKA_DISABLE,
        "creator": creator,
        "helpers": [],
        "remark": "mcp kafka disable ticket",
        "details": {
            "cluster_id": cluster_id,
        },
    }

    # 创建单据
    tk = Ticket.create_ticket(**ticket_param)

    return {"bill_id": tk.pk, "bill_url": tk.url}


def submit_kafka_enable_bill(
    bk_biz_id: int,
    cluster_domain: str,
    creator: str = "mcp_user",
) -> Dict:
    """
    提交Kafka集群启用单据

    Args:
        bk_biz_id: 业务ID
        cluster_domain: 集群域名
        creator: 创建者用户名

    Returns:
        包含单据ID和单据URL的字典
    """
    cluster_obj = Cluster.objects.get(bk_biz_id=bk_biz_id, immute_domain=cluster_domain)
    cluster_id = cluster_obj.id

    # 构建单据参数
    ticket_param = {
        "bk_biz_id": bk_biz_id,
        "ticket_type": TicketType.KAFKA_ENABLE,
        "creator": creator,
        "helpers": [],
        "remark": "mcp kafka enable ticket",
        "details": {
            "cluster_id": cluster_id,
        },
    }

    # 创建单据
    tk = Ticket.create_ticket(**ticket_param)

    return {"bill_id": tk.pk, "bill_url": tk.url}


def submit_kafka_destroy_bill(
    bk_biz_id: int,
    cluster_domain: str,
    creator: str = "mcp_user",
) -> Dict:
    """
    提交Kafka集群删除单据

    Args:
        bk_biz_id: 业务ID
        cluster_domain: 集群域名
        creator: 创建者用户名

    Returns:
        包含单据ID和单据URL的字典
    """
    cluster_obj = Cluster.objects.get(bk_biz_id=bk_biz_id, immute_domain=cluster_domain)
    cluster_id = cluster_obj.id

    # 构建单据参数
    ticket_param = {
        "bk_biz_id": bk_biz_id,
        "ticket_type": TicketType.KAFKA_DESTROY,
        "creator": creator,
        "helpers": [],
        "remark": "mcp kafka destroy ticket",
        "details": {
            "cluster_id": cluster_id,
        },
    }

    # 创建单据
    tk = Ticket.create_ticket(**ticket_param)

    return {"bill_id": tk.pk, "bill_url": tk.url}


def submit_kafka_apply_bill(
    bk_biz_id: int,
    cluster_name: str,
    db_app_abbr: str,
    ip_source: str,
    timezone: str = "Asia/Shanghai",
    city_code: str = "default",
    region: str = "default",
    disaster_tolerance_level: str = "MAX_EACH_ZONE_EQUAL",
    replication_num: int = 2,
    version: str = "2.4.0",
    nodes: Dict = None,
    resource_spec: Dict = None,
    creator: str = "mcp_user",
) -> Dict:
    """
    提交Kafka集群部署单据

    Args:
        bk_biz_id: 业务ID
        cluster_name: 集群名称
        db_app_abbr: 应用缩写
        ip_source: 主机来源 (resource_pool 或 manual_input)
        timezone: 时区，默认Asia/Shanghai
        city_code: 城市代码，默认default
        region: 区域，默认default
        disaster_tolerance_level: 容灾级别，默认MAX_EACH_ZONE_EQUAL
        replication_num: 副本数量，默认2
        version: Kafka版本号，默认2.4.0
        nodes: 节点列表，当ip_source为manual_input时使用，格式为 {"zookeeper": [...], "broker": [...]}
        resource_spec: 资源池规格，当ip_source为resource_pool时使用
        creator: 创建者用户名

    Returns:
        包含单据ID和单据URL的字典
    """
    from backend.db_services.infras.host import get_city_code_name_map

    # 获取城市名称
    city_map = get_city_code_name_map()
    city_name = str(city_map.get(city_code, "随机"))

    # 自动生成用户名和密码
    username = get_random_string(8)
    password = DBPasswordHandler.get_random_password(security_type=DBPrivSecurityType.KAFKA_PASSWORD)
    domain = f"kafka.{cluster_name}.{db_app_abbr}.db"

    # 构建单据参数
    ticket_param = {
        "bk_biz_id": bk_biz_id,
        "ticket_type": TicketType.KAFKA_APPLY,
        "creator": creator,
        "helpers": [],
        "remark": "mcp kafka apply ticket",
        "details": {
            "username": username,
            "uid": 0,  # 暂时固定为0
            "retention_hours": 24,  # 1天
            "replication_num": replication_num,
            "port": 9092,
            "password": password,
            "partition_num": 1,
            "no_security": 0,  # 启用认证
            "nodes": nodes,
            "ip_source": ip_source,
            "db_version": version,
            "created_by": creator,
            "cluster_name": cluster_name,
            "city_code": city_code,
            "bk_cloud_id": 0,  # 默认云区域ID
            "db_app_abbr": db_app_abbr,
            "cluster_alias": "",
            "retention_bytes": -1,  # 不限制
            "disaster_tolerance_level": disaster_tolerance_level,
            "domain": domain,
            "timezone": timezone,
            "region": region,
            "city_name": city_name,  # 根据 city_code 获取
            "sub_zone_ids": [],
            "sub_zone_names": [],
        },
    }

    # 根据主机来源添加不同的参数
    if ip_source == IpSource.RESOURCE_POOL.value:
        # 补充 resource_spec 的详细信息，用于页面展示
        if resource_spec:
            for role in ["broker", "zookeeper"]:
                if role in resource_spec and "spec_id" in resource_spec[role]:
                    spec_id = resource_spec[role]["spec_id"]
                    try:
                        spec_obj = Spec.objects.get(spec_id=spec_id)
                        # 补充规格详细信息
                        resource_spec[role]["capacity"] = spec_obj.capacity
                        resource_spec[role]["cpu"] = spec_obj.cpu or {}
                        resource_spec[role]["mem"] = spec_obj.mem or {}
                        resource_spec[role]["qps"] = spec_obj.qps or {}
                        resource_spec[role]["spec_name"] = spec_obj.spec_name
                        resource_spec[role]["storage_spec"] = spec_obj.storage_spec or []
                    except Spec.DoesNotExist:
                        # 如果规格不存在，使用默认值
                        resource_spec[role]["capacity"] = 0
                        resource_spec[role]["cpu"] = {}
                        resource_spec[role]["mem"] = {}
                        resource_spec[role]["qps"] = {}
                        resource_spec[role]["spec_name"] = ""
                        resource_spec[role]["storage_spec"] = []

                    # 补充亲和性和位置规格
                    if "affinity" not in resource_spec[role]:
                        resource_spec[role]["affinity"] = disaster_tolerance_level
                    if "location_spec" not in resource_spec[role]:
                        resource_spec[role]["location_spec"] = {"city": city_code}
                    if "labels" not in resource_spec[role]:
                        resource_spec[role]["labels"] = []
                    if "label_names" not in resource_spec[role]:
                        resource_spec[role]["label_names"] = []

        ticket_param["details"]["resource_spec"] = resource_spec

    # 创建单据
    tk = Ticket.create_ticket(**ticket_param)

    return {"bill_id": tk.pk, "bill_url": tk.url}
