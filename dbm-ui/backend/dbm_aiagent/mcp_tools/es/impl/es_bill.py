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

from backend.db_meta.enums import InstanceRole
from backend.db_meta.models import Cluster, Machine, Spec
from backend.db_services.dbbase.constants import ES_DEFAULT_PORT
from backend.ticket.builders.common.base import IpSource
from backend.ticket.constants import TicketType
from backend.ticket.models import Ticket

# ES 集群包含的节点角色
ES_ROLES = ["master", "hot", "cold", "client"]
# 热/冷数据节点支持单机多实例部署
ES_INSTANCE_NUM_ROLES = ["hot", "cold"]
# ES 可扩缩容的角色（master 固定数量，不支持扩缩容）
ES_SCALABLE_ROLES = {
    "hot": InstanceRole.ES_DATANODE_HOT.value,
    "cold": InstanceRole.ES_DATANODE_COLD.value,
    "client": InstanceRole.ES_CLIENT.value,
}
# ES 替换支持的角色（替换场景下 master 也可以被替换）
ES_REPLACE_ROLES = {
    "master": InstanceRole.ES_MASTER.value,
    "hot": InstanceRole.ES_DATANODE_HOT.value,
    "cold": InstanceRole.ES_DATANODE_COLD.value,
    "client": InstanceRole.ES_CLIENT.value,
}


def _get_cluster(bk_biz_id: int, cluster_domain: str) -> Cluster:
    """根据业务ID和集群域名获取集群对象"""
    return Cluster.objects.get(bk_biz_id=bk_biz_id, immute_domain=cluster_domain)


def _spec_disk(spec_id) -> int:
    """获取指定规格的磁盘容量（各挂载点 min 之和）"""
    if not spec_id:
        return 0
    spec = Spec.objects.filter(spec_id=spec_id).first()
    if not spec:
        return 0
    return sum(disk_spec.get("min", 0) for disk_spec in spec.storage_spec or [])


def _sum_machine_disk(host_ids: List[int]) -> int:
    """累加一批主机的规格磁盘容量（各挂载点 min 之和），按主机去重避免单机多实例重复计算"""
    machines = Machine.objects.filter(bk_host_id__in=set(host_ids))
    spec_ids = {m.spec_id for m in machines if m.spec_id}
    return sum(_spec_disk(spec_id) for spec_id in spec_ids)


def _role_host_ids(cluster_obj: Cluster, instance_role: str) -> List[int]:
    """获取集群中某角色的所有主机ID（去重，兼容单机多实例）"""
    return list(
        cluster_obj.storageinstance_set.filter(instance_role=instance_role)
        .values_list("machine__bk_host_id", flat=True)
        .distinct()
    )


def _enrich_es_resource_spec(
    resource_spec: Dict, city_code: str = "default", affinity: str = "MAX_EACH_ZONE_EQUAL"
) -> Dict:
    """补充 ES 资源池规格的亲和性、位置等字段，用于资源池申请与前端展示"""
    if not resource_spec:
        return resource_spec

    for role, spec in resource_spec.items():
        if not isinstance(spec, dict):
            continue
        spec.setdefault("affinity", affinity)
        spec.setdefault("location_spec", {"city": city_code, "sub_zone_ids": []})
        spec.setdefault("labels", [])
        spec.setdefault("label_names", [])
        # 热/冷节点补充单机实例数，默认 1
        if role in ES_INSTANCE_NUM_ROLES:
            spec.setdefault("instance_num", 1)
        # 补充规格名，供前端部署/扩容单据展示规格名称
        if "spec_name" not in spec and spec.get("spec_id"):
            spec_obj = Spec.objects.filter(spec_id=spec["spec_id"]).first()
            if spec_obj:
                spec["spec_name"] = spec_obj.spec_name

    return resource_spec


