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
import logging
import traceback
from datetime import datetime

from django.db import transaction
from django.utils.translation import gettext as _

from backend.db_meta import api
from backend.db_meta.api import machine, storage_instance
from backend.db_meta.enums import ClusterEntryRole, ClusterEntryType, InstanceRole, MachineType
from backend.db_meta.enums.cluster_type import ClusterType
from backend.db_meta.models import Cluster, ClusterEntry, Machine, StorageInstance, StorageInstanceTuple

from . import change_password

logger = logging.getLogger("flow")


def _create_new_node(old_instance: StorageInstance, new_ip: str, new_port: int, bk_biz_id: int, bk_cloud_id: int):
    """辅助函数：复用旧实例规格创建或获取新机器和新实例"""
    old_machine = old_instance.machine

    # 创建或获取新机器
    new_machine = Machine.objects.filter(ip=new_ip, bk_cloud_id=bk_cloud_id).first()
    if not new_machine:
        machine.create(
            machines=[
                {
                    "ip": new_ip,
                    "bk_cloud_id": bk_cloud_id,
                    "bk_biz_id": bk_biz_id,
                    "machine_type": old_machine.machine_type,
                    "spec_id": old_machine.spec_id,
                    "spec_config": old_machine.spec_config,
                }
            ],
            bk_cloud_id=bk_cloud_id,
        )
        new_machine = Machine.objects.filter(ip=new_ip, bk_cloud_id=bk_cloud_id).first()
        new_machine.cluster_type = old_machine.cluster_type
        new_machine.save()

    logger.info(_("创建新机器: {}, 机器ID: {}, 规格ID: {}").format(new_ip, new_machine.bk_host_id, old_machine.spec_id))

    # 创建或获取新实例
    new_instance = StorageInstance.objects.filter(machine=new_machine, port=new_port, bk_biz_id=bk_biz_id).first()
    if not new_instance:
        storage_instance.create(
            instances=[
                {
                    "ip": new_ip,
                    "port": new_port,
                    "instance_role": old_instance.instance_role,
                    "name": old_instance.name,
                }
            ]
        )
        new_instance = StorageInstance.objects.filter(machine=new_machine, port=new_port, bk_biz_id=bk_biz_id).first()

    logger.info(
        _("创建新实例: {}:{}, 实例ID: {}, 角色: {}").format(new_ip, new_port, new_instance.id, old_instance.instance_role)
    )
    return new_machine, new_instance


@transaction.atomic
def replace_instance(
    cluster_id: int,
    new_instance_ip: str,
    new_instance_port: int,
    old_instance_ip: str,
    old_instance_port: int,
    bk_biz_id: int,
):
    """
    用新的 IP/Port 替换 Oracle 主备集群中的单个 Primary 或 Standby 节点。

    Args:
        cluster_id: 集群 ID
        new_instance_ip: 新实例的 IP 地址
        new_instance_port: 新实例的端口号
        old_instance_ip: 旧实例的 IP 地址
        old_instance_port: 旧实例的端口号
        bk_biz_id: 业务 ID
    """
    try:
        cluster = Cluster.objects.get(id=cluster_id, bk_biz_id=bk_biz_id)
        if cluster.cluster_type != ClusterType.OraclePrimaryStandby.value:
            raise ValueError(_("集群类型不是Oracle主备集群，是{}").format(cluster.cluster_type))
        bk_cloud_id = cluster.bk_cloud_id

        old_instance = cluster.storageinstance_set.get(machine__ip=old_instance_ip, port=old_instance_port)
        old_machine = old_instance.machine
        old_role = old_instance.instance_role
        logger.info(
            _("找到旧实例: {}:{}, 实例ID: {}, 角色: {}").format(old_instance_ip, old_instance_port, old_instance.id, old_role)
        )

        new_machine, new_instance = _create_new_node(
            old_instance, new_instance_ip, new_instance_port, bk_biz_id, bk_cloud_id
        )
        logger.info(_("成功创建新实例: {}:{}, 实例ID: {}").format(new_instance_ip, new_instance_port, new_instance.id))

        date = datetime.now()
        if old_role == InstanceRole.PRIMARY.value:
            updated_count = StorageInstanceTuple.objects.filter(ejector=old_instance).update(
                ejector=new_instance, update_at=date
            )
            logger.info(_("更新StorageInstanceTuple: 将发送者从旧实例切换到新实例，更新记录数: {}").format(updated_count))
        elif old_role == InstanceRole.STANDBY.value:
            updated_count = StorageInstanceTuple.objects.filter(receiver=old_instance).update(
                receiver=new_instance, update_at=date
            )
            logger.info(_("更新StorageInstanceTuple: 将接收者从旧实例切换到新实例，更新记录数: {}").format(updated_count))

        target_role = (
            ClusterEntryRole.MASTER_ENTRY.value
            if old_role == InstanceRole.PRIMARY.value
            else ClusterEntryRole.SLAVE_ENTRY.value
        )
        entries = ClusterEntry.objects.filter(
            cluster=cluster, cluster_entry_type=ClusterEntryType.DNS, role=target_role
        )
        entry_update_count = 0
        for entry in entries:
            if entry.storageinstance_set.filter(id=old_instance.id).exists():
                entry.storageinstance_set.remove(old_instance)
                entry.storageinstance_set.add(new_instance)
                entry_update_count += 1
                logger.info(_("更新DNS绑定: Entry={}, 从旧实例切换到新实例").format(entry.entry))
        logger.info(_("共更新DNS绑定条目数: {}").format(entry_update_count))

        cluster.storageinstance_set.remove(old_instance)
        cluster.storageinstance_set.add(new_instance)
        cluster.save()
        logger.info(_("更新集群实例集合: 移除旧实例，添加新实例"))

        old_instance.delete()
        logger.info(_("删除旧实例: {}:{}").format(old_instance_ip, old_instance_port))

        if not StorageInstance.objects.filter(machine=old_machine).exists():
            old_machine.delete()
            logger.info(_("删除旧机器: {}").format(old_instance_ip))
        else:
            logger.info(_("保留旧机器: {}, 因为还有其他实例存在").format(old_instance_ip))

        change_password.ip_change_password(
            old_instance_ip, old_instance_port, new_instance_ip, new_instance_port, bk_cloud_id
        )
        logger.info(
            _("执行密码修改操作: 从{}:{}到{}:{}").format(old_instance_ip, old_instance_port, new_instance_ip, new_instance_port)
        )

        logger.info(_("Oracle实例替换完成: 集群ID={}, 新实例={}:{}").format(cluster_id, new_instance_ip, new_instance_port))
    except Exception as e:
        logger.error(traceback.format_exc())
        raise Exception("oracle replace instance failed: {}".format(e))


