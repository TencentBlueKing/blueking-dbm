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

from backend.components import DBConfigApi
from backend.components.dbconfig.constants import FormatType, LevelName
from backend.db_meta.models import StorageInstance
from backend.db_services.dbbase.resources import query
from backend.db_services.dbbase.resources.register import register_resource_decorator
from backend.flow.consts import ConfigTypeEnum

logger = logging.getLogger("root")


@register_resource_decorator()
class MysqlListRetrieveResource(query.ListRetrieveResource):
    """查看 mysql 架构的资源"""

    @classmethod
    def _get_default_storage_engine(cls, cluster, default_storage_engine_cache: dict = None) -> str:
        cache_key = cluster.db_module_id
        if default_storage_engine_cache is not None and cache_key in default_storage_engine_cache:
            return default_storage_engine_cache[cache_key]

        try:
            mysql_config = DBConfigApi.query_conf_item(
                {
                    "bk_biz_id": str(cluster.bk_biz_id),
                    "level_name": LevelName.MODULE,
                    "level_value": str(cluster.db_module_id),
                    "conf_file": cluster.major_version,
                    "conf_type": ConfigTypeEnum.DBConf,
                    "namespace": cluster.cluster_type,
                    "format": FormatType.MAP,
                }
            )["content"]
            default_storage_engine = (mysql_config or {}).get("mysqld.default_storage_engine", "")
        except Exception as e:
            logger.warning(
                "get mysql default storage engine failed, bk_biz_id=%s, db_module_id=%s, cluster_type=%s, err=%s",
                cluster.bk_biz_id,
                cluster.db_module_id,
                cluster.cluster_type,
                e,
            )
            default_storage_engine = ""

        if default_storage_engine_cache is not None:
            default_storage_engine_cache[cache_key] = default_storage_engine
        return default_storage_engine

    @classmethod
    def _filter_cluster_hook(
        cls, bk_biz_id, cluster_queryset, proxy_queryset, storage_queryset, limit, offset, **kwargs
    ):
        kwargs["default_storage_engine_cache"] = {}
        return super()._filter_cluster_hook(
            bk_biz_id, cluster_queryset, proxy_queryset, storage_queryset, limit, offset, **kwargs
        )

    @classmethod
    def _to_cluster_representation(cls, cluster, *args, **kwargs):
        cluster_info = super()._to_cluster_representation(cluster, *args, **kwargs)
        cluster_info["default_storage_engine"] = cls._get_default_storage_engine(
            cluster, kwargs.get("default_storage_engine_cache")
        )
        return cluster_info

    @staticmethod
    def slave_associate_mater_role(instances):
        """
        查询slave/repeater角色关联的主库
        """
        pair_instance_map = {}
        instance_ids = [instance["id"] for instance in instances]
        insts = (
            StorageInstance.objects.filter(id__in=instance_ids)
            .select_related("machine")
            .prefetch_related("as_receiver", "as_receiver__ejector__machine")
        )
        for inst in insts:
            key = f"{inst.machine.ip}:{inst.port}"
            pair_instance_map[key] = inst.as_receiver.get().ejector.simple_desc

        return pair_instance_map
