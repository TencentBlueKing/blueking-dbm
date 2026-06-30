"""
TencentBlueKing is pleased to support the open source community by making 蓝鲸智云-DB管理系统(BlueKing-BK-DBM) available.
Copyright (C) 2017-2023 THL A29 Limited, a Tencent company. All rights reserved.
Licensed under the MIT License (the "License"); you may not use this file except in compliance with the License.
You may obtain a copy of the License at https://opensource.org/licenses/MIT
Unless required by applicable law or agreed to in writing, software distributed under the License is distributed on
an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the License for the
specific language governing permissions and limitations under the License.
"""
import json
import logging

from django.utils.translation import gettext as _
from pipeline.component_framework.component import Component

from backend.components import DRSApi
from backend.db_meta.enums import InstanceStatus
from backend.db_meta.enums.instance_role import TenDBClusterSpiderRole
from backend.db_meta.models import Cluster, ProxyInstance
from backend.db_package.models import Package
from backend.flow.plugins.components.collections.mysql.exec_actuator_script import ExecuteDBActuatorScriptService
from backend.flow.utils.mysql.mysql_act_playload import MysqlActPayload
from backend.flow.utils.mysql.mysql_version_parse import spider_major_version_parse

logger = logging.getLogger("flow")

# 需要从已有 Spider 实例克隆到新 Spider 实例的核心运行时配置变量列表（按字母排序）
# 这些变量涵盖：连接数限制、InnoDB 引擎参数、慢查询阈值、Spider 引擎专属参数等
COPY_CONFIG_LIST = [
    "group_concat_max_len",
    "innodb_io_capacity",
    "innodb_read_io_threads",
    "innodb_strict_mode",
    "innodb_write_io_threads",
    "long_query_time",
    "max_connections",
    "max_prepared_stmt_count",
    "spider_bgs_mode",
    "spider_max_connections",
    "spider_net_read_timeout",
    "spider_net_write_timeout",
    "spider_parallel_limit",
    "spider_quick_mode",
    "table_open_cache",
    "table_definition_cache",
    "show_json_type",
]

# spider1.x 不支持的继承配置列表
SPIDER_1_X_NOT_SUPPORT_CONFIG_LIST = ["show_json_type", "spider_parallel_limit"]

# spider3.x 在 3.5.3 之前：show_json_type 与 spider_parallel_limit 均不支持
SPIDER_3_X_BEFORE_3_5_3_NOT_SUPPORT_CONFIG_LIST = ["show_json_type", "spider_parallel_limit"]

# spider3.x 在 [3.5.3, 3.7.13) 之间：spider_parallel_limit 已支持，show_json_type 仍不支持
SPIDER_3_X_BEFORE_3_7_13_NOT_SUPPORT_CONFIG_LIST = ["show_json_type"]

# spider3.x 在 [3.7.13, 3.8.0) 之间：全部支持
SPIDER_3_X_AFTER_3_7_13_NOT_SUPPORT_CONFIG_LIST = []

# spider3.x 在 3.8.0 及以上：show_json_type 再次不支持（3.8.x 移除了该特性）
SPIDER_3_X_AFTER_3_8_0_NOT_SUPPORT_CONFIG_LIST = ["show_json_type"]

# spider4.x 不支持的继承配置列表
SPIDER_4_X_NOT_SUPPORT_CONFIG_LIST = []

# spider 版本段与不支持的继承配置列表映射
# key 为 (major_version_no, sub_version_min)，表示「主版本号 + 子版本号下限」组成的版本段起点
# 同一主版本下若有多段，按子版本下限升序写；运行时取「<= 当前子版本号」的最大下限对应的列表
MAJOR_VERSION_NOT_SUPPORT_CONFIG_MAP = {
    (1000000, 0): SPIDER_1_X_NOT_SUPPORT_CONFIG_LIST,
    (3000000, 0): SPIDER_3_X_BEFORE_3_5_3_NOT_SUPPORT_CONFIG_LIST,
    (3000000, 5003): SPIDER_3_X_BEFORE_3_7_13_NOT_SUPPORT_CONFIG_LIST,
    (3000000, 7013): SPIDER_3_X_AFTER_3_7_13_NOT_SUPPORT_CONFIG_LIST,
    (3000000, 8000): SPIDER_3_X_AFTER_3_8_0_NOT_SUPPORT_CONFIG_LIST,
    (4000000, 0): SPIDER_4_X_NOT_SUPPORT_CONFIG_LIST,
}


