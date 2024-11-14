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
from bkcrypto.constants import AsymmetricCipherType, SymmetricCipherType

from .apigw_domains import *  # pylint: disable=wildcard-import
from .apm import *  # pylint: disable=wildcard-import
from .bklog import *  # pylint: disable=wildcard-import
from .bkrepo import *  # pylint: disable=wildcard-import
from .dev import *  # pylint: disable=wildcard-import
from .nameservice import *  # pylint: disable=wildcard-import
from .sync_meta import *  # pylint: disable=wildcard-import

APP_CODE = get_type_env(key="APP_ID", default="bk-dbm", _type=str)
SECRET_KEY = get_type_env(key="APP_TOKEN", default="xxxx", _type=str)
DEFAULT_USERNAME = get_type_env(key="DEFAULT_USERNAME", default="admin", _type=str)
# 环境允许跨域的域名
CORS_ALLOWED_ORIGINS = get_type_env(key="CORS_ALLOWED_ORIGINS", default=[], _type=list)

RUN_VER = get_type_env(key="RUN_VER", default="open", _type=str)
RIO_TOKEN = get_type_env(key="RIO_TOKEN", default="", _type=str)

# Redis 配置
REDIS_HOST = get_type_env(key="REDIS_HOST", _type=str, default="localhost")
REDIS_PORT = get_type_env(key="REDIS_PORT", _type=int, default=6379)
REDIS_PASSWORD = get_type_env(key="REDIS_PASSWORD", _type=str, default="")
REDIS_URL = f"redis://{f':{REDIS_PASSWORD}@' if REDIS_PASSWORD else ''}{REDIS_HOST}:{REDIS_PORT}/1"

BROKER_URL = get_type_env(key="BROKER_URL", default=REDIS_URL, _type=str)
SESSION_COOKIE_DOMAIN = get_type_env(key="SESSION_COOKIE_DOMAIN", default="", _type=str)

# CC业务模型中的英文业务简称
BK_APP_ABBR = get_type_env(key="BK_APP_ABBR", _type=str, default="")
# CMDB 监控相关字段
CMDB_HOST_STATE_ATTR = get_type_env(key="CMDB_HOST_STATE_ATTR", _type=str, default="bk_state")
CMDB_NO_MONITOR_STATUS = get_type_env(key="CMDB_NO_MONITOR_STATUS", _type=str, default="运营中[无告警]")
CMDB_NEED_MONITOR_STATUS = get_type_env(key="CMDB_NEED_MONITOR_STATUS", _type=str, default="运营中[需告警]")

# 蓝鲸全业务业务ID
JOB_BLUEKING_BIZ_ID = get_type_env(key="JOB_BLUEKING_BIZ_ID", _type=int, default=9991001)

# DBM 系统在 CMDB 中的业务ID
DBA_APP_BK_BIZ_ID = get_type_env(key="DBA_APP_BK_BIZ_ID", _type=int)

# esb 访问地址
BK_COMPONENT_API_URL = get_type_env(key="BK_COMPONENT_API_URL", _type=str, default="https://bk-component.example.com")

# 开启外部路由，供外部环境使用(DBConsole)
ENABLE_EXTERNAL_PROXY = get_type_env(key="ENABLE_EXTERNAL_PROXY", _type=bool, default=False)
# 开启所有路由，不屏蔽。！！这里只用在合作伙伴环境！！
ENABLE_OPEN_EXTERNAL_PROXY = get_type_env(key="ENABLE_OPEN_EXTERNAL_PROXY", _type=bool, default=False)

# ITSM 服务ID
BK_ITSM_PROJECT_KEY = get_type_env(key="BK_ITSM_PROJECT_KEY", _type=str, default="0")

# IAM 相关配置
BK_IAM_SYSTEM_ID = "bk_dbm"  # BK_IAM_SYSTEM_ID固定为bk_dbm，不可更改
BK_IAM_SKIP = get_type_env(key="BK_IAM_SKIP", _type=bool, default=False)
BK_IAM_SYSTEM_NAME = get_type_env(key="BK_IAM_SYSTEM_NAME", _type=str, default="数据库管理")
BK_IAM_INNER_HOST = get_type_env(key="BK_IAM_V3_INNER_HOST", _type=str, default="https://iam-inner.example.com")
BK_IAM_USE_APIGATEWAY = True
BK_IAM_APIGATEWAY = get_type_env(key="BK_IAM_APIGATEWAY", _type=str, default="https://iam-apigw.example.com")
BK_IAM_API_VERSION = get_type_env(key="BK_IAM_API_VERSION", _type=str, default="v1")
IAM_APP_URL = get_type_env(key="IAM_APP_URL", _type=str, default="https://iam.example.com")
BK_IAM_RESOURCE_API_HOST = get_type_env(key="BK_IAM_RESOURCE_API_HOST", _type=str, default="https://bkdbm.example.com")
BK_IAM_GRADE_MANAGER_ID = get_type_env(key="BK_IAM_GRADE_MANAGER_ID", _type=int, default=0)

