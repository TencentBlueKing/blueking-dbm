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
from .bkrepo import *  # pylint: disable=wildcard-import

APP_CODE = get_type_env(key="APP_ID", default="bk-dbm", _type=str)
SECRET_KEY = get_type_env(key="APP_TOKEN", default="yb2gur=g)hxbmpk3#b%ez5_#6o!tf9vkqsnwo4dxyr0n&w3=9k", _type=str)
DEFAULT_USERNAME = get_type_env(key="DEFAULT_USERNAME", default="admin", _type=str)

RUN_VER = get_type_env(key="RUN_VER", default="open", _type=str)

# Redis 配置
REDIS_HOST = get_type_env(key="REDIS_HOST", _type=str, default="localhost")
REDIS_PORT = get_type_env(key="REDIS_PORT", _type=int, default=6379)
REDIS_PASSWORD = get_type_env(key="REDIS_PASSWORD", _type=str, default="")
REDIS_URL = f"redis://{f':{REDIS_PASSWORD}@' if REDIS_PASSWORD else ''}{REDIS_HOST}:{REDIS_PORT}/1"

BROKER_URL = get_type_env(key="BROKER_URL", default=REDIS_URL, _type=str)
SESSION_COOKIE_DOMAIN = get_type_env(key="SESSION_COOKIE_DOMAIN", default="", _type=str)

# CC业务模型中的英文业务简称
BK_APP_ABBR = get_type_env(key="BK_APP_ABBR", _type=str, default="")

# 蓝鲸全业务业务ID
JOB_BLUEKING_BIZ_ID = get_type_env(key="JOB_BLUEKING_BIZ_ID", _type=int, default=9991001)

# DBM 系统在 CMDB 中的业务ID
DBA_APP_BK_BIZ_ID = get_type_env(key="DBA_APP_BK_BIZ_ID", _type=int)

# esb 访问地址
BK_COMPONENT_API_URL = get_type_env(key="BK_COMPONENT_API_URL", _type=str, default="https://bk-component.example.com")

# ITSM 服务ID
BK_ITSM_PROJECT_KEY = get_type_env(key="BK_ITSM_PROJECT_KEY", _type=str, default="0")

# IAM 相关配置
BK_IAM_SYSTEM_ID = "bk_dbm"  # BK_IAM_SYSTEM_ID固定为bk_dbm，不可更改
BK_IAM_SKIP = get_type_env(key="BK_IAM_SKIP", _type=bool, default=False)
BK_IAM_SYSTEM_NAME = get_type_env(key="BK_IAM_SYSTEM_NAME", _type=str, default="DB管理平台")
BK_IAM_INNER_HOST = get_type_env(key="BK_IAM_V3_INNER_HOST", _type=str, default="https://iam-inner.example.com")
BK_IAM_USE_APIGATEWAY = True
BK_IAM_APIGATEWAY = get_type_env(key="BK_IAM_APIGATEWAY", _type=str, default="https://iam-apigw.example.com")
IAM_APP_URL = get_type_env(key="IAM_APP_URL", _type=str, default="https://iam.example.com")
BK_IAM_RESOURCE_API_HOST = get_type_env(key="BK_IAM_RESOURCE_API_HOST", _type=str, default="https://bkdbm.example.com")

# APIGW 相关配置
BK_APIGATEWAY_DOMAIN = get_type_env(key="BK_APIGATEWAY_DOMAIN", _type=str, default=BK_COMPONENT_API_URL)
BK_APIGW_STATIC_VERSION = get_type_env(key="BK_APIGW_STATIC_VERSION", _type=str, default="1.0.0")
BK_APIGW_MANAGER_MAINTAINERS = get_type_env(key="BK_APIGW_MANAGER_MAINTAINERS", _type=list, default=["admin"])
BK_APIGW_STAGE_NAME = get_type_env(key="BK_APIGW_STAGE_NAME", _type=str, default="test")
BK_APIGW_GRANT_APPS = get_type_env(key="BK_APIGW_GRANT_APPS", _type=list, default=[])
BK_APIGW_RESOURCE_DOCS_ARCHIVE_FILE = get_type_env(key="BK_APIGW_RESOURCE_DOCS_ARCHIVE_FILE", _type=str)

ENVIRONMENT = get_type_env(key="BKPAAS_ENVIRONMENT", default="prod", _type=str)

