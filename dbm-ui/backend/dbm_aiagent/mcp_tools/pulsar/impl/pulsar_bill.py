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
import copy
from typing import Dict, List

from django.utils.translation import gettext_lazy as _
from rest_framework import serializers

from backend.db_meta.enums import ClusterPhase, ClusterType, InstanceRole
from backend.db_meta.models import Cluster, Machine, Spec
from backend.ticket.builders.common.base import IpSource
from backend.ticket.constants import TicketType
from backend.ticket.models import Ticket

# Pulsar 可扩缩容的角色（zookeeper 固定 3 台，不参与扩缩容）
SCALABLE_ROLES = {
    "broker": InstanceRole.PULSAR_BROKER.value,
    "bookkeeper": InstanceRole.PULSAR_BOOKKEEPER.value,
}


def _get_cluster(bk_biz_id: int, cluster_domain: str) -> Cluster:
    try:
        cluster = Cluster.objects.get(bk_biz_id=bk_biz_id, immute_domain=cluster_domain)
    except Cluster.DoesNotExist:
        raise serializers.ValidationError(_("集群不存在: {}").format(cluster_domain))
    # immute_domain 全局唯一，理论上不会查到非 Pulsar 集群，这里显式校验只是为了在
    # schema/数据出现意外时给出清晰的错误提示，而不是让后续按 Pulsar 角色过滤实例时
    # 静默返回空结果或产生误导性数据
    if cluster.cluster_type != ClusterType.Pulsar.value:
        raise serializers.ValidationError(
            _("集群 {} 不是 Pulsar 类型集群（实际类型: {}）").format(cluster_domain, cluster.cluster_type)
        )
    return cluster


def _validate_resource_spec_roles(resource_spec: Dict, allowed_roles: Dict) -> None:
    """
    校验 resource_spec 的角色 key 都在允许范围内。

    resource_spec 的构建逻辑是"遍历已知角色去查找"，如果角色名写错（如 'brker'
    而不是 'broker'），该角色会被静默跳过、不报错，导致单据提交成功但缺少预期的
    扩容内容。这里提前校验，把拼写错误变成明确的报错。
    """
    invalid_roles = set(resource_spec) - set(allowed_roles)
    if invalid_roles:
        raise serializers.ValidationError(
            _("resource_spec 包含不支持的角色: {}，可选角色: {}").format(
                ", ".join(sorted(invalid_roles)), ", ".join(sorted(allowed_roles))
            )
        )


def _check_phase_transfer(cluster_obj: Cluster, target_phase: str) -> None:
    """
    校验集群状态转移是否合法（启用<->禁用<->销毁）。

    Ticket.create_ticket() 是绕开单据表单的底层建单接口，不会触发
    ticket/builders/common/bigdata.py::BigDataTakeDownDetailSerializer.validate_cluster_id()
    里的状态转移校验（那条校验只在走 DRF 序列化器 is_valid() 时才生效），
    因此这里手动复用同一套判断规则，避免对已启用的集群重复提启用单之类的问题。

    抛 rest_framework 的 ValidationError 而不是裸 ValueError：drf_exception_handler
    专门识别这个类型转成简洁的业务错误（code=100），裸异常会掉进兜底分支变成
    吓人的"系统错误，请联系管理员"（code=500）。
    """
    if not ClusterPhase.cluster_status_transfer_valid(cluster_obj.phase, target_phase):
        raise serializers.ValidationError(
            "集群 {} 当前状态为 {}，不能转为 {}".format(cluster_obj.name, cluster_obj.phase, target_phase)
        )


def _sum_machine_disk(host_ids: List[int]) -> int:
    """累加一批主机的规格磁盘容量（各挂载点 min 之和）"""
    total = 0
    machines = Machine.objects.filter(bk_host_id__in=host_ids)
    spec_ids = {m.spec_id for m in machines if m.spec_id}
    specs = {s.spec_id: s for s in Spec.objects.filter(spec_id__in=spec_ids)}
    for machine in machines:
        spec = specs.get(machine.spec_id)
        if spec:
            total += sum(disk_spec.get("min", 0) for disk_spec in spec.storage_spec or [])
    return total


def _role_host_ids(cluster_obj: Cluster, instance_role: str) -> List[int]:
    return list(
        cluster_obj.storageinstance_set.filter(instance_role=instance_role).values_list(
            "machine__bk_host_id", flat=True
        )
    )


