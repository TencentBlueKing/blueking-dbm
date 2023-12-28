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
from django.utils.translation import ugettext as _
from pipeline.component_framework.component import Component

from backend.components import DBConfigApi
from backend.components.dbconfig.constants import FormatType, LevelName, ReqType
from backend.db_meta.enums import ClusterType
from backend.db_meta.models import Cluster
from backend.flow.consts import ConfigTypeEnum
from backend.flow.plugins.components.collections.common.base_service import BaseService


class TendbHAInstantiateConfigService(BaseService):
    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        global_data = data.get_one_of_inputs("global_data")

        cluster_id = global_data["cluster_id"]
        cluster_obj = Cluster.objects.get(pk=cluster_id)

        data = DBConfigApi.get_or_generate_instance_config(
            {
                "bk_biz_id": str(cluster_obj.bk_biz_id),
                "level_name": LevelName.CLUSTER,
                "level_value": cluster_obj.immute_domain,
                "level_info": {"module": str(cluster_obj.db_module_id)},
                "conf_file": cluster_obj.major_version,
                "conf_type": ConfigTypeEnum.DBConf,
                "namespace": ClusterType.TenDBHA.value,
                "format": FormatType.MAP_LEVEL,
                "method": ReqType.GENERATE_AND_PUBLISH,
            }
        )

        self.log_info(_("[{}] 实例化 {} 配置成功: {}".format(kwargs["node_name"], cluster_obj.immute_domain, data)))
        return True


class TendbHAInstantiateConfigComponent(Component):
    name = __name__
    code = "tendbha_instantiate_config"
    bound_service = TendbHAInstantiateConfigService
