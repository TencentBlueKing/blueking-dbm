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
from typing import Union

from backend.configuration.constants import DBType
from backend.db_meta.enums import AccessLayer, MachineType
from backend.db_meta.models import ProxyInstance, StorageInstance
from backend.flow.utils.base.cc_topo_operate import CCTopoOperator


class MysqlCCTopoOperator(CCTopoOperator):
    db_type = DBType.MySQL.value

    def generate_custom_labels(self, inst: Union[StorageInstance, ProxyInstance]) -> dict:
        # 定义注册mysql/proxy/spider服务实例需要的labels标签结构
        return {"exporter_conf_path": f"exporter_{inst.port}.cnf"}

    @staticmethod
    def generate_ins_instance_role(ins: Union[StorageInstance, ProxyInstance]):
        """
        生成服务实例的 instance role
        """
        if ins.machine_type == MachineType.PROXY.value:
            # proxy_instance表没有所谓的实例角色，则用 AccessLayer 枚举来代替
            return AccessLayer.PROXY.value
        if ins.machine_type == MachineType.SPIDER.value:
            # spider 有单独的角色管理
            return ins.tendbclusterspiderext.spider_role
        return ins.instance_role
