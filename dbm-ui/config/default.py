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
from pathlib import Path
from typing import Dict

import pymysql
from bkcrypto import constants
from bkcrypto.asymmetric.options import RSAAsymmetricOptions, SM2AsymmetricOptions
from bkcrypto.symmetric.options import AESSymmetricOptions, SM4SymmetricOptions
from blueapps.conf.default_settings import *  # pylint: disable=wildcard-import
from blueapps.core.celery.celery import app

from backend import env
from backend.core.encrypt.interceptors import SymmetricInterceptor

if env.RUN_VER == "open":
    from blueapps.patch.settings_open_saas import *  # pylint: disable=wildcard-import
else:
    from blueapps.patch.settings_paas_services import *  # pylint: disable=wildcard-import


# django 3.2 默认的 default_auto_field 是 BigAutoField，django_celery_beat 在 2.2.1 版本已处理此问题
# 受限于 celery 和 bamboo 的版本，这里暂时这样手动设置 default_auto_field 来处理此问题
from django_celery_beat.apps import AppConfig
AppConfig.default_auto_field = "django.db.models.AutoField"

pymysql.install_as_MySQLdb()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

APP_CODE = env.APP_CODE
SECRET_KEY = env.SECRET_KEY
ENVIRONMENT = env.ENVIRONMENT

CONF_PATH = os.path.abspath(__file__)
PROJECT_ROOT = os.path.dirname(os.path.dirname(CONF_PATH))

# 敏感参数,记录请求参数时需剔除
SENSITIVE_PARAMS = ["app_code", "app_secret", "bk_app_code", "bk_app_secret"]

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

ALLOWED_HOSTS = ["*"]

INSTALLED_APPS += (
    "django_celery_beat",
    "whitenoise.runserver_nostatic",
    "rest_framework",
    "django_comment_migrate",
    "django_extensions",
    "drf_yasg",
    "crispy_forms",
    "django_filters",
    # version log
    "backend.version_log",
    # bk_notice
    "bk_notice_sdk",
    # pipeline
    "pipeline.component_framework",
    "pipeline.eri",
    # bk-iam
    "backend.iam_app",
    "iam.contrib.iam_migration",
    # bk-audit
    "bk_audit.contrib.bk_audit",
    # apm
    "blueapps.opentelemetry.instrument_app",
    # backend
    "backend.core.storages",
    "backend.core.encrypt",
    "backend.core.translation",
    "backend.db_services.mysql",
    "backend.configuration",
    "backend.ticket",
    "backend.db_package",
    "backend.flow",
    "backend.flow.plugins",
    "backend.db_meta.apps.DBMeta",
    "backend.db_services.dbpermission.db_authorize",
    "backend.db_services.mysql.permission.clone",
    "backend.db_services.mysql.open_area",
    "backend.db_services.ipchooser",
    "backend.dbm_init",
    "backend.dbm_tools",
    "backend.db_proxy",
    "backend.db_monitor",
    "backend.db_services.redis.redis_dts",
    "backend.db_services.redis.rollback",
    "backend.db_services.redis.autofix",
    "backend.db_dirty",
    "apigw_manager.apigw",
    "backend.db_periodic_task",
    "backend.db_report",
    "backend.db_services.redis.slots_migrate",
    "backend.db_services.mysql.dumper",
)


MIDDLEWARE = (
    # 接口耗时调试工具
    # "pyinstrument.middleware.ProfilerMiddleware",

    # JWT认证，透传的应用信息，透传的用户信息
    "apigw_manager.apigw.authentication.ApiGatewayJWTGenericMiddleware",
    "apigw_manager.apigw.authentication.ApiGatewayJWTAppMiddleware",
    "apigw_manager.apigw.authentication.ApiGatewayJWTUserMiddleware",
    # request instance provider
    "blueapps.middleware.request_provider.RequestProvider",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    # 跨域检测中间件， 默认关闭
    # 'django.middleware.clickjacking.XFrameOptionsMiddleware',
    "django.middleware.security.SecurityMiddleware",
    # 蓝鲸静态资源服务
    "whitenoise.middleware.WhiteNoiseMiddleware",
    # Auth middleware
    "blueapps.account.middlewares.RioLoginRequiredMiddleware",
    "blueapps.account.middlewares.WeixinLoginRequiredMiddleware",
    # "blueapps.account.middlewares.LoginRequiredMiddleware",
    "backend.bk_web.middleware.DBMLoginRequiredMiddleware",
    # exception middleware
    "blueapps.core.exceptions.middleware.AppExceptionMiddleware",
    # django国际化中间件
    "django.middleware.locale.LocaleMiddleware",
    "backend.bk_web.middleware.RequestProviderMiddleware",
)

