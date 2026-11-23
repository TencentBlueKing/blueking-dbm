# -*- coding: utf-8 -*-
"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"), see LICENSE for details.
"""
from django.db import transaction

from backend.db_meta.enums.comm import TagType
from backend.db_meta.models import Cluster, Tag


def create_cluster_tags(bk_biz_id, tags):
    """获取或创建业务下的集群标签，tags 的格式为 [{"env": "test"}]。"""
    tag_objs = []
    for item in tags:
        ((key, value),) = item.items()
        if key:
            tag, _ = Tag.objects.get_or_create(bk_biz_id=bk_biz_id, key=key, value=value, type=TagType.CLUSTER)
            tag_objs.append(tag)
    return tag_objs


@transaction.atomic
def add_cluster_tag_keys(bk_biz_id, cluster_ids, tags):
    """为已创建的集群绑定标签，保留集群上已存在的同名标签键。"""
    if not cluster_ids or not tags:
        return

    clusters = Cluster.objects.filter(bk_biz_id=bk_biz_id, id__in=cluster_ids)
    cluster_ids = list(clusters.select_for_update().order_by("id").values_list("id", flat=True))
    if not cluster_ids:
        return

    clusters = Cluster.objects.filter(bk_biz_id=bk_biz_id, id__in=cluster_ids)
    through = Cluster.tags.through
    for tag in create_cluster_tags(bk_biz_id, tags):
        add_ids = clusters.exclude(tags__key=tag.key).values_list("id", flat=True)
        through.objects.bulk_create([through(cluster_id=cluster_id, tag_id=tag.id) for cluster_id in add_ids])
