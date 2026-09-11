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
import datetime
import logging
from typing import Optional, Union

from django.utils import timezone
from django.utils.crypto import get_random_string
from django.utils.translation import gettext as _

from backend import env
from backend.configuration.constants import DBType
from backend.configuration.models.dba import DBAdministrator
from backend.core import notify
from backend.db_meta.models import Cluster, Machine, StorageInstance
from backend.db_services.dbbase.constants import IpSource
from backend.db_services.mongodb.autofix.enums import MongoAutofixStatus
from backend.db_services.mongodb.autofix.models import MongoAutofixCore
from backend.db_services.mongodb.autofix.remark import autofix_core_tag
from backend.db_services.redis.autofix.enums import AutofixStatus
from backend.db_services.redis.autofix.models import RedisAutofixCore
from backend.ticket.builders.common.constants import OperaObjType
from backend.ticket.constants import TicketType
from backend.ticket.models import Ticket
from backend.utils.time import datetime2str

logger = logging.getLogger("root")


def _autofix_followup_remark(prefix: str, core: MongoAutofixCore) -> str:
    """自愈后续单备注：前缀 + 域名 + 自愈#id + 可选来自 PRE 单据。"""
    base = "{}-{}{}".format(prefix, core.immute_domain, autofix_core_tag(core.id))
    if core.pre_ticket_id and core.pre_ticket_id > 0:
        return _("{}-来自单据#{}".format(base, core.pre_ticket_id))
    return _(base)


def mongos_get_resource_spec(cluster_id: int, mongos_list: list) -> dict:
    """获取申请机器规格信息，mongos申请机器，判断如果一半机器在同一园区，则排除该园区，否则任意园区"""

    include_or_exclue = True
    sub_zone_ids = []
    # 获取mongos的机器
    all_mongos = Cluster.objects.get(id=cluster_id).proxyinstance_set.all()
    # 获取健康mongos机器在园区的比重 {sub_zone_id: number}
    health_mongos_number = len(all_mongos) - len(mongos_list)  # 所有健康mongos的数量
    health_mongos_sub_zone = {}  # 健康mongos在每个园区的数量
    for mongos in all_mongos:
        if mongos.machine.ip in [host["ip"] for host in mongos_list]:
            continue
        if not health_mongos_sub_zone.get(str(mongos.machine.bk_sub_zone_id)):
            health_mongos_sub_zone[str(mongos.machine.bk_sub_zone_id)] = 0
        health_mongos_sub_zone[str(mongos.machine.bk_sub_zone_id)] += 1
    #  健康mongos在每个园区的机器数量占所有健康mongos的数量的百分比
    if health_mongos_number > 0:
        mongos_sub_zone_percent = {
            sub_zone: num / health_mongos_number for sub_zone, num in health_mongos_sub_zone.items()
        }
        for sub_zone, sub_zone_percent in mongos_sub_zone_percent.items():
            if sub_zone_percent >= 0.5:
                include_or_exclue = False
                sub_zone_ids.append(int(sub_zone))
                break

    resource_spec = {}
    for host in mongos_list:
        effective_sub_zone_ids = [z for z in sub_zone_ids if z]
        effective_include = include_or_exclue if effective_sub_zone_ids else True
        resource_spec.update(
            {
                host["ip"]: {
                    "spec_id": host["spec_id"],
                    "count": 1,
                    "spec_config": host["spec_config"],
                    "location_spec": {
                        "city": host["city"],
                        "sub_zone_ids": effective_sub_zone_ids,
                        "include_or_exclue": effective_include,
                    },
                    "labels": host.get("labels") or [],
                    "label_names": host.get("label_names") or [],
                }
            }
        )
    return resource_spec


