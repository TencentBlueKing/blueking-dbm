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
from collections import defaultdict
from typing import Dict, List, Tuple

from django.db.models.signals import post_save
from django.dispatch import receiver

from backend import env
from backend.db_meta.enums import MachineType
from backend.db_meta.models import Cluster, StorageInstance
from backend.db_monitor.models import DutyRule, MonitorPolicy
from backend.db_services.mysql.dumper.models import DumperSubscribeConfig
from backend.db_services.mysql.open_area.models import TendbOpenAreaConfig
from backend.flow.models import FlowTree
from backend.iam_app.dataclass.resources import ResourceEnum
from backend.iam_app.handlers.permission import Permission

# 缓存已经授权过的资源属性
__cache_resource_attr: Dict[str, List[Tuple]] = defaultdict(list)


def post_save_grant_iam(resource_meta, model, instance, creator, created):
    if not created or not creator or env.BK_IAM_SKIP:
        return

    resource = resource_meta.create_instance(getattr(instance, resource_meta.lookup_field))

    # 排除_bk_iam_path_, id, name这些专用字段
    pop_fields = ["_bk_iam_path_", "id", "name"]
    for field in pop_fields:
        resource.attribute.pop(field, None)

    # 如果已被缓存，则无需授权
    attr_tuple = tuple(sorted([attr for attr in resource.attribute.values()]))
    if attr_tuple in __cache_resource_attr[resource.type]:
        return

    # 新建关联属性授权
    Permission(username="admin").grant_creator_actions_attr(resource, creator)
    __cache_resource_attr[resource.type].append(attr_tuple)


@receiver(post_save, sender=FlowTree)
def post_save_flow(sender, instance, created, **kwargs):
    post_save_grant_iam(ResourceEnum.TASKFLOW, FlowTree, instance, instance.created_by, created)


@receiver(post_save, sender=Cluster)
def post_save_cluster(sender, instance, created, **kwargs):
    resource_meta = ResourceEnum.cluster_type_to_resource_meta(instance.cluster_type)
    post_save_grant_iam(resource_meta, Cluster, instance, instance.creator, created)


@receiver(post_save, sender=StorageInstance)
def post_save_storage_instance(sender, instance, created, **kwargs):
    if instance.machine_type != MachineType.INFLUXDB:
        return
    resource_meta = ResourceEnum.INFLUXDB
    post_save_grant_iam(resource_meta, StorageInstance, instance, instance.creator, created)


@receiver(post_save, sender=MonitorPolicy)
def post_save_monitor_policy(sender, instance, created, **kwargs):
    resource_meta = ResourceEnum.MONITOR_POLICY
    post_save_grant_iam(resource_meta, MonitorPolicy, instance, instance.creator, created)


@receiver(post_save, sender=DutyRule)
def post_save_duty_rule(sender, instance, created, **kwargs):
    resource_meta = ResourceEnum.DUTY_RULE
    post_save_grant_iam(resource_meta, DutyRule, instance, instance.creator, created)


@receiver(post_save, sender=TendbOpenAreaConfig)
def post_save_openarea_config(sender, instance, created, **kwargs):
    resource_meta = ResourceEnum.OPENAREA_CONFIG
    post_save_grant_iam(resource_meta, TendbOpenAreaConfig, instance, instance.creator, created)


@receiver(post_save, sender=DumperSubscribeConfig)
def post_save_dumper_subscribe_config(sender, instance, created, **kwargs):
    resource_meta = ResourceEnum.DUMPER_SUBSCRIBE_CONFIG
    post_save_grant_iam(resource_meta, DumperSubscribeConfig, instance, instance.creator, created)
