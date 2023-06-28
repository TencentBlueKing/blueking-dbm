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
import base64
import datetime
import glob
import json
import logging
import os
import subprocess

from django.conf import settings

from backend import env
from backend.components import BKLogApi, BKMonitorV3Api, CCApi, ItsmApi
from backend.components.constants import SSL_KEY
from backend.configuration.constants import BKM_DBM_REPORT, DBM_REPORT_INITIAL_VALUE, DBM_SSL, RESOURCE_TOPO, DBType
from backend.configuration.models.system import SystemSettings, SystemSettingsEnum
from backend.core.storages.constants import FileCredentialType, StorageType
from backend.core.storages.file_source import BkJobFileSourceManager
from backend.core.storages.storage import get_storage
from backend.db_meta.models import AppMonitorTopo
from backend.db_monitor.constants import TPLS_ALARM_DIR, TPLS_COLLECT_DIR
from backend.db_monitor.models import AlertRule, CollectInstance, CollectTemplate, NoticeGroup, RuleTemplate
from backend.db_services.ipchooser.constants import DB_MANAGE_SET
from backend.dbm_init.constants import CC_APP_ABBR_ATTR, CC_HOST_DBM_ATTR
from backend.dbm_init.json_files.format import JsonConfigFormat
from backend.exceptions import ApiError, ApiRequestError, ApiResultError

logger = logging.getLogger("root")

# ToDo：支持命令行参数控制
EXCLUDE_DB_TYPES = [
    # DBType.Pulsar.value, DBType.InfluxDB.value
]