class InstallSpiderWithCopyConfigService(ExecuteDBActuatorScriptService):
    """
    安装 Spider 节点并克隆已有同角色 Spider 实例的核心运行时配置。

    继承自 ExecuteDBActuatorScriptService，在执行 actuator 脚本安装 Spider 之前，
    会先从集群中已有的同角色 Spider 实例获取核心运行时参数，并将其注入到安装流程的
    kwargs 中，使新装的 Spider 节点能够继承已有节点的配置。

    如果集群中不存在同角色的 Spider 实例（即首次添加该角色），则跳过克隆配置，
    直接以配置系统中的默认配置进行安装。
    """

    def get_spider_core_runtime_config(self, spider: ProxyInstance, target_spider_pkg_name: str) -> dict:
        """
        通过 DRS（Database Remote Service）远程查询指定 Spider 实例的核心运行时配置。

        工作流程：
        1. 根据 COPY_CONFIG_LIST 拼装 SQL: show global variables where Variable_name in (...)
        2. 通过 DRSApi.rpc 远程执行 SQL 查询目标 Spider 实例的全局变量
        3. 将查询结果解析为 {变量名: 变量值} 的字典
        4. 校验 COPY_CONFIG_LIST 中所有变量是否都在查询结果中，缺失则抛出异常

        Args:
            spider: ProxyInstance 对象，表示一个已运行的 Spider 代理实例
            target_spider_pkg_name: 目标 Spider 实例的版本介质包名称，用于推算部署spider主版本号的信息

        Returns:
            dict: 键为变量名，值为对应的配置值，如 {"max_connections": "1000", ...}

        Raises:
            Exception: DRS 查询失败或返回结果中缺少 COPY_CONFIG_LIST 中定义的变量时抛出
        """
        # 获取主版本号、子版本号信息
        # 例：mariadb-11.4.2-linux-x86_64-tspider-3.7.13.tar.gz -> (3000000, 7013)
        major_version_no, sub_version_no = spider_major_version_parse(target_spider_pkg_name, True)
        spider_core_runtime_config = {}
        # 拼装 SQL，查询 COPY_CONFIG_LIST 中定义的全局变量
        sql = "show global variables where Variable_name in ({})".format(
            ", ".join("'{}'".format(v) for v in COPY_CONFIG_LIST)
        )

        # 通过 DRS API 远程执行 SQL，获取目标 Spider 实例的配置
        res = DRSApi.rpc(
            {
                "addresses": [spider.ip_port],
                "cmds": [sql],
                "force": False,
                "bk_cloud_id": spider.machine.bk_cloud_id,
            }
        )
        if res[0]["error_msg"]:
            # 远程查询失败，直接抛出异常中断流程
            raise Exception(_("{} 获取实例参数配置时出现异常, 请检查该实例是否出现故障:{}".format(spider.ip_port, res[0]["error_msg"])))

        # 解析查询结果，将 Variable_name -> Value 映射到字典中
        configs = res[0]["cmd_results"][0]["table_data"]
        for config in configs:
            spider_core_runtime_config[config["Variable_name"]] = config["Value"]

        # 校验 COPY_CONFIG_LIST 中的变量是否都存在于查询结果中
        missing_keys = set(COPY_CONFIG_LIST) - set(spider_core_runtime_config.keys())
        if missing_keys:
            self.log_warning(_("{} 源实例查询不到的需要继承的配置变量有: {}".format(spider.ip_port, ", ".join(sorted(missing_keys)))))

        # 计算目标spider的版本信息，获取到对应的不支持的继承配置列表
        # 在 MAJOR_VERSION_NOT_SUPPORT_CONFIG_MAP 中筛选出主版本号一致、且子版本号下限 <= 当前子版本号的所有版本段，
        # 取「子版本号下限最大」的一段对应的不支持列表，即当前版本所在的版本段（若无匹配则返回空列表）
        matched_segment = max(
            (
                (sub_min, not_support)
                for (major, sub_min), not_support in MAJOR_VERSION_NOT_SUPPORT_CONFIG_MAP.items()
                if major == major_version_no and sub_min <= sub_version_no
            ),
            default=(0, []),
        )
        not_support_config_list = matched_segment[1]
        self.log_info(
            _(
                "{} 新安装的spider版本[{}]不支持继承配置有: {}".format(
                    spider.ip_port, target_spider_pkg_name, ", ".join(sorted(not_support_config_list))
                )
            )
        )
        # 过滤掉目标版本不支持的配置
        for key in not_support_config_list:
            spider_core_runtime_config.pop(key, None)

        return spider_core_runtime_config

    def _execute(self, data, parent_data) -> bool:
        """
        节点执行入口，负责在安装 Spider 前获取并注入克隆配置。

        执行流程：
        1. 从 kwargs 中获取集群 ID 和待安装的 Spider 角色
        2. 查询集群中处于 RUNNING 状态的同角色 Spider 实例
        3. 若存在同角色实例，随机取一个作为配置模板，查询其核心运行时配置
        4. 将克隆配置以 spider_copy_config 字段注入 kwargs["cluster"] 字典中（值为 {端口号: 配置字典}）
        5. 调用父类 _execute 方法执行实际的 actuator 脚本安装

        Args:
            data: pipeline 流程数据对象，包含 kwargs 等输入参数
            parent_data: 父流程数据对象

        Returns:
            bool: 执行是否成功
        """
        kwargs = data.get_one_of_inputs("kwargs")
        cluster = Cluster.objects.get(id=kwargs["cluster"]["cluster_id"])
        spider_pkg = Package.objects.get(id=kwargs["cluster"]["pkg_id"])
        install_spider_role = kwargs["cluster"]["install_spider_role"]

        # 查找集群中处于 RUNNING 状态、且角色与待安装角色相同的 Spider 实例
        source_spiders = cluster.proxyinstance_set.filter(
            status=InstanceStatus.RUNNING, tendbclusterspiderext__spider_role=install_spider_role
        )
        # 根据待安装的 Spider 角色选择对应的 payload 生成函数：
        # - spider_slave 角色使用 get_install_slave_spider_payload
        # - 其他角色（spider_master / spider_mnt 等）使用 get_install_spider_payload
        if install_spider_role == TenDBClusterSpiderRole.SPIDER_SLAVE.value:
            get_mysql_payload_func = MysqlActPayload.get_install_slave_spider_payload.__name__
        else:
            get_mysql_payload_func = MysqlActPayload.get_install_spider_payload.__name__
        data.get_one_of_inputs("kwargs")["get_mysql_payload_func"] = get_mysql_payload_func
        if not source_spiders:
            # 首次添加该角色的 Spider，无需克隆配置，直接走默认安装流程
            self.log_info(_("集群不存在同角色的spider，不执行克隆配置操作，本次新装的spider配置一切以配置系统为准"))
            return super()._execute(data, parent_data)

        # 随机取第一个实例作为克隆配置的来源模板
        template_spider = source_spiders.first()
        self.log_info(_("获取到克隆配置的来源实例: {}").format(template_spider.ip_port))
        copy_config = self.get_spider_core_runtime_config(template_spider, spider_pkg.name)
        self.log_info(_("核心参数配置：{}".format(json.dumps(copy_config))))

        # 将克隆配置以 {"spider_copy_config": {端口号: 配置字典}} 的形式合并到 kwargs["cluster"] 中
        # 后续 actuator 脚本会读取该配置并应用到新安装的 Spider 实例上
        data.get_one_of_inputs("kwargs")["cluster"] = {
            **kwargs["cluster"],
            "spider_copy_config": {template_spider.port: copy_config},
        }
        return super()._execute(data, parent_data)


class InstallSpiderWithCopyConfigComponent(Component):
    """
    Pipeline 组件注册类，将 InstallSpiderWithCopyConfigService 注册为可在流程编排中使用的组件。

    属性:
        name: 组件名称，使用当前模块名
        code: 组件唯一标识码，用于流程编排中引用该组件
        bound_service: 绑定的服务类，即 InstallSpiderWithCopyConfigService
    """

    name = __name__
    code = "install_spider_with_copy_config"
    bound_service = InstallSpiderWithCopyConfigService