def _submit(bk_biz_id: int, ticket_type: str, creator: str, remark: str, details: Dict) -> Dict:
    """统一提单入口"""
    tk = Ticket.create_ticket(
        bk_biz_id=bk_biz_id,
        ticket_type=ticket_type,
        creator=creator,
        helpers=[],
        remark=remark,
        details=details,
    )
    return {"bill_id": tk.pk, "bill_url": tk.url}


def submit_pulsar_scale_up_bill(
    bk_biz_id: int,
    cluster_domain: str,
    ip_source: str,
    nodes: Dict = None,
    resource_spec: Dict = None,
    creator: str = "mcp_user",
) -> Dict:
    """
    提交Pulsar集群扩容单据

    Args:
        bk_biz_id: 业务ID
        cluster_domain: 集群域名
        ip_source: 主机来源 (resource_pool 或 manual_input)
        nodes: 节点列表，当ip_source为manual_input时使用，格式 {"broker": [...], "bookkeeper": [...]}
        resource_spec: 资源池规格，当ip_source为resource_pool时使用，可含 broker/bookkeeper 两个角色
        creator: 创建者用户名

    Returns:
        包含单据ID和单据URL的字典
    """
    cluster_obj = _get_cluster(bk_biz_id, cluster_domain)

    details = {"cluster_id": cluster_obj.id, "ip_source": ip_source}

    if ip_source == IpSource.RESOURCE_POOL.value:
        # 深拷贝，避免下面 setdefault/直接赋值修改到调用方传入的原始字典
        resource_spec = copy.deepcopy(resource_spec) if resource_spec else {}
        _validate_resource_spec_roles(resource_spec, SCALABLE_ROLES)

        ext_info = {}
        # Pulsar 扩容可同时涉及 broker 和 bookkeeper，逐角色补默认字段
        for role_name, instance_role in SCALABLE_ROLES.items():
            role_spec = resource_spec.get(role_name)
            if not role_spec:
                continue

            # 缺省的 spec_id 取该角色现有机器的规格
            if "spec_id" not in role_spec:
                instance = cluster_obj.storageinstance_set.filter(instance_role=instance_role).first()
                if instance:
                    role_spec["spec_id"] = instance.machine.spec_id
            # 补充默认的 affinity 和 location_spec 字段，用于页面展示详细扩容信息
            role_spec.setdefault("affinity", "MAX_EACH_ZONE_EQUAL")
            role_spec.setdefault(
                "location_spec",
                {"city": cluster_obj.region or "default", "sub_zone_ids": cluster_obj.zone_list or []},
            )
            role_spec.setdefault("labels", [])
            role_spec.setdefault("label_names", [])

            # ext_info 供前端渲染扩容磁盘信息
            count = role_spec.get("count", 1)
            expansion_disk = 0
            spec_id = role_spec.get("spec_id")
            if spec_id:
                spec_obj = Spec.objects.filter(spec_id=spec_id).first()
                if spec_obj:
                    expansion_disk = sum(disk_spec.get("min", 0) for disk_spec in spec_obj.storage_spec or []) * count
            ext_info[role_name] = {
                "total_hosts": cluster_obj.storageinstance_set.filter(instance_role=instance_role).count(),
                "expansion_disk": expansion_disk,
                "total_disk": None,  # 当前集群磁盘，暂时不计算
            }

        details["resource_spec"] = resource_spec
        if ext_info:
            details["ext_info"] = ext_info
    elif ip_source == IpSource.MANUAL_INPUT.value:
        details["nodes"] = nodes

    return _submit(bk_biz_id, TicketType.PULSAR_SCALE_UP, creator, "mcp pulsar scale up ticket", details)


def submit_pulsar_shrink_bill(
    bk_biz_id: int,
    cluster_domain: str,
    nodes: Dict,
    creator: str = "mcp_user",
) -> Dict:
    """
    提交Pulsar集群缩容单据

    约束（由单据 builder 校验）：broker 至少保留1台，bookkeeper 至少保留2台，且不支持缩容 zookeeper。

    Args:
        bk_biz_id: 业务ID
        cluster_domain: 集群域名
        nodes: 需要缩容的节点，格式 {"broker": [{"ip","bk_host_id","bk_cloud_id"}], "bookkeeper": [...]}
        creator: 创建者用户名

    Returns:
        包含单据ID和单据URL的字典
    """
    cluster_obj = _get_cluster(bk_biz_id, cluster_domain)

    # ext_info 按角色分别统计缩容磁盘，供前端渲染
    ext_info = {}
    for role_name, instance_role in SCALABLE_ROLES.items():
        role_nodes = nodes.get(role_name) or []
        shrink_host_ids = [node["bk_host_id"] for node in role_nodes]
        ext_info[role_name] = {
            "total_hosts": cluster_obj.storageinstance_set.filter(instance_role=instance_role).count(),
            "shrink_disk": _sum_machine_disk(shrink_host_ids),
            "total_disk": _sum_machine_disk(_role_host_ids(cluster_obj, instance_role)),
        }

    details = {
        "cluster_id": cluster_obj.id,
        # builder 侧 old_nodes 必须同时含 broker 和 bookkeeper 两个 key，缺失的补空列表
        "old_nodes": {role_name: nodes.get(role_name) or [] for role_name in SCALABLE_ROLES},
        "ext_info": ext_info,
    }

    return _submit(bk_biz_id, TicketType.PULSAR_SHRINK, creator, "mcp pulsar shrink ticket", details)