AUTHENTICATION_BACKENDS = [
    *AUTHENTICATION_BACKENDS,
    'apigw_manager.apigw.authentication.UserModelBackend',
]

ROOT_URLCONF = "backend.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "static", BASE_DIR / "staticfiles"],
        "APP_DIRS": True,
        "OPTIONS": {
            "string_if_invalid": "{{%s}}",
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "wsgi.application"

# Database
# https://docs.djangoproject.com/en/3.2/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": os.environ.get("DB_NAME", APP_CODE),
        "USER": os.environ.get("DB_USER", "root"),
        "PASSWORD": os.environ.get("DB_PASSWORD", ""),
        "HOST": os.environ.get("DB_HOST", "127.0.0.1"),
        "PORT": os.environ.get("DB_PORT", "3306"),
        "OPTIONS": {"init_command": "SET default_storage_engine=INNODB", "charset": "utf8mb4"},
        "TEST": {
            "CHARSET": "utf8",
            "COLLATION": "utf8_general_ci",
        },
    },
    "report_db": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": os.environ.get("REPORT_DB_NAME", APP_CODE),
        "USER": os.environ.get("REPORT_DB_USER", "root"),
        "PASSWORD": os.environ.get("REPORT_DB_PASSWORD", ""),
        "HOST": os.environ.get("REPORT_DB_HOST", "127.0.0.1"),
        "PORT": os.environ.get("REPORT_DB_PORT", "3306"),
        "OPTIONS": {"init_command": "SET default_storage_engine=INNODB", "charset": "utf8mb4"},
        "TEST": {
            "CHARSET": "utf8",
            "COLLATION": "utf8_general_ci",
        },
    }
}

DATABASE_ROUTERS = ["backend.db_report.database_router.ReportRouter"]

# Cache - 缓存后端采用redis
# https://docs.djangoproject.com/en/3.2/ref/settings/#cache
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": env.REDIS_URL,
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "REDIS_CLIENT_CLASS": "redis.client.StrictRedis",
            "REDIS_CLIENT_KWARGS": {"decode_responses": True},
            "SERIALIZER": "backend.utils.redis.JSONSerializer",
        },
    },
    "login_db": {"BACKEND": "django.core.cache.backends.db.DatabaseCache", "LOCATION": "account_cache"},
}

# blueapps
BK_COMPONENT_API_URL = env.BK_COMPONENT_API_URL
BK_SAAS_HOST = env.BK_SAAS_HOST
IS_AJAX_PLAIN_MODE = True

# init admin list
INIT_SUPERUSER = ["admin"]

DJANGO_REDIS_CONNECTION_FACTORY = "backend.utils.redis.ConnectionFactory"

RUN_VER = env.RUN_VER
BK_PAAS_HOST = os.getenv("BK_PAAS_HOST", "")

# IAM Settings
# https://github.com/TencentBlueKing/iam-python-sdk/blob/master/docs/usage.md
BK_IAM_SKIP = env.BK_IAM_SKIP
BK_IAM_INNER_HOST = env.BK_IAM_INNER_HOST
BK_IAM_SYSTEM_ID = env.BK_IAM_SYSTEM_ID
BK_IAM_USE_APIGATEWAY = env.BK_IAM_USE_APIGATEWAY
BK_IAM_APIGATEWAY_URL = env.BK_IAM_APIGATEWAY
BK_IAM_MIGRATION_APP_NAME = "iam_app"
BK_IAM_MIGRATION_JSON_PATH = "backend/iam_app/migration_json_files"
BK_IAM_RESOURCE_API_HOST = env.BK_IAM_RESOURCE_API_HOST

