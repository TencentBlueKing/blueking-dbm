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
from typing import Any, Dict

from django.db import transaction
from django.utils.translation import ugettext_lazy as _

from backend.components import NameServiceApi
from backend.configuration.models import DBAdministrator
from backend.db_meta import api
from backend.db_meta.enums import ClusterEntryType, TenDBClusterSpiderRole
from backend.db_meta.enums.cluster_entry_role import ClusterEntryRole
from backend.db_meta.enums.cluster_type import ClusterType
from backend.db_meta.models import CLBEntryDetail, Cluster, ClusterEntry, ProxyInstance
from backend.db_services.plugin.nameservice.clb import get_dns_status_by_ip, response_fail, response_ok
from backend.env import CLB_DOMAIN
from backend.flow.utils import dns_manage


def create_lb_and_register_target(cluster_id: int, role: str) -> Dict[str, Any]:
    """创建clb并绑定后端主机"""

    # 获取信息
    cluster = Cluster.objects.get(id=cluster_id)
    immute_domain = cluster.immute_domain
    bk_biz_id = cluster.bk_biz_id
    region = cluster.region
    # 判断clb是否已经存在
    if ClusterEntry.objects.filter(cluster=cluster, cluster_entry_type=ClusterEntryType.CLB.value).exists():
        message = "clb of cluster:{} has existed".format(immute_domain)
        return response_fail(code=3, message=message)
    if cluster.cluster_type == ClusterType.TenDBHA:
        proixes = ProxyInstance.objects.filter(cluster=cluster).all()
        ips = [f"{proxy.machine.ip}:{proxy.port}" for proxy in proixes]
    elif cluster.cluster_type == ClusterType.TenDBCluster:
        proixes = cluster.proxyinstance_set.filter(tendbclusterspiderext__spider_role=role)
        ips = [f"{proxy.machine.ip}:{proxy.port}" for proxy in proixes]
    else:
        message = "not supported cluster type"
        return response_fail(code=4, message=message)
    if not ips or len(proixes) < 0:
        message = "no target to bind"
        return response_fail(code=5, message=message)
    db_type = ClusterType.cluster_type_to_db_type(cluster.cluster_type)
    # 通过bk_biz_id获取manager，backupmanager，去除admin
    users = DBAdministrator().get_biz_db_type_admins(bk_biz_id=bk_biz_id, db_type=db_type)
    users = [user for user in users if user != "admin"]
    manager = users[0]
    backupmanager = users[1] if len(users) > 1 else users[0]
    clb_port = proixes[0].port
    # 进行请求，得到返回结果
    output = NameServiceApi.clb_create_lb_and_register_target(
        {
            "region": region,
            "loadbalancername": immute_domain,
            "listenername": immute_domain,
            "manager": manager,
            "backupmanager": backupmanager,
            "protocol": "TCP",
            "ips": ips,
        },
        raw=True,
    )
    output["clb_port"] = clb_port
    return output


def operate_part_target(cluster_id: int, ips: list, bind: bool) -> dict:
    """绑定或解绑部分后端主机"""

    # 获取信息
    cluster = Cluster.objects.get(id=cluster_id)
    cluster_entry = ClusterEntry.objects.get(cluster=cluster, cluster_entry_type=ClusterEntryType.CLB.value)
    clb_detail = CLBEntryDetail.objects.get(entry=cluster_entry)
    params = {
        "region": clb_detail.clb_region,
        "loadbalancerid": clb_detail.clb_id,
        "listenerid": clb_detail.listener_id,
        "ips": ips,
    }
    # 进行请求，得到返回结果
    if bind:
        output = NameServiceApi.clb_register_part_target(params, raw=True)
    else:
        output = NameServiceApi.clb_deregister_part_target(params, raw=True)
    return output


def deregister_target_and_delete_lb(cluster_id: int) -> Dict[str, Any]:
    """解绑后端主机并删除clb"""

    # 获取集群信息
    cluster = Cluster.objects.get(id=cluster_id)
    cluster_entry = ClusterEntry.objects.get(cluster=cluster, cluster_entry_type=ClusterEntryType.CLB.value)
    clb_detail = CLBEntryDetail.objects.get(entry=cluster_entry)
    region = clb_detail.clb_region
    loadbalancerid = clb_detail.clb_id
    listenerid = clb_detail.listener_id

    # 进行请求，得到返回结果
    output = NameServiceApi.clb_deregister_target_and_del_lb(
        {
            "region": region,
            "loadbalancerid": loadbalancerid,
            "listenerid": listenerid,
        },
        raw=True,
    )
    return output