def mongod_get_resource_spec(cluster_id: int, mongod_list: list) -> dict:
    """获取申请机器规格信息：优先同城；健康存储实例若某园区占比 >=50% 则排除该园区。"""

    include_or_exclue = True
    sub_zone_ids = []
    all_mongod = Cluster.objects.get(id=cluster_id).storageinstance_set.select_related("machine").all()
    fault_ips = {host["ip"] for host in mongod_list}
    health_mongod_sub_zone = {}
    health_mongod_number = 0
    for inst in all_mongod:
        if inst.machine.ip in fault_ips:
            continue
        health_mongod_number += 1
        zone_key = str(inst.machine.bk_sub_zone_id)
        health_mongod_sub_zone[zone_key] = health_mongod_sub_zone.get(zone_key, 0) + 1

    if health_mongod_number > 0:
        mongod_sub_zone_percent = {
            sub_zone: num / health_mongod_number for sub_zone, num in health_mongod_sub_zone.items()
        }
        for sub_zone, sub_zone_percent in mongod_sub_zone_percent.items():
            if sub_zone_percent >= 0.5:
                include_or_exclue = False
                sub_zone_ids.append(int(sub_zone))
                break

    resource_spec = {}
    for host in mongod_list:
        # 园区 id 为 0/空 表示未打园区，排除无意义且会导致本地资源池申请不到机
        effective_sub_zone_ids = [z for z in sub_zone_ids if z]
        effective_include = include_or_exclue if effective_sub_zone_ids else True
        resource_spec[host["ip"]] = {
            "spec_id": host["spec_id"],
            "count": 1,
            "spec_config": host["spec_config"],
            "location_spec": {
                "city": host["city"],
                "sub_zone_ids": effective_sub_zone_ids,
                "include_or_exclue": effective_include,
            },
            # 与部署/替换单据一致：有标签的资源池必须带 labels，否则只会匹配无标签主机
            "labels": host.get("labels") or [],
            "label_names": host.get("label_names") or [],
        }
    return resource_spec


def build_mongod_list_from_core(core: MongoAutofixCore) -> list:
    """从 MongoAutofixCore 组装 mongod_list（供 MONGODB_AUTOFIX 申请资源）。"""
    machine = None
    if core.bk_host_id:
        machine = Machine.objects.filter(bk_host_id=core.bk_host_id).first()
    if not machine:
        machine = Machine.objects.filter(ip=core.ip, bk_biz_id=core.bk_biz_id).first()
    if not machine:
        raise Machine.DoesNotExist(f"machine not found for autofix core ip={core.ip} host_id={core.bk_host_id}")

    city = core.bk_city
    try:
        if machine.bk_city_id and machine.bk_city and machine.bk_city.logical_city:
            city = machine.bk_city.logical_city.name
    except Exception:  # noqa: BLE001
        pass

    # 资源标签来自环境变量；正式默认空，本地冒烟在 local.env 配 cyc
    return [
        {
            "ip": machine.ip,
            "spec_id": machine.spec_id,
            "spec_config": machine.spec_config,
            "city": city,
            "cluster_type": core.cluster_type,
            "bk_host_id": machine.bk_host_id,
            "bk_sub_zone": machine.bk_sub_zone,
            "bk_sub_zone_id": machine.bk_sub_zone_id,
            "instance_type": machine.machine_type,
            "labels": list(env.MONGODB_AUTOFIX_RESOURCE_LABELS or []),
            "label_names": list(env.MONGODB_AUTOFIX_RESOURCE_LABEL_NAMES or []),
        }
    ]