# BK-AUDIT 审计中心配置，见 https://github.com/TencentBlueKing/bk-audit-python-sdk/tree/master
BK_AUDIT_SETTINGS = {
    "formatter": "bk_audit.contrib.django.formatters.DjangoFormatter",
}

# apm 配置
ENABLE_OTEL_TRACE = env.ENABLE_OTEL_TRACE
BK_APP_OTEL_INSTRUMENT_DB_API = env.BK_APP_OTEL_INSTRUMENT_DB_API  # 是否开启 DB 访问 trace（开启后 span 数量会明显增多）


# BAMBOO PIPELINE 配置
AUTO_UPDATE_COMPONENT_MODELS = False

# APIGW 蓝鲸网关配置
BK_APIGW_STATIC_VERSION = env.BK_APIGW_STATIC_VERSION
BK_APIGW_MANAGER_MAINTAINERS = env.BK_APIGW_MANAGER_MAINTAINERS
BK_APIGW_STAGE_NAME = env.BK_APIGW_STAGE_NAME
BK_APIGATEWAY_DOMAIN = env.BK_APIGATEWAY_DOMAIN
BK_API_URL_TMPL = env.BK_API_URL_TMPL
BK_APIGW_NAME = "bkdbm"
BK_APIGW_GRANT_APPS = env.BK_APIGW_GRANT_APPS
# TODO: apigw文档待补充
BK_APIGW_RESOURCE_DOCS_BASE_DIR = env.BK_APIGW_RESOURCE_DOCS_BASE_DIR

BK_NOTICE = {
    "BK_API_URL_TMPL": BK_API_URL_TMPL,
}

# 需将 bkapi.example.com 替换为真实的云 API 域名，在 PaaS 3.0 部署的应用，可从环境变量中获取 BK_API_URL_TMPL

# Password validation
# https://docs.djangoproject.com/en/3.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

# Internationalization
# https://docs.djangoproject.com/en/3.2/topics/i18n/

# 国际化相关配置
LANGUAGE_CODE = "zh-cn"
USE_I18N = True
USE_L10N = True
LOCALURL_USE_ACCEPT_LANGUAGE = True
LANGUAGE_COOKIE_NAME = "blueking_language"
LANGUAGE_SESSION_KEY = "blueking_language"

# 设定使用根目录的locale
LOCALE_PATHS = (os.path.join(PROJECT_ROOT, "locale"),)

TIME_ZONE = "Etc/GMT-8"

USE_TZ = True

SITE_URL = "/"

# Static storages (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/3.2/howto/static-files/
SECURE_CONTENT_TYPE_NOSNIFF = False

STATIC_URL = "static/"

STATIC_ROOT = BASE_DIR / "static"

# STATICFILES_DIRS = [os.path.join(BASE_DIR / "staticfiles")]

STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# Default primary key field type
# https://docs.djangoproject.com/en/3.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# session 配置
SESSION_COOKIE_NAME = "dbm_sessionid"
CSRF_COOKIE_NAME = "dbm_csrftoken"

SESSION_COOKIE_DOMAIN = env.SESSION_COOKIE_DOMAIN
CSRF_COOKIE_DOMAIN = SESSION_COOKIE_DOMAIN

# request_id 的头
REQUEST_ID_HEADER = "HTTP_X_REQUEST_ID"

APIGW_PUBLIC_KEY = env.APIGW_PUBLIC_KEY

# DRF 配置
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        # "backend.bk_web.authentication.BKTicketAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": ["backend.iam_app.handlers.drf_perm.base.IsAuthenticatedPermission"],
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
    "DEFAULT_RENDERER_CLASSES": [
        "backend.bk_web.renderers.BKAPIRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.LimitOffsetPagination",
    "PAGE_SIZE": 10,
    "DATETIME_FORMAT": None,
    "TEST_REQUEST_DEFAULT_FORMAT": "json",
    "EXCEPTION_HANDLER": "backend.bk_web.handlers.drf_exception_handler",
}
USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