def submit_pulsar_replace_bill(
    bk_biz_id: int,
    cluster_domain: str,
    old_nodes: Dict,
    ip_source: str = IpSource.RESOURCE_POOL.value,
    new_nodes: Dict = None,
    resource_spec: Dict = None,
    creator: str = "mcp_user",
) -> Dict:
    """
    提交Pulsar集群替换单据

    替换前后各角色的节点数量必须一致（由单据 builder 校验）。

    Args:
        bk_biz_id: 业务ID
        cluster_domain: 集群域名
        old_nodes: 被替换的节点，格式 {"broker": [...], "bookkeeper": [...], "zookeeper": [...]}
        ip_source: 新机器来源，默认 resource_pool
        new_nodes: 新节点，当 ip_source 为 manual_input 时使用
        resource_spec: 资源池规格，当 ip_source 为 resource_pool 时使用
        creator: 创建者用户名

    Returns:
        包含单据ID和单据URL的字典
    """
    cluster_obj = _get_cluster(bk_biz_id, cluster_domain)

    details = {
        "cluster_id": cluster_obj.id,
        "ip_source": ip_source,
        "old_nodes": old_nodes,
    }

    if ip_source == IpSource.RESOURCE_POOL.value:
        # 深拷贝，避免下面 setdefault/直接赋值修改到调用方传入的原始字典
        resource_spec = copy.deepcopy(resource_spec) if resource_spec else {}
        # resource_spec 里的角色必须是 old_nodes 实际在替换的角色，否则说明角色名写错了
        # （比如把 broker 拼成 brker），静默忽略会导致用户指定的规格没生效、单据却成功提交
        invalid_roles = set(resource_spec) - set(old_nodes)
        if invalid_roles:
            raise serializers.ValidationError(
                _("resource_spec 包含 old_nodes 中不存在的角色: {}").format(", ".join(sorted(invalid_roles)))
            )

        # 替换数量需与被替换节点一致，缺省时按 old_nodes 的数量和现有规格补齐
        for role_name, role_nodes in old_nodes.items():
            if not role_nodes:
                continue
            role_spec = resource_spec.setdefault(role_name, {})
            role_spec.setdefault("count", len(role_nodes))
            if "spec_id" not in role_spec:
                # getattr 默认值只用来在还没定位到 role_name 时给出更友好的报错，
                # 不能真的静默跳过——否则 role_name 一旦对不上 InstanceRole 命名，
                # 会生成一张缺 spec_id 的替换单却不报错
                instance_role = getattr(InstanceRole, f"PULSAR_{role_name.upper()}", None)
                if not instance_role:
                    raise serializers.ValidationError(_("无法识别的角色: {}").format(role_name))
                instance = cluster_obj.storageinstance_set.filter(instance_role=instance_role.value).first()
                if instance:
                    role_spec["spec_id"] = instance.machine.spec_id
        details["resource_spec"] = resource_spec
    elif ip_source == IpSource.MANUAL_INPUT.value:
        details["new_nodes"] = new_nodes

    return _submit(bk_biz_id, TicketType.PULSAR_REPLACE, creator, "mcp pulsar replace ticket", details)


def submit_pulsar_reboot_bill(
    bk_biz_id: int,
    cluster_domain: str,
    instance_list: List[Dict],
    creator: str = "mcp_user",
) -> Dict:
    """
    提交Pulsar实例重启单据

    Args:
        bk_biz_id: 业务ID
        cluster_domain: 集群域名
        instance_list: 待重启实例列表，每项含 ip/port/instance_id/bk_host_id/bk_cloud_id
        creator: 创建者用户名

    Returns:
        包含单据ID和单据URL的字典
    """
    cluster_obj = _get_cluster(bk_biz_id, cluster_domain)

    details = {
        "cluster_id": cluster_obj.id,
        "instance_list": instance_list,
    }

    return _submit(bk_biz_id, TicketType.PULSAR_REBOOT, creator, "mcp pulsar reboot ticket", details)


