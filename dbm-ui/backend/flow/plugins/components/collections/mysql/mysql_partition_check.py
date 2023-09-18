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

from backend.components.mysql_partition.client import DBPartitionApi
from backend.flow.plugins.components.collections.common.base_service import BaseService


class MysqlPartitionDryRunService(BaseService):
    """
    获取分区语句
    """

    def _execute(self, data, parent_data) -> bool:
        global_data = data.get_one_of_inputs("global_data") or {}
        trans_data = data.get_one_of_inputs("trans_data")
        try:
            resp = DBPartitionApi.dry_run(
                {
                    "cluster_type": global_data["cluster_type"],
                    "bk_biz_id": global_data["bk_biz_id"],
                    "config_ids": [global_data["config_id"]],
                    "cluster_id": global_data["cluster_id"],
                    "ip": global_data["ip"],
                    "port": global_data["port"],
                    "operator": global_data["created_by"],
                    "bk_cloud_id": global_data["bk_cloud_id"],
                }
            )
        except Exception as e:
            self.log_error(_("分区管理服务api异常，相关信息: {}").format(e))
            return False
        self.log_info(resp)
        trans_data.execute_objects = resp
        data.outputs["trans_data"] = trans_data
        self.log_info(_("单据id{}".format(global_data["uid"])))
        self.log_info(_("获取分区语句成功"))
        return True


class MysqlPartitionDryRunServiceComponent(Component):
    name = __name__
    code = "mysql_partition_dry_run"
    bound_service = MysqlPartitionDryRunService
