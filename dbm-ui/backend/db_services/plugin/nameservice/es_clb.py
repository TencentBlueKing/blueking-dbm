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

from backend.components import NameServiceApi
from backend.configuration.constants import DBType
from backend.configuration.models import DBAdministrator
from backend.db_meta import api
from backend.db_meta.enums import ClusterEntryType, InstanceRole
from backend.db_meta.models import Cluster, ClusterEntry, StorageInstance
from backend.env import CLB_DOMAIN
from backend.flow.engine.bamboo.scene.es.atom_jobs.access_manager import (
    get_access_ips_from_dbmeta,
    get_access_ips_from_dns,
)
from backend.flow.utils import dns_manage
from backend.flow.utils.clb_manage import get_clb_by_ip


@transaction.atomic
def mdy_dbmeta_for_es_domain_bind_clb(immute_domain: str, bk_cloud_id: int, created_by: str):
    """主域名直接指向CLB"""
    cluster = Cluster.objects.get(bk_cloud_id=bk_cloud_id, immute_domain=immute_domain)
    immute_entry = cluster.clusterentry_set.filter(
        cluster_entry_type=ClusterEntryType.DNS.value, entry=cluster.immute_domain
    ).first()
    clb_entry = cluster.clusterentry_set.filter(cluster_entry_type=ClusterEntryType.CLB.value).first()
    # 域名entry 增加forward
    immute_entry.forward_to_id = clb_entry.id
    immute_entry.creator = created_by
    immute_entry.save(update_fields=["forward_to_id", "creator"])

    # 解除域名entry与storage instance的绑定关系
    immute_entry.storageinstance_set.clear()


@transaction.atomic
def mdy_dbmeta_for_es_domain_unbind_clb(immute_domain: str, bk_cloud_id: int, created_by: str):
    """主域名解绑CLB"""
    cluster = Cluster.objects.get(bk_cloud_id=bk_cloud_id, immute_domain=immute_domain)
    immute_entry = cluster.clusterentry_set.filter(
        cluster_entry_type=ClusterEntryType.DNS.value, entry=cluster.immute_domain
    ).first()
    # 移除域名entry的forward
    immute_entry.forward_to_id = None
    immute_entry.creator = created_by
    immute_entry.save(update_fields=["forward_to_id", "creator"])

    # 增加域名entry与storage instance的绑定关系
    for role in [
        InstanceRole.ES_CLIENT,
        InstanceRole.ES_DATANODE_HOT,
        InstanceRole.ES_DATANODE_COLD,
        InstanceRole.ES_MASTER,
    ]:
        instances = StorageInstance.objects.filter(instance_role=role, bind_entry__cluster_id=cluster.id)
        if instances.exists():
            immute_entry.storageinstance_set.add(*instances)
            immute_entry.save()
            break


def is_es_domain_bind_clb(immute_domain: str, bk_cloud_id: int) -> bool:
    """判断主域名是否绑定了clb ip"""
    cluster = Cluster.objects.get(bk_cloud_id=bk_cloud_id, immute_domain=immute_domain)
    immute_entry = cluster.clusterentry_set.filter(
        cluster_entry_type=ClusterEntryType.DNS.value, entry=cluster.immute_domain
    ).first()
    return immute_entry.forward_to_id is not None


def is_ip_in_dns(bk_biz_id: int, bk_cloud_id: int, domain: str, ip: str) -> bool:
    """判断ip是否在域名映射中"""
    results = dns_manage.DnsManage(bk_biz_id=bk_biz_id, bk_cloud_id=bk_cloud_id).get_domain(domain_name=domain)
    for result in results:
        if result["ip"] == ip:
            return True
    return False


def get_dns_status_by_domain(bk_biz_id: int, bk_cloud_id: int, domain: str) -> bool:
    """判断域名是否存在"""
    result = dns_manage.DnsManage(bk_biz_id=bk_biz_id, bk_cloud_id=bk_cloud_id).get_domain(domain_name=domain)
    return len(result) > 0


def response_ok() -> Dict[str, Any]:
    """成功返回"""

    return {"code": 0, "message": "ok"}


def response_fail(code: int, message: str) -> Dict[str, Any]:
    """失败返回"""

    return {"code": code, "message": message}