# SaaS访问地址，用于用户访问/第三方应用跳转/Iframe/Grafana 等场景
BK_SAAS_HOST = get_type_env(key="BK_SAAS_HOST", _type=str, default="http://bk-dbm")
# BK_SAAS_CALLBACK_URL 用于 接口回调/权限中心访问 等场景
BK_SAAS_CALLBACK_URL = (
    # 通常因证书问题，这里需要使用 http
    get_type_env(key="BK_SAAS_CALLBACK_URL", _type=str, default="")
    or BK_SAAS_HOST.replace("https", "http")
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

# 跳过审批开关，默认关闭，方便本地联调
ITSM_FLOW_SKIP = get_type_env(key="ITSM_FLOW_SKIP", _type=str, default=False)

# 名字服务北极星部门字段
NAMESERVICE_POLARIS_DEPARTMENT = get_type_env(key="NAMESERVICE_POLARIS_DEPARTMENT", _type=str, default="")
# 名字服务添加clb域名
CLB_DOMAIN = get_type_env(key="CLB_DOMAIN", _type=bool, default=False)

# 标准运维SA 空闲检查任务模版ID
SA_CHECK_TEMPLATE_ID = get_type_env(key="SA_CHECK_TEMPLATE_ID", _type=int)

# 标准运维SA 初始化任务模版ID
SA_INIT_TEMPLATE_ID = get_type_env(key="SA_INIT_TEMPLATE_ID", _type=int)

# 标准运维SA 初始化任务模版ID
YUM_INSTALL_PERL = get_type_env(key="YUM_INSTALL_PERL", _type=bool, default=False)


# 内嵌grafana地址
GRAFANA_URL = get_type_env(key="GRAFANA_URL", _type=str, default="")

# grafana监控数据源地址
BKMONITOR_URL = get_type_env(key="BKMONITOR_URL", _type=str, default="")

# mysql-crond 相关
MYSQL_CROND_BEAT_PATH = get_type_env(
    key="MYSQL_CROND_BEAT_PATH", _type=str, default="/usr/local/gse_bkte/plugins/bin/bkmonitorbeat"
)
MYSQL_CROND_AGENT_ADDRESS = get_type_env(
    key="MYSQL_CROND_AGENT_ADDRESS", _type=str, default="/usr/local/gse_bkte/agent/data/ipc.state.report"
)

# 云区域服务部署
DRS_PORT = get_type_env(key="DRS_PORT", _type=int, default=8888)
DBM_PORT = get_type_env(key="DRS_PORT", _type=int, default=80)
MANAGE_PORT = get_type_env(key="DRS_PORT", _type=int, default=8080)
# nginx转发dbm的地址(如果没有则取BK_SAAS_HOST)
DBM_EXTERNAL_ADDRESS = get_type_env(key="DBM_EXTERNAL_ADDRESS", _type=str, default=BK_SAAS_HOST)

APIGW_PUBLIC_KEY = get_type_env(key="APIGW_PUBLIC_KEY", _type=str, default="")

# 云区域组件旁路配置
DRS_SKIP_SSL = get_type_env(key="DRS_SKIP_SSL", _type=bool, default=False)
DOMAIN_SKIP_PROXY = get_type_env(key="DOMAIN_SKIP_PROXY", _type=bool, default=False)
DRS_USERNAME = get_type_env(key="DRS_USERNAME", _type=str, default="")
DRS_PASSWORD = get_type_env(key="DRS_PASSWORD", _type=str, default="")
DBHA_USERNAME = get_type_env(key="DBHA_USERNAME", _type=str, default="")
DBHA_PASSWORD = get_type_env(key="DBHA_PASSWORD", _type=str, default="")
TEST_ACCESS_HOSTS = get_type_env(key="TEST_ACCESS_HOSTS", _type=list, default=[])

# 版本号
APP_VERSION = get_type_env(key="APP_VERSION", _type=str, default="")
CHART_VERSION = get_type_env(key="CHART_VERSION", _type=str, default="")

# 资源池伪造开关
FAKE_RESOURCE_APPLY_ENABLE = get_type_env(key="FAKE_RESOURCE_APPLY_ENABLE", _type=bool, default=False)
# 资源池是否支持亲和性(暂不支持)
RESOURCE_SUPPORT_AFFINITY = get_type_env(key="RESOURCE_SUPPORT_AFFINITY", _type=bool, default=False)

# Agent版本: 1.0/2.0
GSE_AGENT_VERSION = get_type_env(key="GSE_AGENT_VERSION", _type=str, default="1.0")

# 后端加密算法
ASYMMETRIC_CIPHER_TYPE = get_type_env(key="ASYMMETRIC_CIPHER_TYPE", _type=str, default=AsymmetricCipherType.RSA.value)
SYMMETRIC_CIPHER_TYPE = get_type_env(key="SYMMETRIC_CIPHER_TYPE", _type=str, default=SymmetricCipherType.AES.value)