def submit_es_apply_bill(
    bk_biz_id: int,
    cluster_name: str,
    db_app_abbr: str,
    resource_spec: Dict,
    version: str,
    city_code: str,
    http_port: int = ES_DEFAULT_PORT,
    disaster_tolerance_level: str = "MAX_EACH_ZONE_EQUAL",
    cluster_alias: str = "",
    bk_cloud_id: int = 0,
    creator: str = "mcp_user",
) -> Dict:
    """
    提交 ES 集群部署单据

    Args:
        bk_biz_id: 业务ID
        cluster_name: 集群名称
        db_app_abbr: 业务英文缩写
        resource_spec: 资源池规格
        version: ES 版本号
        http_port: 端口，默认 9200
        city_code: 城市代码
        disaster_tolerance_level: 容灾级别，默认 MAX_EACH_ZONE_EQUAL
        cluster_alias: 集群别名，默认空字符串
        bk_cloud_id: 云区域ID，默认 0
        creator: 创建者用户名

    Returns:
        包含单据ID和单据URL的字典
    """
    details = {
        "cluster_name": cluster_name,
        "cluster_alias": cluster_alias,
        "db_app_abbr": db_app_abbr,
        "db_version": version,
        "ip_source": IpSource.RESOURCE_POOL.value,
        "bk_cloud_id": bk_cloud_id,
        "city_code": city_code,
        "disaster_tolerance_level": disaster_tolerance_level,
        "http_port": http_port,
        "resource_spec": _enrich_es_resource_spec(resource_spec, city_code, disaster_tolerance_level),
    }

    ticket_param = {
        "bk_biz_id": bk_biz_id,
        "ticket_type": TicketType.ES_APPLY,
        "creator": creator,
        "helpers": [],
        "remark": "mcp es apply ticket",
        "details": details,
    }

    tk = Ticket.create_ticket(**ticket_param)
    return {"bill_id": tk.pk, "bill_url": tk.url}


def submit_es_scale_up_bill(
    bk_biz_id: int,
    cluster_domain: str,
    resource_spec: Dict,
    creator: str = "mcp_user",
) -> Dict:
    """
    提交 ES 集群扩容单据

    Args:
        bk_biz_id: 业务ID
        cluster_domain: 集群域名
        resource_spec: 资源池规格
        creator: 创建者用户名

    Returns:
        包含单据ID和单据URL的字典
    """
    cluster_obj = _get_cluster(bk_biz_id, cluster_domain)
    cluster_id = cluster_obj.id

    enriched_spec = _enrich_es_resource_spec(resource_spec, cluster_obj.region or "default") or {}

    # 计算 ext_info：按角色统计扩容磁盘与主机数，供前端渲染单据需求信息
    ext_info = {}
    for role_name, instance_role in ES_SCALABLE_ROLES.items():
        role_spec = enriched_spec.get(role_name)
        if not isinstance(role_spec, dict):
            continue
        count = role_spec.get("count", 1)
        role_host_ids = _role_host_ids(cluster_obj, instance_role)
        ext_info[role_name] = {
            "total_hosts": len(role_host_ids),
            "expansion_disk": _spec_disk(role_spec.get("spec_id")) * count,
            "total_disk": _sum_machine_disk(role_host_ids),
        }

    details = {
        "cluster_id": cluster_id,
        "ip_source": IpSource.RESOURCE_POOL.value,
        "resource_spec": enriched_spec,
        "ext_info": ext_info,
    }

    ticket_param = {
        "bk_biz_id": bk_biz_id,
        "ticket_type": TicketType.ES_SCALE_UP,
        "creator": creator,
        "helpers": [],
        "remark": "mcp es scale up ticket",
        "details": details,
    }

    tk = Ticket.create_ticket(**ticket_param)
    return {"bill_id": tk.pk, "bill_url": tk.url}


def submit_es_shrink_bill(
    bk_biz_id: int,
    cluster_domain: str,
    old_nodes: Dict,
    creator: str = "mcp_user",
) -> Dict:
    """
    提交 ES 集群缩容单据

    Args:
        bk_biz_id: 业务ID
        cluster_domain: 集群域名
        old_nodes: 需要缩容的节点列表，格式为 {"hot": [...], "cold": [...], "client": [...]}
        creator: 创建者用户名

    Returns:
        包含单据ID和单据URL的字典
    """
    cluster_obj = _get_cluster(bk_biz_id, cluster_domain)
    cluster_id = cluster_obj.id

    # 计算 ext_info：按角色统计缩容磁盘、总磁盘与主机数，供前端渲染单据需求信息
    ext_info = {}
    for role_name, instance_role in ES_SCALABLE_ROLES.items():
        role_nodes = old_nodes.get(role_name) or []
        shrink_host_ids = [node["bk_host_id"] for node in role_nodes]
        role_host_ids = _role_host_ids(cluster_obj, instance_role)
        ext_info[role_name] = {
            "total_hosts": len(role_host_ids),
            "shrink_disk": _sum_machine_disk(shrink_host_ids),
            "total_disk": _sum_machine_disk(role_host_ids),
        }

    ticket_param = {
        "bk_biz_id": bk_biz_id,
        "ticket_type": TicketType.ES_SHRINK,
        "creator": creator,
        "helpers": [],
        "remark": "mcp es shrink ticket",
        "details": {
            "cluster_id": cluster_id,
            # builder 侧 old_nodes 必须同时含 hot/cold/client 三个 key，缺失的补空列表
            "old_nodes": {role_name: old_nodes.get(role_name) or [] for role_name in ES_SCALABLE_ROLES},
            "ext_info": ext_info,
        },
    }

    tk = Ticket.create_ticket(**ticket_param)
    return {"bill_id": tk.pk, "bill_url": tk.url}