def create_mongod_reload_ticket(core: MongoAutofixCore, creator: Optional[str] = None) -> Optional[Ticket]:
    """从 Core 组装并创建 MONGODB_INSTANCE_RELOAD 单据。"""
    if not creator:
        mongodb_dba = DBAdministrator.get_biz_db_type_admins(bk_biz_id=core.bk_biz_id, db_type=DBType.MongoDB.value)
        creator = mongodb_dba[0] if mongodb_dba else "admin"

    ports = core.ports or []
    # 整机多端口：MACHINE；单端口且能解析 instance_id：INSTANCE
    if len(ports) == 1:
        storage = (
            StorageInstance.objects.select_related("machine")
            .prefetch_related("cluster")
            .filter(machine__ip=core.ip, port=ports[0])
            .first()
        )
        if core.bk_host_id:
            storage = storage or (
                StorageInstance.objects.select_related("machine")
                .prefetch_related("cluster")
                .filter(machine__bk_host_id=core.bk_host_id, port=ports[0])
                .first()
            )
        if storage:
            cluster = storage.cluster.first()
            details = {
                "force": True,
                "target_select_mode": OperaObjType.INSTANCE.value,
                "infos": [
                    {
                        "cluster_id": cluster.id if cluster else core.cluster_id,
                        "bk_host_id": storage.machine.bk_host_id,
                        "ip": storage.machine.ip,
                        "instance_id": storage.id,
                        "port": storage.port,
                        "role": storage.machine_type,
                    }
                ],
            }
        else:
            details = {
                "force": True,
                "target_select_mode": OperaObjType.MACHINE.value,
                "infos": [{"bk_host_id": core.bk_host_id, "ip": core.ip, "ports": ports}],
            }
    else:
        details = {
            "force": True,
            "target_select_mode": OperaObjType.MACHINE.value,
            "infos": [{"bk_host_id": core.bk_host_id, "ip": core.ip, "ports": ports}],
        }

    # 自愈自动链路：跳过 ITSM / 人工确认，页面手工重启不受影响
    details["need_itsm"] = False
    details["need_manual_confirm"] = False

    remark = _autofix_followup_remark(_("自动发起-自愈修复重启"), core)

    ticket = Ticket.create_ticket(
        ticket_type=TicketType.MONGODB_INSTANCE_RELOAD.value,
        creator=creator,
        bk_biz_id=core.bk_biz_id,
        remark=remark,
        details=details,
    )
    notify.send_msg.apply_async(args=(ticket.id,))
    return ticket


def create_mongod_fix_status_ticket(core: MongoAutofixCore, creator: Optional[str] = None) -> Optional[Ticket]:
    """从 Core 组装并创建 MONGODB_INSTANCE_FIX_STATUS（探测成功后修元数据状态，不重启）。"""
    if not creator:
        mongodb_dba = DBAdministrator.get_biz_db_type_admins(bk_biz_id=core.bk_biz_id, db_type=DBType.MongoDB.value)
        creator = mongodb_dba[0] if mongodb_dba else "admin"

    ports = core.ports or []
    if not ports:
        logger.error("create_mongod_fix_status_ticket: empty ports core=%s", core.id)
        return None

    infos = []
    for port in ports:
        storage = (
            StorageInstance.objects.select_related("machine")
            .prefetch_related("cluster")
            .filter(machine__ip=core.ip, port=port)
            .first()
        )
        if core.bk_host_id:
            storage = storage or (
                StorageInstance.objects.select_related("machine")
                .prefetch_related("cluster")
                .filter(machine__bk_host_id=core.bk_host_id, port=port)
                .first()
            )
        if not storage:
            logger.error(
                "create_mongod_fix_status_ticket: storage missing ip=%s port=%s core=%s",
                core.ip,
                port,
                core.id,
            )
            return None
        cluster = storage.cluster.first()
        cluster_id = cluster.id if cluster else core.cluster_id
        master_domain = (cluster.immute_domain if cluster else None) or core.immute_domain
        infos.append(
            {
                "ip": storage.machine.ip,
                "port": storage.port,
                "bk_cloud_id": storage.machine.bk_cloud_id,
                "dry_run": False,
                "cluster_id": cluster_id,
                "instance_address": f"{storage.machine.ip}:{storage.port}",
                "master_domain": master_domain,
            }
        )

    details = {
        "infos": infos,
        # 自愈自动链路：跳过 ITSM / 人工确认
        "need_itsm": False,
        "need_manual_confirm": False,
    }

    remark = _autofix_followup_remark(_("自动发起-自愈状态修复"), core)

    ticket = Ticket.create_ticket(
        ticket_type=TicketType.MONGODB_INSTANCE_FIX_STATUS.value,
        creator=creator,
        bk_biz_id=core.bk_biz_id,
        remark=remark,
        details=details,
    )
    notify.send_msg.apply_async(args=(ticket.id,))
    return ticket