# APIGW 相关配置
BK_APIGATEWAY_DOMAIN = get_type_env(key="BK_APIGATEWAY_DOMAIN", _type=str, default=BK_COMPONENT_API_URL)
BK_API_URL_TMPL = get_type_env(key="BK_API_URL_TMPL", _type=str, default=f"{BK_APIGATEWAY_DOMAIN}/api/{{api_name}}/")
BK_APIGW_STATIC_VERSION = get_type_env(key="BK_APIGW_STATIC_VERSION", _type=str, default="1.0.0")
BK_APIGW_MANAGER_MAINTAINERS = get_type_env(key="BK_APIGW_MANAGER_MAINTAINERS", _type=list, default=["admin"])
BK_APIGW_STAGE_NAME = get_type_env(key="BK_APIGW_STAGE_NAME", _type=str, default="test")
BK_APIGW_GRANT_APPS = get_type_env(key="BK_APIGW_GRANT_APPS", _type=list, default=[])
BK_APIGW_RESOURCE_DOCS_BASE_DIR = get_type_env(
    key="BK_APIGW_RESOURCE_DOCS_BASE_DIR", _type=str, default="backend/docs/apigw"
)
APIGW_PUBLIC_KEY = get_type_env(key="APIGW_PUBLIC_KEY", _type=str, default="")

ENVIRONMENT = get_type_env(key="BKPAAS_ENVIRONMENT", default="prod", _type=str)

# SaaS访问地址，用于用户访问/第三方应用跳转/Iframe/Grafana 等场景
BK_SAAS_HOST = get_type_env(key="BK_SAAS_HOST", _type=str, default="http://bk-dbm")
# BK_SAAS_CALLBACK_URL 用于 接口回调/权限中心访问 等场景
# 通常因证书问题，这里需要使用 http
BK_SAAS_CALLBACK_URL = get_type_env(key="BK_SAAS_CALLBACK_URL", _type=str, default="") or BK_SAAS_HOST.replace(
    "https", "http"
)

# 其他系统访问地址
BK_DOMAIN = get_type_env(key="BK_DOMAIN", _type=str, default=".example.com")
BK_PAAS_URL = get_type_env(key="BK_PAAS_URL", _type=str, default="http://paas.example.com")
BK_CMDB_URL = get_type_env(key="BK_CMDB_URL", _type=str, default=BK_PAAS_URL.replace("paas", "cmdb"))
BK_JOB_URL = get_type_env(key="BK_JOB_HOST", _type=str, default=None)
BK_NODEMAN_URL = get_type_env(key="BK_NODEMAN_URL", _type=str, default="http://apps.example.com/bk--nodeman")
BK_SCR_URL = get_type_env(key="BK_SCR_URL", _type=str, default="http://scr.example.com")
BK_SOPS_URL = get_type_env(key="BK_SOPS_HOST", _type=str, default=None)
BK_HELPER_URL = get_type_env(key="BK_HELPER_URL", _type=str, default=None)
# 北极星服务
POLARIS_URL = get_type_env(key="POLARIS_URL", _type=str, default="http://polaris.example.com")

# 仅在容器中暴露service，提供内部服务调用，不暴露ingress
SERVICE_ONLY = get_type_env(key="SERVICE_ONLY", _type=str, default=False)

ADMIN_USERS = [u.strip() for u in get_type_env(key="ADMIN_USERS", default="admin", _type=str).split(",") if u]

# 标准运维
# 标准运维SA 空闲检查任务模版ID
SA_CHECK_TEMPLATE_ID = get_type_env(key="SA_CHECK_TEMPLATE_ID", _type=int)
# 标准运维SA 初始化任务模版ID
SA_INIT_TEMPLATE_ID = get_type_env(key="SA_INIT_TEMPLATE_ID", _type=int)
# 标准运维SA 安装L5Agent的模板ID
SA_L5_AGENT_TEMPLATE_ID = get_type_env(key="SA_L5_AGENT_TEMPLATE_ID", _type=int)
# 标准运维项目 ID
BK_SOPS_PROJECT_ID = get_type_env(key="BK_SOPS_PROJECT_ID", _type=int, default=1)