def add_clb_info_to_meta(output: Dict[str, Any], cluster_id: int, role: str, creator: str) -> Dict[str, Any]:
    """clb信息写入meta"""

    # 获取信息
    cluster = Cluster.objects.get(id=cluster_id)
    entry_role = get_cluster_entry_role(role)
    # 进行判断请求结果,请求结果正确，写入数据库
    if output["code"] == 0:
        clb_ip = output["data"]["loadbalancerip"]
        try:
            api.entry.clb.create(
                [
                    {
                        "domain": cluster.immute_domain,
                        "clb_ip": clb_ip,
                        "clb_id": output["data"]["loadbalancerid"],
                        "clb_listener_id": output["data"]["listenerid"],
                        "clb_region": cluster.region,
                        "clb_port": output["clb_port"],
                        "role": entry_role,
                    }
                ],
                creator,
            )
        except Exception as e:
            message = "add clb info to meta fail, error:{}".format(str(e))
            return response_fail(code=3, message=message)
    return response_ok()


def delete_clb_info_from_meta(output: Dict[str, Any], cluster_id: int) -> Dict[str, Any]:
    """在meta中删除clb信息"""

    # 获取信息
    cluster = Cluster.objects.get(id=cluster_id)
    cluster_entry = ClusterEntry.objects.get(cluster=cluster, cluster_entry_type=ClusterEntryType.CLB.value)
    clb_detail = CLBEntryDetail.objects.get(entry=cluster_entry)
    # 进行判断请求结果，如果为0操作删除db数据
    if output["code"] == 0:
        loadbalancerid = clb_detail.clb_id
        try:
            cluster.clusterentry_set.filter(cluster_entry_type=ClusterEntryType.CLB).delete()
        except Exception as e:
            message = "delete clb:{} info in db fail, error:{}".format(loadbalancerid, str(e))
            return response_fail(code=1, message=message)
    return response_ok()


def add_clb_domain_to_dns(cluster_id: int, creator: str) -> Dict[str, Any]:
    """添加clb域名到dns"""

    # 获取信息
    cluster = Cluster.objects.get(id=cluster_id)
    cluster_entry = ClusterEntry.objects.get(cluster=cluster, cluster_entry_type=ClusterEntryType.CLB.value)
    clb_detail = CLBEntryDetail.objects.get(entry=cluster_entry)
    immute_domain = cluster.immute_domain
    bk_cloud_id = cluster.bk_cloud_id
    bk_biz_id = cluster.bk_biz_id
    clb_ip = clb_detail.clb_ip
    # 添加clb域名以及dns
    if CLB_DOMAIN:
        # 添加clb域名dns
        clb_domain = build_clb_domain(immute_domain)
        result = dns_manage.DnsManage(bk_biz_id=bk_biz_id, bk_cloud_id=bk_cloud_id).get_domain(domain_name=clb_domain)
        if len(result) < 1:
            result = dns_manage.DnsManage(bk_biz_id=bk_biz_id, bk_cloud_id=bk_cloud_id).create_domain(
                instance_list=["{}#{}".format(clb_ip, str(clb_detail.clb_port))], add_domain_name=clb_domain
            )
        if not result:
            return {"code": 3, "message": "add clb domain to dns fail"}
        try:
            if not ClusterEntry.objects.filter(
                cluster=cluster, cluster_entry_type=ClusterEntryType.CLBDNS.value
            ).exists():
                ClusterEntry.objects.create(
                    cluster=cluster,
                    cluster_entry_type=ClusterEntryType.CLBDNS,
                    entry=clb_domain,
                    creator=creator,
                    forward_to_id=cluster_entry.id,
                )
        except Exception as e:
            message = "cluster:{} add clb domain fail, error:{}".format(immute_domain, str(e))
            return response_fail(code=3, message=message)
    return response_ok()


def build_clb_domain(domain: str) -> str:
    """构建clb域名数据"""
    return "{}.{}".format("clb", domain)