SPECTACULAR_SETTINGS = {"COMPONENT_SPLIT_REQUEST": True}

# DJANGO CELERY BEAT
CELERYBEAT_SCHEDULER = 'django_celery_beat.schedulers.DatabaseScheduler'
# CELERY 配置，申明任务的文件路径，即包含有 @task 装饰器的函数文件
CELERY_IMPORTS = (
    "backend.db_periodic_task.local_tasks",
    # TODO: 等celery service服务正式启动后，开启remote_tasks的注册
    # "backend.db_periodic_task.remote_tasks",
)

# celery 配置
app.conf.enable_utc = False
app.conf.timezone = "Asia/Shanghai"
app.conf.broker_url = env.BROKER_URL

# 版本日志
VERSION_LOG = {"MD_FILES_DIR": os.path.join(PROJECT_ROOT, "release")}


def get_logging_config(log_dir: str, log_level: str = "ERROR") -> Dict:
    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "verbose": {
                "format": "%(levelname)s [%(asctime)s] [%(request_id)s] %(name)s %(pathname)s %(lineno)d %(funcName)s "
                "%(process)d %(thread)d \n \t %(message)s \n",
                # noqa
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
            "simple": {"format": "%(levelname)s [%(asctime)s] [%(filename)s:%(lineno)d] %(message)s"},
            "json": {"class": "backend.flow.engine.logger.jsonfmt.JSONFormatter"},
        },
        "filters": {
            "request_id": {"()": "backend.utils.log.RequestIdFilter"},
        },
        "handlers": {
            "null": {
                "level": "DEBUG",
                "class": "logging.NullHandler",
            },
            "console": {
                "level": "DEBUG",
                "class": "logging.StreamHandler",
                "formatter": "verbose",
                "filters": ["request_id"],
            },
            "flow": {
                "level": "DEBUG",
                "class": "logging.StreamHandler",
                "formatter": "json",
                # 'filters': ['node_id'],
            },
            "app": {
                # "class": "logging.handlers.RotatingFileHandler",
                "class": "logging.StreamHandler",
                "level": log_level,
                "formatter": "verbose",
                # "filename": os.path.join(log_dir, f"{APP_CODE}.log"),
                "filters": ["request_id"],
                # "maxBytes": log_max_bytes,
                # "backupCount": log_backup_count,
            },
        },
        "loggers": {
            "root": {"level": "DEBUG", "handlers": ["console"], "propagate": False},
            "flow": {"level": "DEBUG", "handlers": ["flow"], "propagate": False},
        },
    }


LOG_LEVEL = "ERROR"

BK_LOG_DIR = os.getenv("BK_LOG_DIR", "/data/apps/logs/")

# ==============================================================================
# 文件存储
# ==============================================================================
# 用于控制默认的文件存储类型
STORAGE_TYPE = env.STORAGE_TYPE
# 是否覆盖同名文件
FILE_OVERWRITE = env.FILE_OVERWRITE
BKREPO_USERNAME = env.BKREPO_USERNAME
BKREPO_PASSWORD = env.BKREPO_PASSWORD
BKREPO_PROJECT = env.BKREPO_PROJECT
# 默认文件存放仓库
BKREPO_BUCKET = env.BKREPO_BUCKET
# 对象存储平台域名
BKREPO_ENDPOINT_URL = env.BKREPO_ENDPOINT_URL
BKREPO_SSL_PATH = env.BKREPO_SSL_PATH

# 存储类型 - storage class 映射关系
STORAGE_TYPE_IMPORT_PATH_MAP = {
    "FILE_SYSTEM": "backend.core.storages.storage.AdminFileSystemStorage",
    "BLUEKING_ARTIFACTORY": "backend.core.storages.storage.CustomBKRepoStorage",
}

