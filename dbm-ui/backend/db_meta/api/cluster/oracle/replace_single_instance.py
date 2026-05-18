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

from django.db import transaction
from django.utils.translation import gettext as _

from backend.db_meta.api import machine, storage_instance
from backend.db_meta.enums import ClusterEntryRole, ClusterEntryType, InstanceRole
from backend.db_meta.enums.cluster_type import ClusterType
from backend.db_meta.models import Cluster, ClusterEntry, Machine, StorageInstance

from . import change_password

logger = logging.getLogger("flow")


@transaction.atomic
def replace_single_instance(
    cluster_id: int,
    new_ip: str,
    new_port: int,
    bk_biz_id: int,
):
    """
    Oracle 单实例机器替换（ClusterType.OracleSingleNone）。

    将集群中唯一的 PRIMARY 实例迁移到新机器/新端口，包括：
      1. 查找集群及旧 PRIMARY 实例
      2. 创建新 Machine（复用旧机器规格）
      3. 创建新 StorageInstance（复用旧实例的 service_name / instance_role）
      4. 更新 ClusterEntry DNS 绑定（MASTER_ENTRY）
      5. 更新 Cluster.storageinstance_set
      6. 清理旧 StorageInstance 与旧 Machine（若无其他实例引用）

    Args:
        cluster_id (int): 集群 ID
        new_ip (str): 新机器 IP
        new_port (int): 新实例端口（通常与旧端口相同，但允许变更）
        bk_biz_id (int): 业务 ID
    """
    try:
        # ── 1. 找集群 & 旧 PRIMARY 实例 ───────────────────────────────────────
        cluster = Cluster.objects.get(id=cluster_id, bk_biz_id=bk_biz_id)
        if cluster.cluster_type != ClusterType.OracleSingleNone.value:
            raise ValueError(_("集群类型不是Oracle单实例集群，是{}").format(cluster.cluster_type))

        bk_cloud_id = cluster.bk_cloud_id
        logger.info(_("找到集群: {}, 业务ID: {}, 云区域ID: {}").format(cluster.name, bk_biz_id, bk_cloud_id))

        old_instance = cluster.storageinstance_set.get(instance_role=InstanceRole.PRIMARY.value)
        old_machine = old_instance.machine
        old_ip = old_machine.ip
        old_port = old_instance.port
        old_machine_cluster_type = old_machine.cluster_type
        logger.info(
            _("找到旧PRIMARY实例: {}:{}, 机器ID: {}, ServiceName: {}").format(
                old_ip, old_port, old_machine.bk_host_id, old_instance.name
            )
        )

        # 幂等检查：若新实例已与集群绑定则直接返回
        if cluster.storageinstance_set.filter(
            machine__ip=new_ip, port=new_port, machine__bk_cloud_id=bk_cloud_id
        ).exists():
            logger.info(_("新实例 {}:{} 已存在于集群 {} 中，跳过替换").format(new_ip, new_port, cluster_id))
            return

        # ── 2. 创建新 Machine ───────────────────────────────────────
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
            new_machine = Machine.objects.get(ip=new_ip, bk_cloud_id=bk_cloud_id)
            # 为新机器设置 cluster_type
            new_machine.cluster_type = old_machine_cluster_type
            new_machine.save()
            logger.info(_("创建新机器: {}, 机器ID: {}, 规格ID: {}").format(new_ip, new_machine.bk_host_id, old_machine.spec_id))
        else:
            raise ValueError(_("机器: {}已被使用, 机器ID: {}，请检查").format(new_ip, new_machine.bk_host_id))

        # ── 3. 创建新 StorageInstance ───────────────────────────────
        new_instance = StorageInstance.objects.filter(machine=new_machine, port=new_port, bk_biz_id=bk_biz_id).first()
        if not new_instance:
            storage_instance.create(
                instances=[
                    {
                        "ip": new_ip,
                        "port": new_port,
                        "instance_role": old_instance.instance_role,
                        # 复用旧实例的 service_name（Oracle SID/服务名不随机器变更）
                        "name": old_instance.name,
                    }
                ]
            )
            new_instance = StorageInstance.objects.get(machine=new_machine, port=new_port, bk_biz_id=bk_biz_id)
            logger.info(
                _("创建新PRIMARY实例: {}:{}, 实例ID: {}, ServiceName: {}").format(
                    new_ip, new_port, new_instance.id, new_instance.name
                )
            )
        else:
            logger.info(_("实例: {}:{}已存在, 实例ID: {}").format(new_ip, new_port, new_instance.id))

        # ── 4. 更新 ClusterEntry DNS 绑定（MASTER_ENTRY）────────────────────
        master_entries = ClusterEntry.objects.filter(
            cluster=cluster,
            cluster_entry_type=ClusterEntryType.DNS,
            role=ClusterEntryRole.MASTER_ENTRY.value,
        )
        for entry in master_entries:
            if entry.storageinstance_set.filter(id=old_instance.id).exists():
                entry.storageinstance_set.remove(old_instance)
                entry.storageinstance_set.add(new_instance)
                logger.info(_("更新ClusterEntry DNS绑定: 从旧PRIMARY切换到新PRIMARY, Entry: {}").format(entry.entry))

        # ── 5. 更新 Cluster.storageinstance_set ──────────────────────────────
        cluster.storageinstance_set.remove(old_instance)
        cluster.storageinstance_set.add(new_instance)
        cluster.save()
        logger.info(_("更新集群实例集合: 移除旧PRIMARY {}:{}, 添加新PRIMARY {}:{}").format(old_ip, old_port, new_ip, new_port))

        # ── 6. 清理旧 StorageInstance 与旧 Machine ────────────────────────────
        old_instance.delete()
        logger.info(_("删除旧PRIMARY实例: {}:{}").format(old_ip, old_port))

        # 只有当旧机器上没有其他实例时才删除
        if not StorageInstance.objects.filter(machine=old_machine).exists():
            old_machine.delete()
            logger.info(_("删除旧机器: {}").format(old_ip))
        else:
            logger.info(_("旧机器 {} 上仍有其他实例，跳过机器删除").format(old_ip))

        logger.info(_("Oracle单实例机器替换完成，集群ID: {}, 新PRIMARY: {}:{}").format(cluster_id, new_ip, new_port))

        # ── 7. 密码修改 ────────────────────────────
        change_password.ip_change_password(old_ip, old_port, new_ip, new_port, bk_cloud_id)

    except Cluster.DoesNotExist:
        raise Exception(
            "oracle replace single instance failed: cluster_id={} bk_biz_id={} not found".format(cluster_id, bk_biz_id)
        )
    except StorageInstance.DoesNotExist:
        raise Exception(
            "oracle replace single instance failed: PRIMARY instance not found in cluster_id={}".format(cluster_id)
        )
    except Exception as e:
        logger.error(traceback.format_exc())
        raise Exception("oracle replace single instance failed: {}".format(e))
