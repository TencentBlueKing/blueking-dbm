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
import datetime
import json
import logging
import os
import subprocess

from bk_notice_sdk.views import api_call
from blueapps.account.models import User
from django.conf import settings
from django.core.management import call_command
from django.http import HttpRequest
from django.utils import timezone

from backend import env
from backend.bk_dataview.grafana.views import SwitchOrgView
from backend.components import BKMonitorV3Api, CCApi, ItsmApi
from backend.components.constants import SSL_KEY
from backend.configuration.constants import DBM_REPORT_INITIAL_VALUE, SystemSettingsEnum
from backend.configuration.models.system import SystemSettings
from backend.core.storages.constants import FileCredentialType, StorageType
from backend.core.storages.file_source import BkJobFileSourceManager
from backend.core.storages.storage import get_storage
from backend.db_meta.models import AppMonitorTopo
from backend.db_monitor.utils import create_bklog_collector, create_bkmonitor_action
from backend.db_services.cmdb.biz import get_or_create_cmdb_module_with_name, get_or_create_set_with_name
from backend.db_services.ipchooser.constants import DB_MANAGE_SET, DEFAULT_CLOUD, DIRTY_MODULE, RESOURCE_MODULE
from backend.dbm_init.constants import CC_APP_ABBR_ATTR, CC_HOST_DBM_ATTR
from backend.exceptions import ApiError
from backend.iam_app.dataclass import generate_iam_migration_json
from backend.utils.time import datetime2str