@transaction.atomic
def replace_primary_and_standby(
    cluster_id: int,
    new_primary_ip: str,
    new_primary_port: int,
    new_standby_ip: str,
    new_standby_port: int,
    bk_biz_id: int,
):
    """
    同时用新的 IP/Port 替换 Oracle 主备集群中的 Primary 和 Standby 节点。

    Args:
        cluster_id: 集群 ID
        new_primary_ip: 新 Primary IP
        new_primary_port: 新 Primary 端口
        new_standby_ip: 新 Standby IP
        new_standby_port: 新 Standby 端口
        bk_biz_id: 业务 ID
    """
    try:
        # ── 1. 找集群 & 旧主备实例 ─────────────────────────────────
        cluster = Cluster.objects.get(id=cluster_id, bk_biz_id=bk_biz_id)
        if cluster.cluster_type != ClusterType.OraclePrimaryStandby.value:
            raise ValueError(_("集群类型不是Oracle主备集群，是{}").format(cluster.cluster_type))
        bk_cloud_id = cluster.bk_cloud_id
        logger.info(_("找到集群: {}, 业务ID: {}, 云区域ID: {}").format(cluster.name, bk_biz_id, bk_cloud_id))

        old_primary = cluster.storageinstance_set.get(instance_role=InstanceRole.PRIMARY.value)
        old_standby = cluster.storageinstance_set.get(instance_role=InstanceRole.STANDBY.value)

        logger.info(
            _("找到旧主备: Primary({}:{}), Standby({}:{})").format(
                old_primary.machine.ip, old_primary.port, old_standby.machine.ip, old_standby.port
            )
        )

        # ── 2. 创建新机器和新实例 ────────────────────────────────
        new_primary_machine, new_primary = _create_new_node(
            old_primary, new_primary_ip, new_primary_port, bk_biz_id, bk_cloud_id
        )
        logger.info(_("成功创建新Primary实例: {}:{}, 实例ID: {}").format(new_primary_ip, new_primary_port, new_primary.id))
        new_standby_machine, new_standby = _create_new_node(
            old_standby, new_standby_ip, new_standby_port, bk_biz_id, bk_cloud_id
        )
        logger.info(_("成功创建新Standby实例: {}:{}, 实例ID: {}").format(new_standby_ip, new_standby_port, new_standby.id))

        # ── 3. 修改 StorageInstanceTuple ──────────────────────────────────────
        date = datetime.now()
        StorageInstanceTuple.objects.filter(
            ejector=old_primary,
            receiver=old_standby,
        ).update(ejector=new_primary, receiver=new_standby, update_at=date)
        logger.info(
            _("更新StorageInstanceTuple: 将发送者/接收者同时更新为新Primary<{}:{}>和新Standby<{}:{}>").format(
                new_primary_ip, new_primary_port, new_standby_ip, new_standby_port
            )
        )

        # ── 4. 更新 ClusterEntry DNS 绑定 ─────────────────────────────────────
        # 更新 Master DNS
        master_entries = ClusterEntry.objects.filter(
            cluster=cluster,
            cluster_entry_type=ClusterEntryType.DNS,
            role=ClusterEntryRole.MASTER_ENTRY.value,
        )
        for entry in master_entries:
            if entry.storageinstance_set.filter(id=old_primary.id).exists():
                entry.storageinstance_set.remove(old_primary)
                entry.storageinstance_set.add(new_primary)
                logger.info(_("更新Master DNS绑定: 切换到新Primary, Entry: {}").format(entry.entry))

        # 更新 Slave DNS
        slave_entries = ClusterEntry.objects.filter(
            cluster=cluster,
            cluster_entry_type=ClusterEntryType.DNS,
            role=ClusterEntryRole.SLAVE_ENTRY.value,
        )
        for entry in slave_entries:
            if entry.storageinstance_set.filter(id=old_standby.id).exists():
                entry.storageinstance_set.remove(old_standby)
                entry.storageinstance_set.add(new_standby)
                logger.info(_("更新Slave DNS绑定: 切换到新Standby, Entry: {}").format(entry.entry))

        # ── 5. 更新 Cluster.storageinstance_set ──────────────────────────────
        cluster.storageinstance_set.remove(old_primary, old_standby)
        cluster.storageinstance_set.add(new_primary, new_standby)
        cluster.save()
        logger.info(_("更新集群实例集合: 移除旧主备, 添加新主备"))

        # ── 6. 清理旧实例 & 旧机器 ────────────────────────────────────────────
        old_primary_ip, old_primary_port = old_primary.machine.ip, old_primary.port
        old_primary_machine = old_primary.machine
        old_primary.delete()
        logger.info(_("删除旧Primary实例: {}:{}").format(old_primary_ip, old_primary_port))
        if not StorageInstance.objects.filter(machine=old_primary_machine).exists():
            old_primary_machine.delete()
            logger.info(_("删除旧Primary机器: {}").format(old_primary_machine.ip))
        old_standby_ip, old_standby_port = old_standby.machine.ip, old_standby.port
        old_standby_machine = old_standby.machine
        old_standby.delete()
        logger.info(_("删除旧Standby实例: {}:{}").format(old_standby_ip, old_standby_port))
        if not StorageInstance.objects.filter(machine=old_standby_machine).exists():
            old_standby_machine.delete()
            logger.info(_("删除旧Standby机器: {}").format(old_standby_machine.ip))

        logger.info(
            _("Oracle主备同时替换完成，集群ID: {}, 新Primary: {}:{}, 新Standby: {}:{}").format(
                cluster_id, new_primary_ip, new_primary_port, new_standby_ip, new_standby_port
            )
        )

        # ── 7. 密码修改 ────────────────────────────
        change_password.ip_change_password(
            old_primary_ip, old_primary_port, new_primary_ip, new_primary_port, bk_cloud_id
        )
        logger.info(
            _("执行密码修改操作: 从{}:{}到{}:{}").format(old_primary_ip, old_primary_port, new_primary_ip, new_primary_port)
        )
        change_password.ip_change_password(
            old_standby_ip, old_standby_port, new_standby_ip, new_standby_port, bk_cloud_id
        )
        logger.info(
            _("执行密码修改操作: 从{}:{}到{}:{}").format(old_standby_ip, old_standby_port, new_standby_ip, new_standby_port)
        )
    except Exception as e:
        logger.error(traceback.format_exc())
        raise Exception("oracle replace primary and standby failed: {}".format(e))


@transaction.atomic
def new_machine(
    bk_cloud_id: int,
    bk_biz_id: int,
    ip: str,
    resource_spec: dict,
    creator: str,
    cluster_type: str,
):
    # 录入新机器的machine信息
    new_machine = Machine.objects.filter(ip=ip, bk_cloud_id=bk_cloud_id).first()
    if not new_machine:
        api.machine.create(
            machines=[
                {
                    "ip": ip,
                    "bk_biz_id": int(bk_biz_id),
                    "machine_type": MachineType.ORACLE.value,
                    "spec_id": resource_spec[MachineType.ORACLE.value]["id"],
                    "spec_config": resource_spec[MachineType.ORACLE.value],
                },
            ],
            creator=creator,
            bk_cloud_id=bk_cloud_id,
        )
        new_machine = Machine.objects.filter(ip=ip, bk_cloud_id=bk_cloud_id).first()
        new_machine.cluster_type = cluster_type
        new_machine.save()
        logger.info(_("创建新机器: host:{} cluster_type:{}").format(ip, cluster_type))