def submit_es_replace_bill(
    bk_biz_id: int,
    cluster_domain: str,
    old_nodes: Dict,
    resource_spec: Dict = None,
    creator: str = "mcp_user",
) -> Dict:
    """
    提交 ES 集群替换单据

    Args:
        bk_biz_id: 业务ID
        cluster_domain: 集群域名
        old_nodes: 旧节点列表，格式为 {"hot": [...], "cold": [...], "client": [...], "master": [...]}
        resource_spec: 资源池规格，默认与被替换节点规格相同
        creator: 创建者用户名

    Returns:
        包含单据ID和单据URL的字典
    """
    cluster_obj = _get_cluster(bk_biz_id, cluster_domain)
    cluster_id = cluster_obj.id

    # 深拷贝，避免下面 setdefault/直接赋值修改到调用方传入的原始字典
    resource_spec = copy.deepcopy(resource_spec) if resource_spec else {}

    # resource_spec 里的角色必须是 old_nodes 实际在替换的角色，否则说明角色名写错了
    # （比如把 hot 拼成 ht），静默忽略会导致用户指定的规格没生效、单据却成功提交
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
            instance_role = ES_REPLACE_ROLES.get(role_name)
            if not instance_role:
                raise serializers.ValidationError(_("无法识别的角色: {}").format(role_name))
            instance = cluster_obj.storageinstance_set.filter(instance_role=instance_role).first()
            if instance:
                role_spec["spec_id"] = instance.machine.spec_id

    details = {
        "cluster_id": cluster_id,
        "old_nodes": old_nodes,
        "ip_source": IpSource.RESOURCE_POOL.value,
        "resource_spec": _enrich_es_resource_spec(resource_spec, cluster_obj.region or "default"),
    }

    ticket_param = {
        "bk_biz_id": bk_biz_id,
        "ticket_type": TicketType.ES_REPLACE,
        "creator": creator,
        "helpers": [],
        "remark": "mcp es replace ticket",
        "details": details,
    }

    tk = Ticket.create_ticket(**ticket_param)
    return {"bill_id": tk.pk, "bill_url": tk.url}


def submit_es_enable_bill(
    bk_biz_id: int,
    cluster_domain: str,
    creator: str = "mcp_user",
) -> Dict:
    """提交 ES 集群启用单据"""
    cluster_obj = _get_cluster(bk_biz_id, cluster_domain)
    cluster_id = cluster_obj.id

    ticket_param = {
        "bk_biz_id": bk_biz_id,
        "ticket_type": TicketType.ES_ENABLE,
        "creator": creator,
        "helpers": [],
        "remark": "mcp es enable ticket",
        "details": {"cluster_id": cluster_id},
    }

    tk = Ticket.create_ticket(**ticket_param)
    return {"bill_id": tk.pk, "bill_url": tk.url}


def submit_es_disable_bill(
    bk_biz_id: int,
    cluster_domain: str,
    creator: str = "mcp_user",
) -> Dict:
    """提交 ES 集群禁用单据"""
    cluster_obj = _get_cluster(bk_biz_id, cluster_domain)
    cluster_id = cluster_obj.id

    ticket_param = {
        "bk_biz_id": bk_biz_id,
        "ticket_type": TicketType.ES_DISABLE,
        "creator": creator,
        "helpers": [],
        "remark": "mcp es disable ticket",
        "details": {"cluster_id": cluster_id},
    }

    tk = Ticket.create_ticket(**ticket_param)
    return {"bill_id": tk.pk, "bill_url": tk.url}