def create_lb_and_register_target(cluster_id: int) -> Dict[str, Any]:
    """创建clb并绑定后端主机"""

    # 获取信息
    cluster = Cluster.objects.get(id=cluster_id)
    immute_domain = cluster.immute_domain
    region = cluster.region
    bk_biz_id = cluster.bk_biz_id

    # 判断clb是否已经存在
    clb_entry = ClusterEntry.objects.filter(cluster_id=cluster_id, cluster_entry_type=ClusterEntryType.CLB.value)
    if len(clb_entry) > 0:
        message = "clb of cluster:{} has existed".format(immute_domain)
        return response_fail(code=3, message=message)

    # 获取端口号
    masters = StorageInstance.objects.filter(cluster=cluster, instance_role=InstanceRole.ES_MASTER)
    if not masters:
        message = f"the cluster({cluster_id}, {cluster.name}) has no master node"
        return response_fail(code=3, message=message)
    http_port = masters.first().port
    ips = get_access_ips_from_dns(bk_cloud_id=cluster.bk_cloud_id, bk_biz_id=bk_biz_id, domain=immute_domain)
    access_instances = [f"{ip}:{http_port}" for ip in ips]

    # 通过bk_biz_id获取manager，backupmanager，去除admin
    users = DBAdministrator().get_biz_db_type_admins(bk_biz_id=bk_biz_id, db_type=DBType.Es.value)
    users = [user for user in users if user != "admin"]
    manager = users[0]
    backupmanager = users[1] if len(users) > 1 else users[0]

    # 进行请求，得到返回结果
    output = NameServiceApi.clb_create_lb_and_register_target(
        {
            "region": region,
            "loadbalancername": immute_domain,
            "listenername": immute_domain,
            "manager": manager,
            "backupmanager": backupmanager,
            "protocol": "TCP",
            "ips": access_instances,
        },
        raw=True,
    )
    return output


def add_clb_info_to_meta(output: Dict[str, Any], cluster_id: int, creator: str) -> Dict[str, Any]:
    """clb信息写入meta"""

    # 获取信息
    cluster = Cluster.objects.get(id=cluster_id)

    # 进行判断请求结果,请求结果正确，写入数据库
    if (
        output["code"] == 0
        and not cluster.clusterentry_set.filter(cluster_entry_type=ClusterEntryType.CLB.value).exists()
    ):
        clb_ip = output["data"]["loadbalancerip"]
        try:
            api.entry.clb.es_create(
                domain=cluster.immute_domain,
                clb_ip=clb_ip,
                clb_id=output["data"]["loadbalancerid"],
                clb_listener_id=output["data"]["listenerid"],
                clb_region=cluster.region,
                creator=creator,
            )
            return response_ok()
        except Exception as e:
            message = "add clb info to meta fail, error:{}".format(str(e))
            return response_fail(code=3, message=message)
    else:
        message = "add clb info to meta fail, output code={} error or clb_entry is exist".format(output["code"])
        return response_fail(code=3, message=message)


def delete_clb_info_from_meta(output: Dict[str, Any], cluster_id: int) -> Dict[str, Any]:
    """在meta中删除clb信息"""

    # 获取信息
    cluster = Cluster.objects.get(id=cluster_id)
    cluster_clb_entry = cluster.clusterentry_set.filter(cluster_entry_type=ClusterEntryType.CLB.CLB).first()
    # 进行判断请求结果，如果为0操作删除db数据
    if output["code"] == 0 and cluster_clb_entry:
        load_balancer_id = cluster_clb_entry.clbentrydetail_set.first().clb_id
        try:
            cluster_clb_entry.clbentrydetail_set.all().delete()
            cluster.clusterentry_set.filter(cluster_entry_type=ClusterEntryType.CLB).delete()
        except Exception as e:
            message = "delete clb:{} info in db fail, error:{}".format(load_balancer_id, str(e))
            return response_fail(code=1, message=message)
    return response_ok()


def deregister_target_and_delete_lb(cluster_id: int) -> Dict[str, Any]:
    """解绑后端主机并删除clb"""

    # 获取集群信息
    cluster = Cluster.objects.get(id=cluster_id)
    immute_domain = cluster.immute_domain

    # 判断clb是否存在
    if not cluster.clusterentry_set.filter(cluster_entry_type=ClusterEntryType.CLB.value).exists():
        return {"code": 3, "message": "clb of cluster:%s does not exist, can not delete clb" % immute_domain}
    clb_entry = cluster.clusterentry_set.filter(cluster_entry_type=ClusterEntryType.CLB).first()
    clb_manager = get_clb_by_ip(clb_ip=clb_entry.entry)
    # 进行请求，得到返回结果
    output = NameServiceApi.clb_deregister_target_and_del_lb(
        {
            "region": clb_manager.clb_region,
            "loadbalancerid": clb_manager.clb_id,
            "listenerid": clb_manager.listener_id,
        },
        raw=True,
    )
    return output