# Bamboo
ENABLE_CLEAN_EXPIRED_BAMBOO_TASK = get_type_env(key="ENABLE_CLEAN_EXPIRED_BAMBOO_TASK", _type=bool, default=False)
ENABLE_CLEAN_EXPIRED_FLOW_INSTANCE = get_type_env(key="ENABLE_CLEAN_EXPIRED_FLOW_INSTANCE", _type=bool, default=False)
BAMBOO_TASK_VALIDITY_DAY = get_type_env(key="BAMBOO_TASK_VALIDITY_DAY", _type=int, default=360)

# 是否在部署 MySQL 的时候安装 PERL
YUM_INSTALL_PERL = get_type_env(key="YUM_INSTALL_PERL", _type=bool, default=False)

# 内嵌grafana地址
GRAFANA_URL = get_type_env(key="GRAFANA_URL", _type=str, default="")

# grafana监控数据源地址
BKMONITOR_URL = get_type_env(key="BKMONITOR_URL", _type=str, default="")

# 监控处理套餐 Bearer Token
BKMONITOR_BEARER_TOKEN = get_type_env(key="BKMONITOR_BEARER_TOKEN", _type=str, default=SECRET_KEY[:16])

# mysql-crond 相关
MYSQL_CROND_BEAT_PATH = get_type_env(
    key="MYSQL_CROND_BEAT_PATH", _type=str, default="/usr/local/gse_bkte/plugins/bin/bkmonitorbeat"
)
MYSQL_CROND_AGENT_ADDRESS = get_type_env(
    key="MYSQL_CROND_AGENT_ADDRESS", _type=str, default="/var/run/ipc.state.report"
)

# 云区域服务部署
DRS_PORT = get_type_env(key="DRS_PORT", _type=int, default=8888)
DBM_PORT = get_type_env(key="DBM_PORT", _type=int, default=80)
MANAGE_PORT = get_type_env(key="MANAGE_PORT", _type=int, default=8080)
# nginx转发dbm的地址(如果没有则取BK_SAAS_HOST)
DBM_EXTERNAL_ADDRESS = get_type_env(key="DBM_EXTERNAL_ADDRESS", _type=str, default=BK_SAAS_HOST)
# 云区域容器化开关
CLOUD_CONTAINER_ENABLE = get_type_env(key="CLOUD_CONTAINER_ENABLE", _type=str, default=False)

# 版本号
APP_VERSION = get_type_env(key="APP_VERSION", _type=str, default="")
CHART_VERSION = get_type_env(key="CHART_VERSION", _type=str, default="")

# 后端加密算法
ASYMMETRIC_CIPHER_TYPE = get_type_env(key="ASYMMETRIC_CIPHER_TYPE", _type=str, default=AsymmetricCipherType.RSA.value)
SYMMETRIC_CIPHER_TYPE = get_type_env(key="SYMMETRIC_CIPHER_TYPE", _type=str, default=SymmetricCipherType.AES.value)

# gcs/scr平台
GCS_SCR_OPERATOR = get_type_env(key="GCS_SCR_OPERATOR", _type=str, default="scr-system")

# 是否启动mysql-dbbackup程序的版本逻辑选择，不启动默认统一安装社区版本
MYSQL_BACKUP_PKG_MAP_ENABLE = get_type_env(key="MYSQL_BACKUP_PKG_MAP_ENABLE", _type=bool, default=False)

# bkdbm 通知机器人的key
WECOM_ROBOT = get_type_env(key="WECOM_ROBOT", _type=str, default="")
MYSQL_CHATID = get_type_env(key="MYSQL_CHATID", _type=str, default="")

# django DebugToolbar是否开启。开启后会对接口进行SQL分析和统计，将大幅度降低接口效率
# 需要开启DEBUG_TOOL_BAR和DEBUG模式，DebugToolbar才会生效
DEBUG_TOOL_BAR = get_type_env(key="DEBUG_TOOL_BAR", _type=bool, default=False)

# window ssh服务远程端口
WINDOW_SSH_PORT = get_type_env(key="WINDOW_SSH_PORT", _type=int, default=22)
# 本地测试人员优先使用的版本
REPO_VERSION_FOR_DEV = get_type_env(key="REPO_VERSION_FOR_DEV", _type=str, default="")