class Services:
    """
    相关服务的初始化操作
    """

    @staticmethod
    def auto_create_itsm_service() -> int:
        """
        创建/更新 bk dbm的itsm服务
        """

        project_key = env.BK_ITSM_PROJECT_KEY
        dbm_catalog_name = "bk_dbm"
        dbm_service_name = "BK_DBM"

        try:
            with open("backend/dbm_init/json_files/itsm/itsm_dbm.json", "r") as f:
                dbm_service_json = json.load(f)
        except FileNotFoundError as e:
            raise Exception("服务json文件不存在，请确保json文件存在后进行创建/更新itsm服务, err: %s", e)

        # 查询dbm服务目录的id，如果不存在则创建服务目录
        catalogs_data = ItsmApi.get_service_catalogs({"project_key": project_key}, use_admin=True)[0]
        root_id = catalogs_data["id"]
        children_catalogs_map = {data["name"]: data["id"] for data in catalogs_data["children"]}
        dbm_catalog_id = children_catalogs_map.get(dbm_catalog_name)
        if dbm_catalog_name not in children_catalogs_map.keys():
            dbm_catalog_data = ItsmApi.create_service_catalog(
                {"project_key": project_key, "parent__id": root_id, "name": dbm_catalog_name}, use_admin=True
            )
            dbm_catalog_id = dbm_catalog_data["id"]

        # 在服务目录中查询服务列表
        services_data = ItsmApi.get_services({"project_key": project_key, "catalog_id": dbm_catalog_id})
        children_services_map = {data["name"]: data["id"] for data in services_data}

        # 对服务进行创建/更新
        dbm_service_json["project_key"] = project_key
        dbm_service_json["catalog_id"] = dbm_catalog_id
        dbm_service_json["name"] = dbm_service_name

        try:
            if dbm_service_name not in children_services_map.keys():
                # 服务不存在则创建服务
                dbm_service_id = ItsmApi.import_service(params=dbm_service_json, use_admin=True)["id"]
                logger.info("itsm服务创建成功，服务id为: %s", dbm_service_id)
            else:
                # 服务存在则更新服务
                dbm_service_id = children_services_map[dbm_service_name]
                dbm_service_json["id"] = dbm_service_id
                ItsmApi.update_service(params=dbm_service_json, use_admin=True)
                logger.info("itsm服务更新成功，服务id为: %s", dbm_service_id)
        except ApiError as e:
            raise Exception("服务创建/更新失败，请联系管理员。错误信息: %s", e)

        # 更新到系统配置中
        SystemSettings.insert_setting_value(key=SystemSettingsEnum.BK_ITSM_SERVICE_ID.value, value=str(dbm_service_id))
        logger.info("服务创建/更新成功")
        return dbm_service_id

    @staticmethod
    def auto_create_bklog_service() -> bool:
        """
        创建/更新 bk dbm的itsm服务
        采集项服务一般不会更改，因此这里就不涉及更新服务了
        """

        bklog_json_files_path = "backend/dbm_init/json_files/bklog"
        # 获取当前采集项的列表 TODO: 暂时不做分页查询，默认当前系统采集项不超过500个
        data = BKLogApi.list_collectors(
            {"bk_biz_id": env.DBA_APP_BK_BIZ_ID, "pagesize": 500, "page": 1}, use_admin=True
        )
        collectors_name__info_map = {collector["collector_config_name_en"]: collector for collector in data["list"]}

        for filename in os.listdir(bklog_json_files_path):
            if not filename.endswith(".json"):
                continue

            # 读取日志采集项json文件，并渲染配置
            with open(os.path.join(bklog_json_files_path, filename), "r") as f:
                bklog_json_str = f.read()
                func_name = filename.split(".")[0]
                if hasattr(JsonConfigFormat, f"format_{func_name}"):
                    bklog_json_str = JsonConfigFormat.format(bklog_json_str, f"format_{func_name}")
                if "mysql" in filename:
                    bklog_json_str = JsonConfigFormat.format(bklog_json_str, JsonConfigFormat.format_mysql.__name__)
                if "redis" in filename:
                    bklog_json_str = JsonConfigFormat.format(bklog_json_str, JsonConfigFormat.format_redis.__name__)
                else:
                    logger.warning(f"格式化函数{func_name}不存在(如果无需格式化json可忽略)")
                try:
                    bklog_json = json.loads(bklog_json_str)
                except json.decoder.JSONDecodeError as err:
                    logger.error(f"读取json文件失败: {filename}, {err}, {bklog_json_str}")
                    raise err

            # 判断采集项是否重复创建
            collector_name = bklog_json["collector_config_name_en"]
            data = BKLogApi.pre_check(
                {
                    "bk_biz_id": env.DBA_APP_BK_BIZ_ID,
                    "collector_config_name_en": collector_name,
                },
                use_admin=True,
            )
            if not data["allowed"]:
                # 采集项已创建，对采集项进行更新
                try:
                    collector_config_id = collectors_name__info_map[collector_name]["collector_config_id"]
                except KeyError:
                    logger.error(f"采集项{collector_name}被创建后删除，暂无法重建，请联系管理员处理。")
                    continue
                bklog_json.update({"collector_config_id": collector_config_id})
                logger.info(f"采集项{collector_name}已创建, 对采集项进行更新...")
                try:
                    BKLogApi.fast_update(params=bklog_json, use_admin=True)
                except (ApiRequestError, ApiResultError) as e:
                    logger.error(f"采集项{collector_name}更新失败，请联系管理员。错误信息：{e}")

                continue

            # 创建采集项
            try:
                data = BKLogApi.fast_create(params=bklog_json, use_admin=True)
                logger.info(f"采集项创建成功，相关信息: {data}")
            except (ApiRequestError, ApiResultError) as e:
                # 当前采集项创建失败默认不影响下一个采集项的创建
                logger.error(f"采集项创建失败，请联系管理员。错误信息：{e}")

        return True

    @staticmethod
    def auto_create_bkcc_service() -> bool:
        """初始化cc配置:
        - 主机模型增加dbm_meta自定义字段
        - 业务模型增加db_app_abbr字段
        - 初始化cc拓扑
        - 初始化临时中转拓扑
        """

        # 初始化DB业务拓扑
        logger.info("init cc topo for monitor discover.")
        AppMonitorTopo.init_topo()

        # 初始化空闲集群的DB空闲模块，用于存放资源池机器
        if not SystemSettings.get_setting_value(key=RESOURCE_TOPO):
            manage_set = CCApi.create_set(
                {
                    "bk_biz_id": env.DBA_APP_BK_BIZ_ID,
                    "data": {"bk_parent_id": env.DBA_APP_BK_BIZ_ID, "bk_set_name": DB_MANAGE_SET},
                }
            )
            resource_module = CCApi.create_module(
                {
                    "bk_biz_id": env.DBA_APP_BK_BIZ_ID,
                    "bk_set_id": manage_set["bk_set_id"],
                    "data": {"bk_parent_id": manage_set["bk_set_id"], "bk_module_name": "resource.idle.module"},
                }
            )
            SystemSettings.insert_setting_value(
                key=RESOURCE_TOPO,
                value_type="dict",
                value={"set_id": manage_set["bk_set_id"], "module_id": resource_module["bk_module_id"]},
            )

        # 初始化主机自定义属性，用于system数据拷贝
        logger.info("init cc biz custom field <%s> for monitor's dbm_system copy.", CC_HOST_DBM_ATTR)
        model_attrs = CCApi.search_object_attribute(
            {
                "bk_biz_id": env.DBA_APP_BK_BIZ_ID,
                "bk_obj_id": "host",
            },
            use_admin=True,
        )

        exist_dbm_attr = [attr for attr in model_attrs if attr["bk_property_id"] == CC_HOST_DBM_ATTR]
        if exist_dbm_attr:
            logger.info("skip exist dbm attr in host model")
            return True

        CCApi.create_biz_custom_field(
            {
                "bk_biz_id": env.DBA_APP_BK_BIZ_ID,
                "bk_obj_id": "host",
                "bk_property_name": CC_HOST_DBM_ATTR,
                "bk_property_id": CC_HOST_DBM_ATTR,
                "bk_property_group": "default",
                "unit": "",
                "placeholder": "dbm专用字段",
                "bk_property_type": "longchar",
                # 必须为True，否则字段只读
                "editable": True,
                "isrequired": False,
                "option": "",
            },
            use_admin=True,
        )

        logger.info("init cc db_app_abbr for english app")

        # 为业务模型增加dbm_app_abbr字段
        model_attrs = CCApi.search_object_attribute(
            {
                "bk_biz_id": env.DBA_APP_BK_BIZ_ID,
                "bk_obj_id": "biz",
            },
            use_admin=True,
        )
        exist_dbm_attr = [attr for attr in model_attrs if attr["bk_property_id"] == CC_APP_ABBR_ATTR]
        if exist_dbm_attr:
            logger.warning("skip exist dbm attr in biz model")
            return True

        CCApi.create_object_attribute(
            {
                "bk_obj_id": "biz",
                "bk_property_name": CC_APP_ABBR_ATTR,
                "bk_property_id": CC_APP_ABBR_ATTR,
                "bk_property_group": "default",
                "unit": "",
                "placeholder": "",
                "bk_property_type": "singlechar",
                "editable": True,
                "isrequired": False,
                "option": "^[A-Za-z0-9_-]+$",
            },
            use_admin=True,
        )

        logger.warning("create dbm attr in biz model success")

        return True

    @staticmethod
    def init_alarm_strategy():
        """初始化告警策略"""

        bkm_dbm_report = SystemSettings.get_setting_value(key=BKM_DBM_REPORT)

        now = datetime.datetime.now()
        updated_alarms = 0
        logger.warning("[init_alarm_strategy] sync bkmonitor alarm start: %s", now)

        # 未来考虑将模板放到db管理
        # rules = RuleTemplate.objects.filter(is_enabled=True, bk_biz_id=0)
        # for rule in rules:
        alarm_tpls = os.path.join(TPLS_ALARM_DIR, "*.tpl64")
        for alarm_tpl in glob.glob(alarm_tpls):
            with open(alarm_tpl, "rb") as f:
                template_dict = json.loads(base64.b64decode(f.read()))
                rule = RuleTemplate(**template_dict)

            alert_params = rule.details

            # 支持跳过部分db类型的初始化
            if rule.db_type in EXCLUDE_DB_TYPES:
                continue

            try:
                try:
                    # 唯一性：db_type+name
                    alert_rule = AlertRule.objects.get(bk_biz_id=rule.bk_biz_id, db_type=rule.db_type, name=rule.name)
                    # alert_rule = AlertRule.objects.get(template_id=rule.id)
                    alert_params["id"] = alert_rule.monitor_strategy_id
                    logger.warning("[init_alarm_strategy] update bkmonitor alarm: %s " % rule.db_type)
                except AlertRule.DoesNotExist:
                    # 为了能够重复执行，这里也支持下AlertRule被清空的情况
                    res = BKMonitorV3Api.search_alarm_strategy_v3(
                        {
                            "page": 1,
                            "page_size": 1,
                            "conditions": [{"key": "name", "value": alert_params["name"]}],
                            "bk_biz_id": env.DBA_APP_BK_BIZ_ID,
                            "with_notice_group": False,
                            "with_notice_group_detail": False,
                        },
                        use_admin=True,
                    )

                    # 批量获取策略
                    strategy_config_list = res["strategy_config_list"]

                    # 业务下存在该策略
                    if strategy_config_list:
                        strategy_config = strategy_config_list[0]
                        alert_params["id"] = strategy_config["id"]
                        logger.warning("[init_alarm_strategy] sync bkmonitor alarm: %s " % rule.db_type)
                    else:
                        logger.warning("[init_alarm_strategy] create bkmonitor alarm: %s " % rule.db_type)

                # 更新业务id
                alert_params["bk_biz_id"] = env.DBA_APP_BK_BIZ_ID

                # 用最新告警组覆盖模板中的
                notice = alert_params["notice"]
                notice["user_groups"] = NoticeGroup.get_monitor_groups(db_type=rule.db_type)

                # 自定义事件和指标需要渲染metric_id
                # {bk_biz_id}_bkmoinitor_event_{event_data_id}
                items = alert_params["items"]
                for item in items:
                    for query_config in item["query_configs"]:
                        if "custom.event" not in query_config["metric_id"]:
                            continue

                        query_config["metric_id"] = query_config["metric_id"].format(
                            bk_biz_id=env.DBA_APP_BK_BIZ_ID, event_data_id=bkm_dbm_report["event"]["data_id"]
                        )
                        query_config["result_table_id"] = query_config["result_table_id"].format(
                            bk_biz_id=env.DBA_APP_BK_BIZ_ID, event_data_id=bkm_dbm_report["event"]["data_id"]
                        )
                        logger.warning(query_config)
                        # logger.info(query_config["metric_id"], query_config["result_table_id"])

                res = BKMonitorV3Api.save_alarm_strategy_v3(alert_params, use_admin=True)

                # 实例化Rule
                obj, _ = AlertRule.objects.update_or_create(
                    defaults={"details": alert_params, "monitor_strategy_id": res["id"]},
                    bk_biz_id=rule.bk_biz_id,
                    db_type=rule.db_type,
                    name=rule.name,
                    # template_id=rule.id,
                )

                updated_alarms += 1
            except Exception as e:  # pylint: disable=wildcard-import
                logger.error("[init_alarm_strategy] sync bkmonitor alarm: %s (%s)", rule.db_type, e)

        logger.warning(
            "[init_alarm_strategy] finish sync bkmonitor alarm end: %s, update_cnt: %s",
            datetime.datetime.now() - now,
            updated_alarms,
        )

    @staticmethod
    def init_collect_strategy():
        now = datetime.datetime.now()
        updated_collectors = 0

        logger.warning("[init_collect_strategy] start sync bkmonitor collector start: %s", now)

        # 未来考虑将模板放到db管理
        # templates = CollectTemplate.objects.filter(bk_biz_id=0)
        # for template in templates:

        collect_tpls = os.path.join(TPLS_COLLECT_DIR, "*.tpl64")
        for collect_tpl in glob.glob(collect_tpls):
            with open(collect_tpl, "rb") as f:
                template_dict = json.loads(base64.b64decode(f.read()))
                template = CollectTemplate(**template_dict)

            collect_params = template.details

            # 支持跳过部分db类型的初始化
            if template.db_type in EXCLUDE_DB_TYPES:
                continue

            try:
                try:
                    collect_instance = CollectInstance.objects.get(
                        bk_biz_id=template.bk_biz_id, db_type=template.db_type, plugin_id=template.plugin_id
                    )
                    collect_params["id"] = collect_instance.collect_id
                    logger.warning("[init_collect_strategy] update bkmonitor collector: %s " % template.db_type)
                except CollectInstance.DoesNotExist:
                    # 为了能够重复执行，这里考虑下CollectInstance被清空的情况
                    res = BKMonitorV3Api.query_collect_config(
                        {"bk_biz_id": env.DBA_APP_BK_BIZ_ID, "search": {"fuzzy": collect_params["name"]}},
                        use_admin=True,
                    )

                    # 业务下存在该策略
                    collect_config_list = res["config_list"]
                    if res["total"] == 1:
                        collect_config = collect_config_list[0]
                        collect_params["id"] = collect_config["id"]
                        logger.warning("[init_collect_strategy] sync bkmonitor collector: %s " % template.db_type)
                    else:
                        logger.warning("[init_collect_strategy] create bkmonitor collector: %s " % template.db_type)

                # 其他渲染操作
                collect_params["bk_biz_id"] = env.DBA_APP_BK_BIZ_ID
                collect_params["plugin_id"] = template.plugin_id

                collect_params["target_nodes"] = [
                    {"bk_inst_id": bk_set_id, "bk_obj_id": "set", "bk_biz_id": env.DBA_APP_BK_BIZ_ID}
                    for bk_set_id in AppMonitorTopo.get_set_by_plugin_id(plugin_id=template.plugin_id)
                ]

                res = BKMonitorV3Api.save_collect_config(collect_params, use_admin=True)

                # 实例化Rule
                obj, _ = CollectInstance.objects.update_or_create(
                    defaults={"details": collect_params, "collect_id": res["id"]},
                    bk_biz_id=template.bk_biz_id,
                    db_type=template.db_type,
                    plugin_id=template.plugin_id,
                )

                updated_collectors += 1
            except Exception as e:  # pylint: disable=wildcard-import
                logger.error("[init_collect_strategy] sync bkmonitor collector: %s (%s)", template.db_type, e)

        logger.warning(
            "[init_collect_strategy] finish sync bkmonitor collector end: %s, update_cnt: %s",
            datetime.datetime.now() - now,
            updated_collectors,
        )

    @staticmethod
    def init_custom_metric_and_event():
        """初始化自定义指标和采集项"""
        custom_name = "dbm_report_channel"
        logger.info("init_custom_metric_and_event: create metric/event channel for dbmon and mysqlcrond")

        # 自定义指标
        res = BKMonitorV3Api.custom_time_series(
            {
                "search_key": custom_name,
                "page": 1,
                "page_size": 10,
                "bk_biz_id": 3,
            }
        )
        if res.get("total") > 0:
            logger.info("init_custom_metric_and_event: dbm metric exists, skip create")
            time_series_group_id = res["list"][0]["time_series_group_id"]
        else:
            res_custom_time_series = BKMonitorV3Api.create_custom_time_series(
                {
                    "name": custom_name,
                    "scenario": "component",
                    "data_label": custom_name,
                    "is_platform": True,
                    "protocol": "json",
                    "desc": "for dbmon and mysqlcrond",
                    "bk_biz_id": env.DBA_APP_BK_BIZ_ID,
                }
            )
            time_series_group_id = res_custom_time_series["time_series_group_id"]
            logger.info(res_custom_time_series)

        # 更新dataid和token
        res = BKMonitorV3Api.custom_time_series_detail(
            {"time_series_group_id": time_series_group_id, "bk_biz_id": env.DBA_APP_BK_BIZ_ID}
        )
        DBM_REPORT_INITIAL_VALUE["metric"].update(
            {
                "data_id": res["bk_data_id"],
                "token": res["access_token"],
            }
        )

        # 自定义事件
        res = BKMonitorV3Api.query_custom_event_group(
            {
                "search_key": custom_name,
                "page": 1,
                "page_size": 10,
                "bk_biz_id": 3,
            }
        )
        if res.get("total") > 0:
            bk_event_group_id = res["list"][0]["bk_event_group_id"]
            logger.info("init_custom_metric_and_event: dbm event exists, skip create")
        else:
            res_custom_event = BKMonitorV3Api.create_custom_event_group(
                {
                    "name": custom_name,
                    "scenario": "component",
                    "data_label": custom_name,
                    "is_platform": True,
                    "bk_biz_id": env.DBA_APP_BK_BIZ_ID,
                }
            )
            bk_event_group_id = res_custom_event["bk_event_group_id"]
            logger.info(res_custom_event)

        # 更新dataid和token
        logger.info(
            "init_custom_metric_and_event: time_series_group_id=%s, bk_event_group_id=%s",
            time_series_group_id,
            bk_event_group_id,
        )
        # TODO: 监控提供的是页面接口，需要提供时间范围查询详情
        end = datetime.datetime.now()
        start = end - datetime.timedelta(hours=1)
        res = BKMonitorV3Api.get_custom_event_group(
            {
                "time_range": "{} -- {}".format(
                    start.strftime("%Y-%m-%d %H:%M:%S"), end.strftime("%Y-%m-%d %H:%M:%S")
                ),
                "bk_event_group_id": bk_event_group_id,
                "bk_biz_id": env.DBA_APP_BK_BIZ_ID,
            }
        )
        DBM_REPORT_INITIAL_VALUE["event"].update(
            {
                "data_id": res["bk_data_id"],
                "token": res["access_token"],
            }
        )

        logger.info("init_custom_metric_and_event: %s", DBM_REPORT_INITIAL_VALUE)
        SystemSettings.objects.update_or_create(
            defaults={
                "value": DBM_REPORT_INITIAL_VALUE,
                "type": "dict",
                "creator": "system",
                "updater": "system",
            },
            key=BKM_DBM_REPORT,
        )

    @staticmethod
    def auto_create_bkmonitor_alarm() -> bool:
        """初始化bkmonitor配置"""

        logger.info("auto_create_bkmonitor_service")

        # 加载采集策略
        Services.init_collect_strategy()

        # 加载告警策略
        Services.init_alarm_strategy()

        return True

    @staticmethod
    def auto_create_bkmonitor_channel() -> bool:
        """初始化自定义上报通道"""

        Services.init_custom_metric_and_event()

        return True

    @staticmethod
    def auto_create_ssl_service() -> bool:
        """生成c/s密钥对"""
        script_root_dir = os.path.join(settings.BASE_DIR, "scripts/")
        ssl_script = os.path.join(script_root_dir, "make_ssl_pairs.sh")
        ssl_dir = os.path.join(script_root_dir, "ssls")

        # 避免重复初始化
        if SystemSettings.objects.filter(key=SSL_KEY).exists():
            logger.info("auto_create_ssl_service skip initialized task")
            return True

        try:
            os.chdir(script_root_dir)
            exit_code = subprocess.call(ssl_script)
            if exit_code != 0:
                logger.info("auto_create_ssl_service script failed")
                return False
        except Exception as e:
            logger.info("auto_create_ssl_service exception failed, %s", str(e))
            return False

        # 由SystemSettings中的DBM_SSL控制是否重新生成证书，这里直接覆盖
        storage = get_storage(file_overwrite=True)
        dbm_ssl = {}
        for ssl_file_name in os.listdir(ssl_dir):
            with open(os.path.join(ssl_dir, ssl_file_name), "rb") as ssl_file:
                storage.save(name=os.path.join(settings.BKREPO_SSL_PATH, ssl_file_name), content=ssl_file)
                logger.error("auto_create_ssl_service upload %s success", ssl_file_name)

                # 重置文件指针，重新读取文件并写入dict
                ssl_file.seek(0)
                dbm_ssl[ssl_file_name] = str(ssl_file.read().decode())

        # 入库到系统配置，提供给组件接口使用
        SystemSettings.insert_setting_value(key=DBM_SSL, value=dbm_ssl)

        logger.info("auto_create_ssl_service success")
        return True

    @classmethod
    def auto_create_bkjob_service(cls):
        """初始化文件源和凭证"""

        BkJobFileSourceManager.get_or_create_file_source(
            bk_biz_id=env.JOB_BLUEKING_BIZ_ID,
            storage_type=StorageType.BLUEKING_ARTIFACTORY.value,
            credential_type=FileCredentialType.USERNAME_PASSWORD.value,
            credential_auth_info={
                "credential_username": settings.BKREPO_USERNAME,
                "credential_password": settings.BKREPO_PASSWORD,
            },
            access_params={"base_url": settings.BKREPO_ENDPOINT_URL},
        )
        logger.info("auto_create_bkjob_service success")
