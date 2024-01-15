"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""

from backend.configuration.constants import DBType
from backend.db_meta.models import StorageInstance
from backend.flow.utils.base.cc_topo_operate import CCTopoOperator


class SqlserverCCTopoOperator(CCTopoOperator):
    db_type = DBType.Sqlserver.value

    def generate_custom_labels(self, inst: StorageInstance) -> dict:
        # 服务实例需要的labels标签结构
        return {"exporter_conf_path": f"exporter_{inst.port}.cnf"}

    @staticmethod
    def generate_ins_instance_role(ins: StorageInstance):
        """
        生成服务实例的 instance role
        """
        return ins.instance_role
