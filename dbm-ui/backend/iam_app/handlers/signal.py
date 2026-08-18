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

from django.db.models.signals import post_save
from django.dispatch import receiver

from backend import env
from backend.db_meta.models import Cluster
from backend.db_monitor.models import MonitorPolicy, NoticeGroup
from backend.db_services.mysql.dumper.models import DumperSubscribeConfig
from backend.db_services.mysql.open_area.models import TendbOpenAreaConfig
from backend.flow.models import FlowTree
from backend.iam_app.dataclass.resources import ResourceEnum
from backend.iam_app.handlers.permission import Permission
from backend.ticket.models import Ticket

logger = logging.getLogger("root")


def post_save_grant_iam(resource_meta, model, instance, creator, created):
    """新建资源后给创建者授权。V3与V4的授权方式差异由 Permission 的鉴权后端消化"""
    if not created or not creator or env.BK_IAM_SKIP:
        return

    try:
        resource = resource_meta.create_instance(getattr(instance, resource_meta.lookup_field))
        Permission(username="admin").grant_creator_actions(resource, creator)
    except Exception as e:  # pylint: disable=broad-except
        logger.error(f"Grant creator actions failed: {e}")


@receiver(post_save, sender=FlowTree)
def post_save_flow(sender, instance, created, **kwargs):
    post_save_grant_iam(ResourceEnum.TASKFLOW, FlowTree, instance, instance.created_by, created)


@receiver(post_save, sender=Ticket)
def post_save_ticket(sender, instance, created, **kwargs):
    post_save_grant_iam(ResourceEnum.TICKET, Ticket, instance, instance.creator, created)


@receiver(post_save, sender=Cluster)
def post_save_cluster(sender, instance, created, **kwargs):
    resource_meta = ResourceEnum.cluster_type_to_resource_meta(instance.cluster_type)
    if resource_meta is None:
        return
    post_save_grant_iam(resource_meta, Cluster, instance, instance.creator, created)


@receiver(post_save, sender=MonitorPolicy)
def post_save_monitor_policy(sender, instance, created, **kwargs):
    resource_meta = ResourceEnum.MONITOR_POLICY
    post_save_grant_iam(resource_meta, MonitorPolicy, instance, instance.creator, created)


@receiver(post_save, sender=NoticeGroup)
def post_save_duty_rule(sender, instance, created, **kwargs):
    resource_meta = ResourceEnum.NOTIFY_GROUP
    post_save_grant_iam(resource_meta, NoticeGroup, instance, instance.creator, created)


@receiver(post_save, sender=TendbOpenAreaConfig)
def post_save_openarea_config(sender, instance, created, **kwargs):
    resource_meta = ResourceEnum.OPENAREA_CONFIG
    post_save_grant_iam(resource_meta, TendbOpenAreaConfig, instance, instance.creator, created)


@receiver(post_save, sender=DumperSubscribeConfig)
def post_save_dumper_subscribe_config(sender, instance, created, **kwargs):
    resource_meta = ResourceEnum.DUMPER_SUBSCRIBE_CONFIG
    post_save_grant_iam(resource_meta, DumperSubscribeConfig, instance, instance.creator, created)
