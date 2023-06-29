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
from datetime import timedelta
from pathlib import Path
from typing import Dict

import pymysql
from blueapps.conf.default_settings import *  # pylint: disable=wildcard-import
from celery.schedules import crontab
from blueapps.core.celery.celery import app
from config import RUN_VER

if RUN_VER == "open":
    from blueapps.patch.settings_open_saas import *  # pylint: disable=wildcard-import
else:
    from blueapps.patch.settings_paas_services import *  # pylint: disable=wildcard-import

from backend import env

pymysql.install_as_MySQLdb()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

APP_CODE = env.APP_CODE
SECRET_KEY = env.SECRET_KEY

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
    # pipeline
    "pipeline.component_framework",
    "pipeline.eri",
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
    "backend.iam_app",
    "iam.contrib.iam_migration",
    "backend.db_services.mysql.permission.authorize",
    "backend.db_services.mysql.permission.clone",
    "backend.db_services.ipchooser",
    "backend.dbm_init",
    "backend.db_proxy",
    "backend.db_monitor",
    "backend.db_services.redis_dts",
    "backend.db_services.redis.rollback",
)


MIDDLEWARE = (
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
    }
}

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
IS_AJAX_PLAIN_MODE = True

# init admin list
INIT_SUPERUSER = ["admin"]

DJANGO_REDIS_CONNECTION_FACTORY = "backend.utils.redis.ConnectionFactory"

RUN_VER = os.getenv("RUN_VER", "open")
BK_PAAS_HOST = os.getenv("BK_PAAS_HOST", "")

# IAM Settings
# https://github.com/TencentBlueKing/iam-python-sdk/blob/master/docs/usage.md
BK_IAM_SKIP = env.BK_IAM_SKIP
BK_IAM_INNER_HOST = env.BK_IAM_INNER_HOST
BK_IAM_SYSTEM_ID = env.BK_IAM_SYSTEM_ID
BK_IAM_USE_APIGATEWAY = True
BK_IAM_APIGATEWAY_URL = env.BK_IAM_APIGETEWAY
BK_IAM_MIGRATION_APP_NAME = "iam_app"
BK_IAM_MIGRATION_JSON_PATH = "backend/iam_app/migration_json_files"
BK_IAM_RESOURCE_API_HOST = env.BK_IAM_RESOURCE_API_HOST

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
    "DEFAULT_PERMISSION_CLASSES": ["backend.iam_app.handlers.drf_perm.IsAuthenticatedOrAPIGateWayPermission"],
    "DEFAULT_FILTER_BACKENDS": ["django_filters.rest_framework.DjangoFilterBackend"],
    "DEFAULT_RENDERER_CLASSES": [
        "backend.bk_web.renderers.BKAPIRenderer",
        "rest_framework.renderers.BrowsableAPIRenderer",
    ],
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.LimitOffsetPagination",
    "PAGE_SIZE": 10,
    "DATETIME_FORMAT": "%Y-%m-%d %H:%M:%S",
    "TEST_REQUEST_DEFAULT_FORMAT": "json",
    "EXCEPTION_HANDLER": "backend.bk_web.handlers.drf_exception_handler",
}
USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

SPECTACULAR_SETTINGS = {"COMPONENT_SPLIT_REQUEST": True}

# 设置时区
app.conf.enable_utc = False
app.conf.timezone = "Asia/Shanghai"
app.conf.beat_schedule = "django_celery_beat.schedulers:DatabaseScheduler"
app.conf.broker_url = env.BROKER_URL

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

app.conf.beat_schedule = {
    "sync-local-notice-group-every-2min": {
        "task": "backend.db_monitor.tasks.update_local_notice_group",
        "schedule": crontab(minute="*/2"),
    },
    "sync-monitor-notice-group-every-3min": {
        "task": "backend.db_monitor.tasks.update_remote_notice_group",
        "schedule": crontab(minute="*/3"),
    },
    "sync-cc-dbmeta-every-2min": {
        "task": "backend.db_meta.tasks.update_host_dbmeta",
        "schedule": crontab(minute="*/2"),
    },
    "update-app-every-20min": {
        "task": "backend.db_meta.tasks.update_app_cache",
        "schedule": crontab(minute="*/20"),
    },
    "auto-retry-exclusive-inner-flow": {
        "task": "backend.ticket.tasks.ticket_tasks.auto_retry_exclusive_inner_flow",
        "schedule": timedelta(seconds=5),
    },
    "routine-check-every-day": {
        "task": "backend.ticket.tasks.ticket_tasks.auto_create_data_repair_ticket",
        # 默认在2:03自动发起，后续拓展可以在页面配置
        "schedule": crontab(minute=3, hour=2),
    },
    "push-nginx-service-conf-every-5min": {
        "task": "backend.db_proxy.tasks.fill_cluster_service_nginx_conf",
        "schedule": crontab(minute="*/1"),
    },
}

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
    # "CODE_INJECTIONS": {
    #     "<head>": """<head>
    #         <style>
    #             .sidemenu {
    #                 display: none !important;
    #             }
    #             .navbar-page-btn .gicon-dashboard {
    #                 display: none !important;
    #             }
    #             .navbar .navbar-buttons--tv {
    #                 display: none !important;
    #             }
    #         </style>
    #     """
    # },
    "BACKEND_CLASS": "backend.bk_dataview.grafana.backends.api.APIHandler",
}