def mongo_create_ticket(
    cluster: Union[RedisAutofixCore, MongoAutofixCore],
    cluster_ids: list,
    mongos_list: list,
    mongod_list: list,
):
    """mongodb自愈创建单据 以cluster为维度。成功返回 Ticket，规格为空或失败返回 None。"""

    # 获取dba
    mongodb_dba = DBAdministrator.get_biz_db_type_admins(bk_biz_id=cluster.bk_biz_id, db_type=DBType.MongoDB.value)
    logger.info("mongodb autofix get dba:{}".format(mongodb_dba))

    # 申请机器规格信息
    resource_spec = {}
    cluster_type = ""

    # 集群类型
    if mongos_list:
        cluster_type = mongos_list[0]["cluster_type"]
        # mongos的资源规格
        mongos_resource_spec = mongos_get_resource_spec(cluster_ids[0], mongos_list)
        logger.info("mongodb autofix mongos resource_spec:{}".format(mongos_resource_spec))
        resource_spec.update(mongos_resource_spec)
    if mongod_list:
        cluster_type = mongod_list[0]["cluster_type"]
        mongod_resource_spec = mongod_get_resource_spec(cluster_ids[0], mongod_list)
        logger.info("mongodb autofix mongod resource_spec:{}".format(mongod_resource_spec))
        resource_spec.update(mongod_resource_spec)

    if not resource_spec:
        return None

    # 单据信息
    details = {
        "ip_source": IpSource.RESOURCE_POOL.value,
        "infos": [
            {
                "cluster_ids": cluster_ids,
                "immute_domain": cluster.immute_domain,
                "bk_cloud_id": cluster.bk_cloud_id,
                "bk_biz_id": cluster.bk_biz_id,
                "resource_spec": resource_spec,
                "cluster_type": cluster_type,
                "mongos_list": mongos_list,
                "mongod_list": mongod_list,
            }
        ],
    }
    logger.info("mongodb autofix ticket details:{}".format(details))

    core_tag = autofix_core_tag(getattr(cluster, "id", None)) if isinstance(cluster, MongoAutofixCore) else ""
    remark = _("自动发起-自愈任务-{}{}".format(cluster.immute_domain, core_tag))
    pre_ticket_id = getattr(cluster, "pre_ticket_id", None) or 0
    if pre_ticket_id > 0:
        remark = _("自动发起-自愈任务-{}{}-来自单据#{}".format(cluster.immute_domain, core_tag, pre_ticket_id))

    ticket = None
    # 创建单据
    try:
        ticket = Ticket.create_ticket(
            ticket_type=TicketType.MONGODB_AUTOFIX.value,
            creator=mongodb_dba[0],
            bk_biz_id=cluster.bk_biz_id,
            remark=remark,
            details=details,
        )

        # 发送自愈消息提醒
        notify.send_msg.apply_async(args=(ticket.id,))
        if isinstance(cluster, MongoAutofixCore):
            cluster.deal_status = MongoAutofixStatus.TICKETED.value
        else:
            cluster.deal_status = AutofixStatus.AF_WFLOW.value
        cluster.status_version = get_random_string(12)
    except Exception as e:
        if isinstance(cluster, MongoAutofixCore):
            cluster.deal_status = MongoAutofixStatus.FAIL.value
        else:
            cluster.deal_status = AutofixStatus.AF_FAIL.value
        cluster.status_version = str(e)
        logger.info("mongodb autofix create ticket fail:{}".format(e))

    # 回写自愈核心表
    if ticket:
        cluster.ticket_id = ticket.id
    update_fields = ["ticket_id", "status_version", "deal_status"]
    if not isinstance(cluster, MongoAutofixCore):
        # RedisAutofixCore 历史逻辑用字符串时间
        cluster.update_at = datetime2str(datetime.datetime.now(timezone.utc))
        update_fields.append("update_at")
    cluster.save(update_fields=update_fields)
    return ticket