def immute_domain_forward_to_clb_ip(cluster_id: int, creator: str, bind: bool) -> Dict[str, Any]:
    """主域名指向clb ip或者解绑"""

    # 获取集群信息
    cluster = Cluster.objects.get(id=cluster_id)
    immute_domain = cluster.immute_domain
    bk_cloud_id = cluster.bk_cloud_id
    bk_biz_id = cluster.bk_biz_id
    if not cluster.clusterentry_set.filter(cluster_entry_type=ClusterEntryType.CLB.value):
        message = "clb of cluster:{} does not exist, can not bind or unbind clb ip".format(immute_domain)
        return response_fail(code=3, message=message)

    clb_entry = cluster.clusterentry_set.filter(cluster_entry_type=ClusterEntryType.CLB.value).first()
    clb_ip = clb_entry.entry
    # 获取端口号
    masters = StorageInstance.objects.filter(cluster=cluster, instance_role=InstanceRole.ES_MASTER.value)
    if not masters:
        message = f"the cluster({cluster_id}, {cluster.name}) has no master node"
        return response_fail(code=3, message=message)
    port = masters.first().port

    clb_ip_port = "{}#{}".format(clb_ip, str(port))

    if bind:
        if not is_es_domain_bind_clb(immute_domain=immute_domain, bk_cloud_id=bk_cloud_id):
            # 添加dns：主域名指向clb ip
            flag = is_ip_in_dns(bk_biz_id=bk_biz_id, bk_cloud_id=bk_cloud_id, domain=immute_domain, ip=clb_ip)
            if not flag:
                create_dns_result = dns_manage.DnsManage(bk_biz_id=bk_biz_id, bk_cloud_id=bk_cloud_id).create_domain(
                    instance_list=[clb_ip_port], add_domain_name=immute_domain
                )
                if not create_dns_result:
                    message = "add immute domain with clb ip to dns fail"
                    return response_fail(code=3, message=message)

            # 删除老的dns：主域名指向接入节点
            dns_ips = get_access_ips_from_dns(bk_cloud_id=bk_cloud_id, bk_biz_id=bk_biz_id, domain=immute_domain)
            delete_dns_list = [f"{ip}#{str(port)}" for ip in dns_ips if ip != clb_ip]
            if delete_dns_list:
                dns_remove_status = dns_manage.DnsManage(
                    bk_biz_id=bk_biz_id, bk_cloud_id=bk_cloud_id
                ).remove_domain_ip(domain=immute_domain, del_instance_list=delete_dns_list)
                if not dns_remove_status:
                    message = "delete immute domain with access ip from dns fail"
                    return response_fail(code=3, message=message)
            # 修改元数据
            try:
                mdy_dbmeta_for_es_domain_bind_clb(
                    immute_domain=immute_domain,
                    bk_cloud_id=bk_cloud_id,
                    created_by=creator,
                )
            except Exception as e:
                message = "change meta data about immute domain bind clb ip fail, error:{}".format(str(e))
                return response_fail(code=3, message=message)
            return response_ok()
        message = "immute domain has bound clb ip"
        return response_fail(code=3, message=message)
    # 主域名解绑clb ip
    if is_es_domain_bind_clb(immute_domain=immute_domain, bk_cloud_id=bk_cloud_id):
        # 添加dns：主域名指向接入节点
        add_ips = get_access_ips_from_dbmeta(cluster_id=cluster_id)
        add_instances = [f"{ip}#{str(port)}" for ip in add_ips]
        if add_instances:
            dns_create_result = dns_manage.DnsManage(bk_biz_id=bk_biz_id, bk_cloud_id=bk_cloud_id).create_domain(
                instance_list=add_instances, add_domain_name=immute_domain
            )
            if not dns_create_result:
                message = "add immute domain with proxy ip from dns fail"
                return response_fail(code=3, message=message)

        # 删除clb ip
        dns_status_result = is_ip_in_dns(bk_biz_id=bk_biz_id, bk_cloud_id=bk_cloud_id, domain=immute_domain, ip=clb_ip)
        if dns_status_result:
            dns_remove_status = dns_manage.DnsManage(bk_biz_id=bk_biz_id, bk_cloud_id=bk_cloud_id).remove_domain_ip(
                immute_domain, [clb_ip_port]
            )
            if not dns_remove_status:
                message = "delete immute domain with clb ip from dns fail"
                return response_fail(code=3, message=message)
        # 修改元数据
        try:
            mdy_dbmeta_for_es_domain_unbind_clb(
                immute_domain=immute_domain,
                bk_cloud_id=bk_cloud_id,
                created_by=creator,
            )
        except Exception as e:
            message = "change meta data about immute domain unbind clb ip fail, error:{}".format(str(e))
            return response_fail(code=3, message=message)
        return response_ok()
    return response_ok()