def delete_clb_domain_from_dns(cluster_id: int) -> Dict[str, Any]:
    """从dns中删除clb域名"""

    cluster = Cluster.objects.get(id=cluster_id)
    dnsclb_entry = ClusterEntry.objects.filter(
        cluster=cluster, cluster_entry_type=ClusterEntryType.CLBDNS.value
    ).first()
    # 如果存在clb域名指向clb ip，则删除
    if dnsclb_entry:
        clb_detail = CLBEntryDetail.objects.get(entry=dnsclb_entry.forward_to)
        immute_domain = cluster.immute_domain
        bk_cloud_id = cluster.bk_cloud_id
        bk_biz_id = cluster.bk_biz_id
        clb_ip = clb_detail.clb_ip
        port = clb_detail.clb_port
        clb_domain = build_clb_domain(immute_domain)
        # 删除dns：clb域名绑定clb ip
        dns_list = dns_manage.DnsManage(bk_biz_id=bk_biz_id, bk_cloud_id=bk_cloud_id).get_domain(
            domain_name=clb_domain
        )
        if len(dns_list) > 1:
            result = dns_manage.DnsManage(bk_biz_id=bk_biz_id, bk_cloud_id=bk_cloud_id).remove_domain_ip(
                domain="clb.{}".format(immute_domain), del_instance_list=["{}#{}".format(clb_ip, str(port))]
            )
            if not result:
                message = "delete clb.{} dns info fail".format(immute_domain)
                return response_fail(code=1, message=message)
        # 删除元数据clbDns信息
        try:
            cluster.clusterentry_set.filter(cluster_entry_type=ClusterEntryType.CLBDNS).delete()
        except Exception as e:
            message = "delete clb domain of cluster:{} fail, error:{}".format(immute_domain, str(e))
            return response_fail(code=1, message=message)
    return response_ok()


def immute_domain_clb_ip(cluster_id: int, creator: str, bind: bool, role: str) -> Dict[str, Any]:
    """主域名指向clb ip或者解绑

    Args:
        cluster_id: 集群ID
        creator: 操作人
        bind: True表示绑定，False表示解绑
        role: 角色(仅TenDBCluster类型集群需要)

    Returns:
        操作结果字典
    """
    try:
        # 获取集群信息
        cluster = Cluster.objects.get(id=cluster_id)
        clb_detail = get_clb_detail_by_cluster(cluster=cluster)
        # 提取公共参数
        immute_domain = cluster.immute_domain
        bk_cloud_id = cluster.bk_cloud_id
        bk_biz_id = cluster.bk_biz_id
        clb_ip = clb_detail.clb_ip
        port = clb_detail.clb_port
        clb_ip_port = f"{clb_ip}#{port}"

        # 检查集群类型并获取代理IP列表
        if cluster.cluster_type == ClusterType.TenDBHA:
            proxies = ProxyInstance.objects.filter(cluster=cluster).all()
            proxy_ips = [proxy.machine.ip for proxy in proxies]
        elif cluster.cluster_type == ClusterType.TenDBCluster:
            proxies = cluster.proxyinstance_set.filter(tendbclusterspiderext__spider_role=role)
            proxy_ips = [proxy.machine.ip for proxy in proxies]
        else:
            return response_fail(code=4, message=_("不支持的集群类型"))

        # 检查CLB是否存在
        if not ClusterEntry.objects.filter(cluster=cluster, cluster_entry_type=ClusterEntryType.CLB.value).exists():
            return response_fail(code=3, message=_("集群:{}的CLB不存在,无法绑定或解绑CLB IP".format(immute_domain)))
        if bind:
            return _bind_clb_ip(cluster, immute_domain, bk_cloud_id, bk_biz_id, clb_ip_port, proxy_ips, port, creator)
        else:
            return _unbind_clb_ip(
                cluster, immute_domain, bk_cloud_id, bk_biz_id, clb_ip_port, proxy_ips, port, creator
            )

    except Exception as e:
        return response_fail(code=1, message=_("操作异常: {}".format(str(e))))


def _bind_clb_ip(cluster, immute_domain, bk_cloud_id, bk_biz_id, clb_ip_port, proxy_ips, port, creator):
    """绑定CLB IP"""
    if domain_bind_clb_status(immute_domain=immute_domain, bk_cloud_id=bk_cloud_id):
        return response_fail(code=3, message=_("主域名已绑定CLB IP"))

    # 添加DNS：主域名指向CLB IP
    if not get_dns_status_by_ip(
        bk_biz_id=bk_biz_id, bk_cloud_id=bk_cloud_id, domain=immute_domain, ip=clb_ip_port.split("#")[0]
    ):
        if not dns_manage.DnsManage(bk_biz_id, bk_cloud_id).create_domain(
            instance_list=[clb_ip_port], add_domain_name=immute_domain
        ):
            return response_fail(code=3, message=_("添加主域名CLB IP到DNS失败"))

    # 删除老的DNS：主域名指向proxy
    delete_dns_list = [
        f"{ip}#{port}" for ip in proxy_ips if get_dns_status_by_ip(bk_biz_id, bk_cloud_id, immute_domain, ip)
    ]

    if delete_dns_list and not dns_manage.DnsManage(bk_biz_id, bk_cloud_id).remove_domain_ip(
        domain=immute_domain, del_instance_list=delete_dns_list
    ):
        return response_fail(code=3, message=_("从DNS删除主域名代理IP失败"))

    # 修改元数据
    try:
        bind_clb_domain(immute_domain=immute_domain, bk_cloud_id=bk_cloud_id, created_by=creator)
    except Exception as e:
        return response_fail(code=3, message=_("修改主域名绑定CLB IP元数据失败: {}".format(str(e))))

    return response_ok()