def submit_pulsar_enable_bill(bk_biz_id: int, cluster_domain: str, creator: str = "mcp_user") -> Dict:
    """提交Pulsar集群启用单据（集群需处于禁用状态）"""
    cluster_obj = _get_cluster(bk_biz_id, cluster_domain)
    _check_phase_transfer(cluster_obj, ClusterPhase.ONLINE.value)
    return _submit(
        bk_biz_id,
        TicketType.PULSAR_ENABLE,
        creator,
        "mcp pulsar enable ticket",
        {"cluster_id": cluster_obj.id},
    )


def submit_pulsar_disable_bill(bk_biz_id: int, cluster_domain: str, creator: str = "mcp_user") -> Dict:
    """提交Pulsar集群禁用单据（集群需处于启用状态）"""
    cluster_obj = _get_cluster(bk_biz_id, cluster_domain)
    _check_phase_transfer(cluster_obj, ClusterPhase.OFFLINE.value)
    return _submit(
        bk_biz_id,
        TicketType.PULSAR_DISABLE,
        creator,
        "mcp pulsar disable ticket",
        {"cluster_id": cluster_obj.id},
    )


def submit_pulsar_destroy_bill(bk_biz_id: int, cluster_domain: str, creator: str = "mcp_user") -> Dict:
    """提交Pulsar集群删除单据（需集群已处于禁用状态）"""
    cluster_obj = _get_cluster(bk_biz_id, cluster_domain)
    _check_phase_transfer(cluster_obj, ClusterPhase.DESTROY.value)
    return _submit(
        bk_biz_id,
        TicketType.PULSAR_DESTROY,
        creator,
        "mcp pulsar destroy ticket",
        {"cluster_id": cluster_obj.id},
    )


def submit_pulsar_apply_bill(
    bk_biz_id: int,
    cluster_name: str,
    db_app_abbr: str,
    city_code: str,
    db_version: str,
    port: int,
    partition_num: int,
    retention_hours: int,
    replication_num: int,
    ack_quorum: int,
    ip_source: str = IpSource.RESOURCE_POOL.value,
    nodes: Dict = None,
    resource_spec: Dict = None,
    cluster_alias: str = "",
    bk_cloud_id: int = 0,
    creator: str = "mcp_user",
) -> Dict:
    """
    提交Pulsar集群部署单据

    约束（由单据 builder 校验）：
    - zookeeper 必须恰好 3 台，bookkeeper 至少 2 台，broker 至少 1 台
    - replication_num 取值 2 到 bookkeeper 台数之间
    - ack_quorum 必须小于等于 replication_num

    Args:
        bk_biz_id: 业务ID
        cluster_name: 集群名（英文）
        db_app_abbr: 业务英文缩写
        city_code: 城市代码
        db_version: Pulsar版本
        port: broker服务端口
        partition_num: 分区数
        retention_hours: 消息保留时间(小时)
        replication_num: 副本数
        ack_quorum: 最少成功写入副本数
        ip_source: 主机来源，默认 resource_pool
        nodes: 节点列表，当 ip_source 为 manual_input 时使用
        resource_spec: 资源池规格，含 zookeeper/bookkeeper/broker
        cluster_alias: 集群别名
        bk_cloud_id: 云区域ID，默认0（直连区域）
        creator: 创建者用户名

    Returns:
        包含单据ID和单据URL的字典
    """
    details = {
        "cluster_name": cluster_name,
        "cluster_alias": cluster_alias,
        "db_app_abbr": db_app_abbr,
        "city_code": city_code,
        "db_version": db_version,
        "ip_source": ip_source,
        "bk_cloud_id": bk_cloud_id,
        "port": port,
        "partition_num": partition_num,
        "retention_hours": retention_hours,
        "replication_num": replication_num,
        "ack_quorum": ack_quorum,
    }

    if ip_source == IpSource.RESOURCE_POOL.value:
        details["resource_spec"] = resource_spec
    elif ip_source == IpSource.MANUAL_INPUT.value:
        details["nodes"] = nodes

    return _submit(bk_biz_id, TicketType.PULSAR_APPLY, creator, "mcp pulsar apply ticket", details)