def submit_es_destroy_bill(
    bk_biz_id: int,
    cluster_domain: str,
    creator: str = "mcp_user",
) -> Dict:
    """提交 ES 集群删除单据"""
    cluster_obj = _get_cluster(bk_biz_id, cluster_domain)
    cluster_id = cluster_obj.id

    ticket_param = {
        "bk_biz_id": bk_biz_id,
        "ticket_type": TicketType.ES_DESTROY,
        "creator": creator,
        "helpers": [],
        "remark": "mcp es destroy ticket",
        "details": {"cluster_id": cluster_id},
    }

    tk = Ticket.create_ticket(**ticket_param)
    return {"bill_id": tk.pk, "bill_url": tk.url}


def submit_es_create_clb_bill(
    bk_biz_id: int,
    cluster_domain: str,
    creator: str = "mcp_user",
) -> Dict:
    """提交 ES 创建 CLB 单据"""
    cluster_obj = _get_cluster(bk_biz_id, cluster_domain)
    cluster_id = cluster_obj.id

    ticket_param = {
        "bk_biz_id": bk_biz_id,
        "ticket_type": TicketType.ES_CREATE_CLB,
        "creator": creator,
        "helpers": [],
        "remark": "mcp es create clb ticket",
        "details": {"cluster_id": cluster_id},
    }

    tk = Ticket.create_ticket(**ticket_param)
    return {"bill_id": tk.pk, "bill_url": tk.url}


def submit_es_bind_clb_bill(
    bk_biz_id: int,
    cluster_domain: str,
    creator: str = "mcp_user",
) -> Dict:
    """提交 ES 主域名绑定 CLB 单据"""
    cluster_obj = _get_cluster(bk_biz_id, cluster_domain)
    cluster_id = cluster_obj.id

    ticket_param = {
        "bk_biz_id": bk_biz_id,
        "ticket_type": TicketType.ES_DNS_BIND_CLB,
        "creator": creator,
        "helpers": [],
        "remark": "mcp es bind clb ticket",
        "details": {"cluster_id": cluster_id},
    }

    tk = Ticket.create_ticket(**ticket_param)
    return {"bill_id": tk.pk, "bill_url": tk.url}


def submit_es_unbind_clb_bill(
    bk_biz_id: int,
    cluster_domain: str,
    creator: str = "mcp_user",
) -> Dict:
    """提交 ES 主域名解绑 CLB 单据"""
    cluster_obj = _get_cluster(bk_biz_id, cluster_domain)
    cluster_id = cluster_obj.id

    ticket_param = {
        "bk_biz_id": bk_biz_id,
        "ticket_type": TicketType.ES_DNS_UNBIND_CLB,
        "creator": creator,
        "helpers": [],
        "remark": "mcp es unbind clb ticket",
        "details": {"cluster_id": cluster_id},
    }

    tk = Ticket.create_ticket(**ticket_param)
    return {"bill_id": tk.pk, "bill_url": tk.url}


def submit_es_create_polaris_bill(
    bk_biz_id: int,
    cluster_domain: str,
    creator: str = "mcp_user",
) -> Dict:
    """提交 ES 创建北极星单据"""
    cluster_obj = _get_cluster(bk_biz_id, cluster_domain)
    cluster_id = cluster_obj.id

    ticket_param = {
        "bk_biz_id": bk_biz_id,
        "ticket_type": TicketType.ES_CREATE_POLARIS,
        "creator": creator,
        "helpers": [],
        "remark": "mcp es create polaris ticket",
        "details": {"cluster_id": cluster_id},
    }

    tk = Ticket.create_ticket(**ticket_param)
    return {"bill_id": tk.pk, "bill_url": tk.url}


def submit_es_delete_polaris_bill(
    bk_biz_id: int,
    cluster_domain: str,
    creator: str = "mcp_user",
) -> Dict:
    """提交 ES 删除北极星单据"""
    cluster_obj = _get_cluster(bk_biz_id, cluster_domain)
    cluster_id = cluster_obj.id

    ticket_param = {
        "bk_biz_id": bk_biz_id,
        "ticket_type": TicketType.ES_DELETE_POLARIS,
        "creator": creator,
        "helpers": [],
        "remark": "mcp es delete polaris ticket",
        "details": {"cluster_id": cluster_id},
    }

    tk = Ticket.create_ticket(**ticket_param)
    return {"bill_id": tk.pk, "bill_url": tk.url}