def _unbind_clb_ip(cluster, immute_domain, bk_cloud_id, bk_biz_id, clb_ip_port, proxy_ips, port, creator):
    """解绑CLB IP"""
    if not domain_bind_clb_status(immute_domain=immute_domain, bk_cloud_id=bk_cloud_id):
        return response_ok()

    # 添加DNS：主域名指向proxy
    add_dns_list = [
        f"{ip}#{port}" for ip in proxy_ips if not get_dns_status_by_ip(bk_biz_id, bk_cloud_id, immute_domain, ip)
    ]

    if add_dns_list and not dns_manage.DnsManage(bk_biz_id, bk_cloud_id).create_domain(
        instance_list=add_dns_list, add_domain_name=immute_domain
    ):
        return response_fail(code=3, message=_("添加主域名代理IP到DNS失败"))

    # 删除老的DNS：主域名指向CLB IP
    if get_dns_status_by_ip(bk_biz_id, bk_cloud_id, immute_domain, clb_ip_port.split("#")[0]):
        if not dns_manage.DnsManage(bk_biz_id, bk_cloud_id).remove_domain_ip(immute_domain, [clb_ip_port]):
            return response_fail(code=3, message=_("从DNS删除主域名CLB IP失败"))

    # 修改元数据
    try:
        unbind_clb_domain(immute_domain=immute_domain, bk_cloud_id=bk_cloud_id, created_by=creator)
    except Exception as e:
        return response_fail(code=3, message=_("修改主域名解绑CLB IP元数据失败: {}".format(str(e))))

    return response_ok()


@transaction.atomic
def bind_clb_domain(immute_domain: str, bk_cloud_id: int, created_by: str):
    """主域名直接指向CLB"""
    cluster = Cluster.objects.get(bk_cloud_id=bk_cloud_id, immute_domain=immute_domain)
    immute_entry = cluster.clusterentry_set.filter(
        cluster_entry_type=ClusterEntryType.DNS.value, entry=cluster.immute_domain
    ).first()
    clb_entry = cluster.clusterentry_set.filter(cluster_entry_type=ClusterEntryType.CLB.value).first()
    immute_entry.forward_to_id = clb_entry.id
    immute_entry.creator = created_by
    immute_entry.save(update_fields=["forward_to_id", "creator"])


@transaction.atomic
def unbind_clb_domain(immute_domain: str, bk_cloud_id: int, created_by: str):
    """主域名解绑CLB"""
    cluster = Cluster.objects.get(bk_cloud_id=bk_cloud_id, immute_domain=immute_domain)
    immute_entry = cluster.clusterentry_set.filter(
        cluster_entry_type=ClusterEntryType.DNS.value, entry=cluster.immute_domain
    ).first()
    immute_entry.forward_to_id = None
    immute_entry.creator = created_by
    immute_entry.save(update_fields=["forward_to_id", "creator"])


def get_cluster_entry_role(role: str) -> ClusterEntryRole:
    """根据角色获取集群入口角色
    Args:
        role: 集群角色
    Returns:
        ClusterEntryRole: 返回MASTER_ENTRY或SLAVE_ENTRY
    """
    if role in [TenDBClusterSpiderRole.SPIDER_SLAVE]:
        return ClusterEntryRole.SLAVE_ENTRY
    return ClusterEntryRole.MASTER_ENTRY


def get_clb_detail_by_cluster(cluster: Cluster) -> CLBEntryDetail:
    """根据集群获取CLB详情

    Args:
        cluster: 集群对象

    Returns:
        CLB详情对象

    Raises:
        DoesNotExist: 当CLB不存在时抛出
    """
    clb_entry = ClusterEntry.objects.get(cluster=cluster, cluster_entry_type=ClusterEntryType.CLB.value)
    return CLBEntryDetail.objects.get(entry=clb_entry)


def domain_bind_clb_status(immute_domain: str, bk_cloud_id: int) -> bool:
    """判断主域名是否绑定了clb ip"""

    cluster = Cluster.objects.get(bk_cloud_id=bk_cloud_id, immute_domain=immute_domain)
    immute_entry = cluster.clusterentry_set.filter(
        cluster_entry_type=ClusterEntryType.DNS.value, entry=cluster.immute_domain
    ).first()
    return immute_entry.forward_to_id is not None