logger = logging.getLogger("root")


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
        dbm_service_name = dbm_service_json["name"]
        for_update = dbm_service_json.pop("for_update", False)
        dbm_service_id = 0

        try:
            if dbm_service_name not in children_services_map.keys():
                # 服务不存在则创建服务
                dbm_service_id = ItsmApi.import_service(params=dbm_service_json, use_admin=True)["id"]
                logger.info("itsm服务创建成功，服务id为: %s", dbm_service_id)
            elif for_update:
                # 服务存在则更新服务
                dbm_service_id = children_services_map[dbm_service_name]
                dbm_service_json["id"] = dbm_service_id
                ItsmApi.update_service(params=dbm_service_json, use_admin=True)
                logger.info("itsm服务更新成功，服务id为: %s", dbm_service_id)
        except ApiError as e:
            raise Exception("服务创建/更新失败，请联系管理员。错误信息: %s", e)

        # 更新到系统配置中
        if dbm_service_id:
            SystemSettings.insert_setting_value(
                key=SystemSettingsEnum.BK_ITSM_SERVICE_ID.value, value=str(dbm_service_id)
            )
            logger.info("服务创建/更新成功")
        else:
            logger.info("本次更新跳过...")
        return dbm_service_id

    @staticmethod
    def auto_create_bklog_service(startswith: str = "") -> bool:
        """
        创建/更新 日志平台 采集项
        """
        create_bklog_collector(startswith=startswith)
        return True

    @staticmethod
    def init_cc_dbm_meta(bk_biz_id=env.DBA_APP_BK_BIZ_ID):

        # 初始化主机自定义属性，用于system数据拷贝
        logger.info("[%s] init cc biz custom field <%s> for monitor's dbm_system copy.", bk_biz_id, CC_HOST_DBM_ATTR)
        model_attrs = CCApi.search_object_attribute(
            {
                "bk_biz_id": bk_biz_id,
                "bk_obj_id": "host",
            },
            use_admin=True,
        )

        exist_dbm_attr = [attr for attr in model_attrs if attr["bk_property_id"] == CC_HOST_DBM_ATTR]
        if exist_dbm_attr:
            logger.info("skip exist dbm attr in host model")
            return True
        resp = CCApi.create_biz_custom_field(
            {
                "bk_biz_id": bk_biz_id,
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
            raw=True,
        )
        if resp.get("result"):
            return

        # 已经存在，忽略即可
        if resp.get("code") in [CCApi.ErrorCode.CUSTOM_FIELD_ALREADY_EXISTS, CCApi.ErrorCode.TASK_ALREADY_EXISTS]:
            logger.warning(f"create_biz_custom_field({CC_HOST_DBM_ATTR}), resp:{resp}")
        else:
            raise ApiError(f"create_biz_custom_field({CC_HOST_DBM_ATTR}) error, resp:{resp}")

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

        # 初始化db的管理集群和相关模块
        if not SystemSettings.get_setting_value(key=SystemSettingsEnum.MANAGE_TOPO.value):
            # 创建管理集群
            manage_set_id = get_or_create_set_with_name(bk_biz_id=env.DBA_APP_BK_BIZ_ID, bk_set_name=DB_MANAGE_SET)
            # 创建资源池模块和污点池模块
            manage_modules = [RESOURCE_MODULE, DIRTY_MODULE]
            module_name__module_id = {}
            for module in manage_modules:
                module_id = get_or_create_cmdb_module_with_name(
                    bk_biz_id=env.DBA_APP_BK_BIZ_ID, bk_set_id=manage_set_id, bk_module_name=module
                )
                module_name__module_id[module] = module_id
            # 插入管理集群的配置
            SystemSettings.insert_setting_value(
                key=SystemSettingsEnum.MANAGE_TOPO.value,
                value_type="dict",
                value={
                    "set_id": manage_set_id,
                    "resource_module_id": module_name__module_id[RESOURCE_MODULE],
                    "dirty_module_id": module_name__module_id[DIRTY_MODULE],
                },
            )

        # 初始化主机自定义属性，用于system数据拷贝
        Services.init_cc_dbm_meta()

        # 为业务模型增加dbm_app_abbr字段
        logger.info("init cc db_app_abbr for english app")
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
                "bk_biz_id": env.DBA_APP_BK_BIZ_ID,
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
                "bk_biz_id": env.DBA_APP_BK_BIZ_ID,
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
        end = datetime.datetime.now(timezone.utc)
        start = end - datetime.timedelta(hours=1)
        res = BKMonitorV3Api.get_custom_event_group(
            {
                "time_range": "{} -- {}".format(datetime2str(start), datetime2str(end)),
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

        # 上报地址
        proxies = BKMonitorV3Api.proxy_host_info({"bk_biz_id": env.DBA_APP_BK_BIZ_ID})
        for proxy in proxies:
            if proxy["bk_cloud_id"] == DEFAULT_CLOUD:
                DBM_REPORT_INITIAL_VALUE["proxy"] = f'http://{proxy["ip"]}:{proxy["port"]}/v2/push/'
                break

        logger.info("init_custom_metric_and_event: %s", DBM_REPORT_INITIAL_VALUE)
        SystemSettings.objects.update_or_create(
            defaults={
                "value": DBM_REPORT_INITIAL_VALUE,
                "type": "dict",
                "creator": "system",
                "updater": "system",
            },
            key=SystemSettingsEnum.BKM_DBM_REPORT.value,
        )

    @staticmethod
    def auto_create_bkmonitor_alarm() -> bool:
        """初始化bkmonitor配置"""
        from backend.db_monitor.models import CollectInstance, MonitorPolicy

        logger.info("auto_create_bkmonitor_service")

        action_id = create_bkmonitor_action()

        # 加载采集策略
        CollectInstance.sync_collect_strategy()

        # 加载告警策略
        MonitorPolicy.sync_plat_monitor_policy(action_id=action_id)

        return True

    @staticmethod
    def auto_create_bkmonitor_channel() -> bool:
        """初始化自定义上报通道"""

        Services.init_custom_metric_and_event()

        return True

    @staticmethod
    def auto_init_grafana() -> bool:
        request = HttpRequest()
        user = User.objects.filter(is_superuser=True).first()
        if user is None:
            return False
        request.user = User.objects.filter(is_superuser=True).first()
        request.org_name = "dbm"
        SwitchOrgView().initial(request)
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
        SystemSettings.insert_setting_value(key=SystemSettingsEnum.DBM_SSL.value, value=dbm_ssl)

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

    @classmethod
    def auto_register_application(cls):
        """初始化注册 dbm 到通知中心"""
        try:
            response = api_call(
                api_method="register_application", success_message="注册平台成功", error_message="注册平台异常", success_code=201
            )
            if response.get("result") is True:
                logger.info("dbm成功注册平台到通知中心")
            else:
                logger.info("dbm注册平台失败:" + response["message"])
        except Exception as e:
            logger.info("dbm注册平台异常: %s" % str(e))

    @classmethod
    def auto_create_iam_migrations(cls):
        """自动注册iam"""
        try:
            generate_iam_migration_json(json_name="initial.json")
            call_command("iam_makemigrations", "initial.json")
        except Exception as e:
            logger.info("dbm生成iam模型异常: %s" % str(e))
