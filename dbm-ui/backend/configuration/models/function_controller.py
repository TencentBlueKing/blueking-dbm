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
from blue_krill.data_types.enum import EnumField, StructuredEnum
from django.db import models
from django.utils.translation import ugettext_lazy as _

from backend.configuration.constants import DBType
from backend.db_meta.enums import ClusterType


class CustomFuncNameEnum(str, StructuredEnum):
    BigData = EnumField("bigdata", _("大数据"))
    ToolBox = EnumField("toolbox", _("工具箱"))
    TenDBClusterToolBox = EnumField("tendbcluster_toolbox", _("TenDBCluster 工具箱"))


# 用于初始化功能开关，注意调整 key 后需跟前端对齐
# 为降低复杂度，这里仅设计两层功能开关
# 以 DBType、ClusterType、TicketType 为主，按需补充功能开关，需跟前端进行约定
FUNCTION_CONTROLLER_INIT_MAP = {
    DBType.MySQL.value: {
        "is_enabled": True,
        "children": {
            CustomFuncNameEnum.ToolBox.value: {"is_enabled": True},
            ClusterType.TenDBSingle.value: {"is_enabled": True},
            ClusterType.TenDBHA.value: {"is_enabled": True},
            ClusterType.TenDBCluster.value: {"is_enabled": False},
            CustomFuncNameEnum.TenDBClusterToolBox.value: {"is_enabled": False},
        },
    },
    DBType.Redis.value: {
        "is_enabled": True,
        "children": {
            ClusterType.TendisPredixyTendisplusCluster.value: {"is_enabled": True},
            ClusterType.TendisTwemproxyRedisInstance.value: {"is_enabled": True},
            ClusterType.TwemproxyTendisSSDInstance.value: {"is_enabled": True},
            CustomFuncNameEnum.ToolBox.value: {"is_enabled": False},
        },
    },
    CustomFuncNameEnum.BigData.value: {
        "is_enabled": True,
        "children": {
            DBType.Es.value: {"is_enabled": True},
            DBType.Kafka.value: {"is_enabled": True},
            DBType.Hdfs.value: {"is_enabled": True},
            DBType.InfluxDB.value: {"is_enabled": True},
            DBType.Pulsar.value: {"is_enabled": True},
        },
    },
}


class FunctionController(models.Model):
    """
    功能开启控制器
    TODO: 目前仅用作前端访问入口开关，后续需考虑用于限制后台功能和 API 返回的数据
    """

    name = models.CharField(_("功能名称"), max_length=255)
    is_enabled = models.BooleanField(_("是否开启"), default=False)
    is_frozen = models.BooleanField(_("是否冻结"), help_text=_("人工冻结此开关，将不受更新影响"), default=False)
    parent_name = models.CharField(_("父功能名称"), max_length=255, null=True, blank=True)

    class Meta:
        verbose_name = _("功能控制器")
        verbose_name_plural = _("功能控制器")
        unique_together = ("name", "parent_name")

    @classmethod
    def init_function_controller(cls):
        """
        功能开关初始化原则：
        - 不存在的功能开关，进行创建
        - 已存在、非冻结的功能开关，进行更新
        - 已存在、已冻结的功能开关，忽略
        - 如果父开关是关闭的，那么子开关也必须是关闭的
        """
        exist_functions = {
            (func.name, func.parent_name): {"is_enabled": func.is_enabled, "is_frozen": func.is_frozen, "id": func.id}
            for func in FunctionController.objects.all()
        }
        to_be_created_functions = []
        to_be_updated_functions = []

        def calculate_functions(data, parent_name=None):
            for func_name, func_data in data.items():
                name = func_data.get("name", func_name)
                is_enabled = func_data.get("is_enabled", False)
                is_frozen = exist_functions.get((name, parent_name), {}).get("is_frozen", False)
                if (name, parent_name) not in exist_functions:
                    to_be_created_functions.append(
                        FunctionController(
                            name=name, is_enabled=is_enabled, is_frozen=is_frozen, parent_name=parent_name
                        )
                    )
                elif not is_frozen:
                    func_id = exist_functions[(name, parent_name)]["id"]
                    to_be_updated_functions.append(
                        FunctionController(id=func_id, name=name, parent_name=parent_name, is_enabled=is_enabled)
                    )
                if "children" in func_data:
                    calculate_functions(func_data["children"], parent_name=name)

        calculate_functions(FUNCTION_CONTROLLER_INIT_MAP)
        FunctionController.objects.bulk_create(to_be_created_functions)
        FunctionController.objects.bulk_update(to_be_updated_functions, fields=["is_enabled"])

    @classmethod
    def get_all_function_controllers(cls, parent_name: str = None, all_fc_ctl: dict = None):
        """
        递归获取所有 FunctionController 对象及其子对象
        """
        function_controllers = {}
        # 避免在递归中进行 orm 查询，这里查询一次后传入即可
        if all_fc_ctl is None:
            all_fc_ctl = FunctionController.objects.all()
        for fc_ctl in all_fc_ctl:
            if fc_ctl.parent_name != parent_name:
                continue
            function_controllers[fc_ctl.name] = {
                "is_enabled": fc_ctl.is_enabled,
                "children": cls.get_all_function_controllers(parent_name=fc_ctl.name, all_fc_ctl=all_fc_ctl),
            }
        return function_controllers