# 对称/非对称加密算法
BKCRYPTO = {
    # 声明项目所使用的非对称加密算法
    "ASYMMETRIC_CIPHER_TYPE": env.ASYMMETRIC_CIPHER_TYPE,
    # 声明项目所使用的对称加密算法
    "SYMMETRIC_CIPHER_TYPE": env.SYMMETRIC_CIPHER_TYPE,
    "SYMMETRIC_CIPHERS": {
        # default - 所配置的对称加密实例，根据项目需要可以配置多个
        "default": {
            # 可选，用于在 settings 没法直接获取 key 的情况
            # "get_key_config": "apps.utils.encrypt.key.get_key_config",
            # 可选，用于 ModelField，加密时携带该前缀入库，解密时分析该前缀并选择相应的解密算法
            # ⚠️ 前缀和 cipher type 必须一一对应，且不能有前缀匹配关系
            # "db_prefix_map": {
            #     SymmetricCipherType.AES.value: "aes_str:::",
            #     SymmetricCipherType.SM4.value: "sm4_str:::"
            # },
            # 公共参数配置，不同 cipher 初始化时共用这部分参数
            "common": {"key": env.SECRET_KEY},
            "cipher_options": {
                # ⚠️这里的配置项为了兼容以前AES的加密模式，如果是新部署的环境可自行修改
                constants.SymmetricCipherType.AES.value: AESSymmetricOptions(
                    key_size=16,
                    iv=env.SECRET_KEY[:16].encode("utf-8"),
                    mode=constants.SymmetricMode.CBC,
                    interceptor=SymmetricInterceptor
                ),
                # 蓝鲸推荐配置
                constants.SymmetricCipherType.SM4.value: SM4SymmetricOptions(
                    mode=constants.SymmetricMode.CTR, key=env.SECRET_KEY
                )
            }
        },
    },
    "ASYMMETRIC_CIPHERS": {
        # 配置同 SYMMETRIC_CIPHERS
        "default": {
            "cipher_options": {
                constants.AsymmetricCipherType.RSA.value: RSAAsymmetricOptions(
                    padding=constants.RSACipherPadding.PKCS1_v1_5
                ),
                constants.AsymmetricCipherType.SM2.value: SM2AsymmetricOptions()
            },
        },
    }
}

# 默认的file storage
DEFAULT_FILE_STORAGE = STORAGE_TYPE_IMPORT_PATH_MAP[STORAGE_TYPE]

# 并发数
CONCURRENT_NUMBER = 10

# grafana代理配置
BACKEND_DIR = os.path.join(BASE_DIR, "backend/bk_dataview")
GRAFANA = {
    "HOST": env.GRAFANA_URL,
    "PREFIX": "/grafana",
    "ADMIN": ("admin", "admin"),
    "AUTHENTICATION_CLASSES": [
        "backend.bk_dataview.grafana.authentication.SessionAuthentication",
        # "backend.bk_web.authentication.BKTicketAuthentication",
    ],
    "PERMISSION_CLASSES": ["backend.bk_dataview.grafana.permissions.IsAuthenticated"],
    "PROVISIONING_CLASSES": ["backend.bk_dataview.grafana.provisioning.SimpleProvisioning"],
    "PROVISIONING_PATH": os.path.join(BASE_DIR, "backend/bk_dataview"),
    "CODE_INJECTIONS": {
        "<head>": """<head>
            <style>
                .page-toolbar>div:nth-child(-n+1) { display: none }
                nav.page-toolbar > div:last-child { display: none }
                .sidemenu {
                    display: none !important;
                }
                .navbar-page-btn .gicon-dashboard {
                    display: none !important;
                }
                .navbar .navbar-buttons--tv {
                    display: none !important;
                }
            </style>
        """
    },
    "BACKEND_CLASS": "backend.bk_dataview.grafana.backends.api.APIHandler",
}


# 全局启用 pyinstrument，或者在url后面加上?profile=1
# PYINSTRUMENT_PROFILE_DIR = os.path.join(STATIC_ROOT, 'assets/perf')
