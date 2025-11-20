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

from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component

from backend.components import DRSApi
from backend.flow.plugins.components.collections.common.base_service import BaseService


class MySQLCheckVariableConsistencyService(BaseService):
    """
    检查两个MySQL实例的全局变量一致性

    入参说明（kwargs）:
        reference_instance: str - 参考实例地址（格式：ip:port）
        compare_instance: str - 对比实例地址（格式：ip:port）
        variable_names: List[str] - 要对比的MySQL全局变量名称列表
        bk_cloud_id: int - 云区域ID

    功能说明:
        1. 使用 SHOW GLOBAL VARIABLES 查询两个实例的指定变量
        2. 对比变量值是否一致
        3. 自动处理 utf8/utf8mb3 字符集的兼容性
        4. 返回详细的差异信息

    返回值:
        True: 所有变量值一致
        False: 存在变量值差异或查询失败

    示例:
        kwargs = {
            "reference_instance": "127.0.0.1:3306",
            "compare_instance": "127.0.0.2:3306",
            "variable_names": ["character_set_server", "innodb_buffer_pool_size", "max_connections"],
            "bk_cloud_id": 0
        }
    """

    def _execute(self, data, parent_data) -> bool:
        kwargs = data.get_one_of_inputs("kwargs")
        self.log_info(_("传入参数:{}").format(kwargs))

        # 获取实例地址
        reference_instance = kwargs["reference_instance"]
        compare_instance = kwargs["compare_instance"]

        variable_names = kwargs.get("variable_names", [])
        if not variable_names:
            self.log_warning(_("变量名称列表为空，跳过变量一致性检测"))
            return True

        self.log_info(_("开始对比实例变量一致性"))
        self.log_info(_("参考实例: {}").format(reference_instance))
        self.log_info(_("对比实例: {}").format(compare_instance))
        self.log_info(_("检查变量: {}").format(", ".join(variable_names)))

        # 构建查询SQL - 查询指定的全局变量
        variable_names_quoted = ["'{}'".format(var) for var in variable_names]
        query_sql = "SHOW GLOBAL VARIABLES WHERE Variable_name IN ({})".format(", ".join(variable_names_quoted))
        self.log_info(_("构建的查询SQL: {}").format(query_sql))

        # 查询参考实例的变量
        reference_vars = self._query_instance_variables(reference_instance, query_sql, kwargs["bk_cloud_id"], _("参考"))
        if reference_vars is None:
            return False

        # 查询对比实例的变量
        compare_vars = self._query_instance_variables(compare_instance, query_sql, kwargs["bk_cloud_id"], _("对比"))
        if compare_vars is None:
            return False

        # 对比变量值
        return self._compare_variables(variable_names, reference_vars, compare_vars)

    def _query_instance_variables(self, instance_address, query_sql, bk_cloud_id, instance_label):
        """
        查询指定实例的全局变量

        @param instance_address: 实例地址 (ip:port)
        @param query_sql: 查询SQL语句
        @param bk_cloud_id: 云区域ID
        @param instance_label: 实例标签（用于日志，如"参考"或"对比"）
        @return: 变量字典，失败时返回None
        """
        rpc_info = {
            "addresses": [instance_address],
            "cmds": [query_sql],
            "force": False,
            "bk_cloud_id": bk_cloud_id,
        }

        self.log_info(_("查询{}实例的全局变量...").format(instance_label))
        self.log_debug(_("{}实例RPC请求参数: {}").format(instance_label, rpc_info))

        try:
            result = DRSApi.rpc(rpc_info)
            self.log_info(_("查询{}实例返回结果: {}").format(instance_label, result))

            # 检查返回结果的结构
            if not result or len(result) == 0:
                self.log_error(_("{}实例返回结果为空").format(instance_label))
                return None

            if result[0]["error_msg"]:
                self.log_error(_("查询{}实例失败: {}").format(instance_label, result[0]["error_msg"]))
                return None

            # 检查cmd_results是否存在
            if "cmd_results" not in result[0] or not result[0]["cmd_results"]:
                self.log_error(_("{}实例返回结果中缺少cmd_results字段").format(instance_label))
                return None

            # 检查table_data是否存在
            table_data = result[0]["cmd_results"][0].get("table_data")
            self.log_info(_("{}实例返回的table_data行数: {}").format(instance_label, len(table_data) if table_data else 0))

            variables = self._parse_variables(table_data)
            self.log_info(_("{}实例解析得到的变量数量: {}").format(instance_label, len(variables)))
            self.log_info(_("{}实例变量详情: {}").format(instance_label, variables))

            return variables

        except KeyError as e:
            self.log_error(_("查询{}实例结果解析失败，缺少必要字段: {}").format(instance_label, str(e)))
            self.log_error(_("完整返回结果: {}").format(result if "result" in locals() else "N/A"))
            return None
        except Exception as e:
            self.log_error(_("查询{}实例异常: {}").format(instance_label, str(e)))
            self.log_error(_("异常类型: {}").format(type(e).__name__))
            import traceback

            self.log_error(_("异常堆栈: {}").format(traceback.format_exc()))
            return None

    def _compare_variables(self, variable_names, reference_vars, compare_vars):
        """
        对比两个实例的变量值

        @param variable_names: 要对比的变量名称列表
        @param reference_vars: 参考实例的变量字典
        @param compare_vars: 对比实例的变量字典
        @return: True表示一致，False表示存在差异
        """
        self.log_info(_("开始逐个对比变量值..."))
        differences = []

        for var_name in variable_names:
            self.log_debug(_("正在对比变量: {}").format(var_name))
            reference_value = reference_vars.get(var_name)
            compare_value = compare_vars.get(var_name)

            # 如果某个变量在某个实例中不存在，记录警告但继续检查
            if reference_value is None and compare_value is None:
                self.log_warning(_("变量 {} 在两个实例中都不存在").format(var_name))
                continue
            elif reference_value is None:
                self.log_warning(_("变量 {} 在参考实例中不存在，对比实例值为: {}").format(var_name, compare_value))
                continue
            elif compare_value is None:
                self.log_warning(_("变量 {} 在对比实例中不存在，参考实例值为: {}").format(var_name, reference_value))
                continue

            # 记录当前对比的变量值
            self.log_debug(_("变量 {} - 参考实例值: {}, 对比实例值: {}").format(var_name, reference_value, compare_value))

            # 检查是否为 utf8/utf8mb3 兼容性场景
            if self._is_utf8_compatible(reference_value, compare_value):
                self.log_info(
                    _("变量 {} 值兼容 (utf8/utf8mb3): 参考实例={}, 对比实例={}").format(var_name, reference_value, compare_value)
                )
                continue

            # 对比变量值
            if reference_value != compare_value:
                diff_msg = _("变量名: {}, 参考实例: {}, 对比实例: {}").format(var_name, reference_value, compare_value)
                self.log_warning(_("发现变量差异: {}").format(diff_msg))
                differences.append(diff_msg)
            else:
                self.log_debug(_("变量 {} 值一致: {}").format(var_name, reference_value))

        # 返回结果
        if differences:
            self.log_error(_("发现 {} 个变量存在差异:").format(len(differences)))
            for diff in differences:
                self.log_error(_("  - {}").format(diff))
            return False
        else:
            self.log_info(_("所有变量值一致，检查通过"))
            return True

    def _parse_variables(self, table_data):
        """
        解析SHOW GLOBAL VARIABLES查询结果

        @param table_data: DRS API返回的表格数据，格式为字典列表
                          [{"Variable_name": "xxx", "Value": "yyy"}, ...]
        @return: 变量名到值的字典映射
        """
        if not table_data:
            self.log_debug(_("table_data为空，返回空字典"))
            return {}

        self.log_debug(_("开始解析table_data，数据类型: {}, 数据长度: {}").format(type(table_data).__name__, len(table_data)))

        variables = {}
        for idx, row in enumerate(table_data):
            # table_data是字典列表格式
            if isinstance(row, dict):
                var_name = row.get("Variable_name")
                var_value = row.get("Value")
                if var_name:
                    variables[var_name] = var_value
                    self.log_debug(_("解析行 {}: {} = {}").format(idx, var_name, var_value))
                else:
                    self.log_warning(_("解析行 {} 失败，Variable_name为空: {}").format(idx, row))
            # 兼容旧的列表格式（如果存在）
            elif isinstance(row, (list, tuple)) and len(row) >= 2:
                var_name = row[0]
                var_value = row[1]
                variables[var_name] = var_value
                self.log_debug(_("解析行 {} (列表格式): {} = {}").format(idx, var_name, var_value))
            else:
                self.log_warning(_("解析行 {} 失败，未知格式: 类型={}, 内容={}").format(idx, type(row).__name__, row))

        self.log_debug(_("解析完成，共解析到 {} 个变量").format(len(variables)))
        return variables

    def _is_utf8_compatible(self, value1, value2):
        """
        检查两个值是否为utf8/utf8mb3兼容场景
        参考Go代码中的兼容性处理逻辑

        @param value1: 参考实例的值
        @param value2: 对比实例的值
        @return: 是否兼容
        """
        # 完全相同的值
        if value1 == value2:
            return True

        # utf8_ 和 utf8mb3_ 前缀兼容
        if (value1.startswith("utf8_") and value2.startswith("utf8mb3_")) or (
            value1.startswith("utf8mb3_") and value2.startswith("utf8_")
        ):
            return True

        # utf8 和 utf8mb3 直接兼容
        if (value1 == "utf8" and value2 == "utf8mb3") or (value1 == "utf8mb3" and value2 == "utf8"):
            return True

        return False


class MySQLCheckVariableConsistencyComponent(Component):
    name = __name__
    code = "mysql_check_variable_consistency"
    bound_service = MySQLCheckVariableConsistencyService
