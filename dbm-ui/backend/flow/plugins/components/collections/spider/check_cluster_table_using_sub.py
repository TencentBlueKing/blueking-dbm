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
from dataclasses import asdict

from django.utils.translation import ugettext as _

from backend.db_meta.models import Cluster
from backend.flow.consts import DBA_SYSTEM_USER, TruncateDataTypeEnum
from backend.flow.engine.bamboo.scene.common.builder import SubBuilder
from backend.flow.plugins.components.collections.mysql.general_check_db_in_using import GeneralCheckDBInUsingComponent
from backend.flow.utils.mysql.mysql_act_dataclass import BKCloudIdKwargs

logger = logging.getLogger("root")


def build_check_cluster_table_using_sub_flow(root_id: str, cluster_obj: Cluster, parent_global_data: dict):
    sub_pipeline = SubBuilder(root_id=root_id, data=parent_global_data)

    instance_pipes = []
    for spider_instance in cluster_obj.proxyinstance_set.all():
        instance_pipe = SubBuilder(
            root_id=root_id,
            data={
                "ip": spider_instance.machine.ip,
                "port": spider_instance.port,
                "truncate_data_type": TruncateDataTypeEnum.DROP_DATABASE.value,
            },
        )
        instance_pipe.add_act(
            act_name=_(""),
            act_component_code=GeneralCheckDBInUsingComponent.code,
            kwargs=asdict(BKCloudIdKwargs(bk_cloud_id=cluster_obj.bk_cloud_id)),
        )
        instance_pipes.append(
            instance_pipe.build_sub_process(
                sub_name=_("{} {} 检查库表是否在用".format(cluster_obj.immute_domain, spider_instance))
            )
        )

    sub_pipeline.add_parallel_sub_pipeline(sub_flow_list=instance_pipes)
    return sub_pipeline.build_sub_process(sub_name=_("{} 检查库表是否在用".format(cluster_obj.immute_domain)))