def add_clb_domain_to_dns(cluster_id: int, creator: str) -> Dict[str, Any]:
    """添加clb域名到dns"""
    # 获取信息
    cluster = Cluster.objects.get(id=cluster_id)
    clb_entry = cluster.clusterentry_set.filter(cluster_entry_type=ClusterEntryType.CLB).first()
    immute_domain = cluster.immute_domain

    # 获取端口号
    masters = StorageInstance.objects.filter(cluster=cluster, instance_role=InstanceRole.ES_MASTER)
    if not masters:
        message = f"the cluster({cluster_id}, {cluster.name}) has no master node"
        return response_fail(code=3, message=message)
    port = masters.first().port

    bk_cloud_id = cluster.bk_cloud_id
    bk_biz_id = cluster.bk_biz_id
    clb_ip = clb_entry.entry
    # 添加clb域名以及dns
    if CLB_DOMAIN:
        # 添加clb域名dns
        if not get_dns_status_by_domain(
            bk_biz_id=bk_biz_id, bk_cloud_id=bk_cloud_id, domain="clb.{}".format(immute_domain)
        ):
            result = dns_manage.DnsManage(bk_biz_id=bk_biz_id, bk_cloud_id=bk_cloud_id).create_domain(
                instance_list=["{}#{}".format(clb_ip, str(port))], add_domain_name="clb.{}".format(immute_domain)
            )
            if not result:
                return {"code": 3, "message": "add clb domain to dns fail"}
        try:
            if not cluster.clusterentry_set.filter(cluster_entry_type=ClusterEntryType.CLBDNS.value).exists():
                clb = cluster.clusterentry_set.filter(cluster_entry_type=ClusterEntryType.CLB.value).first()
                ClusterEntry.objects.create(
                    cluster_id=cluster.id,
                    cluster_entry_type=ClusterEntryType.CLBDNS,
                    entry="clb.{}".format(cluster.immute_domain),
                    creator=creator,
                    forward_to_id=clb.id,
                )
        except Exception as e:
            message = "cluster:{} add clb domain fail, error:{}".format(immute_domain, str(e))
            return response_fail(code=3, message=message)
    return response_ok()


def delete_clb_domain_from_dns(cluster_id: int) -> Dict[str, Any]:
    """从dns中删除clb域名"""
    cluster = Cluster.objects.get(id=cluster_id)
    bk_cloud_id = cluster.bk_cloud_id
    bk_biz_id = cluster.bk_biz_id

    clb_dns_entries = cluster.clusterentry_set.filter(cluster_entry_type=ClusterEntryType.CLBDNS)
    clb_ip = cluster.clusterentry_set.filter(cluster_entry_type=ClusterEntryType.CLB).first().entry

    # 获取端口号
    masters = StorageInstance.objects.filter(cluster=cluster, instance_role=InstanceRole.ES_MASTER)
    if not masters:
        message = f"the cluster({cluster_id}, {cluster.name}) has no master node"
        return response_fail(code=3, message=message)
    port = masters.first().port

    # 如果存在clb域名指向clb ip，则删除
    if clb_dns_entries.exists():
        # 删除dns：clb域名绑定clb ip
        clb_dns = clb_dns_entries.first().entry
        if get_dns_status_by_domain(bk_biz_id=bk_biz_id, bk_cloud_id=bk_cloud_id, domain=clb_dns):
            result = dns_manage.DnsManage(bk_biz_id=bk_biz_id, bk_cloud_id=bk_cloud_id).remove_domain_ip(
                domain=clb_dns, del_instance_list=["{}#{}".format(clb_ip, str(port))]
            )
            if not result:
                message = "delete {} dns info fail".format(clb_dns)
                return response_fail(code=1, message=message)
        # 删除元数据clbDns信息
        try:
            clb_dns_entries.delete()
        except Exception as e:
            message = "delete clb domain {} fail, error:{}".format(clb_dns, str(e))
            return response_fail(code=1, message=message)
    return response_ok()


def operate_part_target(cluster_id: int, ips: list, bind: bool) -> dict:
    """绑定或解绑部分后端主机"""
    # TODO: 加下数据校验

    # 获取信息
    cluster = Cluster.objects.get(cluster_id=cluster_id)
    clb_entry = cluster.clusterentry_set.filter(cluster_entry_type=ClusterEntryType.CLB).first()

    # 获取端口号
    masters = StorageInstance.objects.filter(cluster=cluster, instance_role=InstanceRole.ES_MASTER)
    if not masters:
        message = f"the cluster({cluster_id}, {cluster.name}) has no master node"
        return response_fail(code=3, message=message)
    http_port = masters.first().port
    instance_list = [f"{ip}:{http_port}" for ip in ips]

    clb_manager = get_clb_by_ip(clb_ip=clb_entry.entry)
    # 进行请求，得到返回结果
    if bind:
        if not clb_manager.add_clb_rs(instance_list=instance_list):
            response_fail(code=3, message="clb bind rs failed")
    else:
        if not clb_manager.del_clb_rs(instance_list=instance_list):
            response_fail(code=3, message="clb unbind rs failed")
    return response_ok()
