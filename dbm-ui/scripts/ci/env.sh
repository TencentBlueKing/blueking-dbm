#!/bin/bash

# DJANGO配置
export DJANGO_SETTINGS_MODULE=config.prod
export DEBUG=true


export APP_ID=bk-dbm
export APP_TOKEN=xxx
export YUM_INSTALL_SERVICE=1
export CREATE_PYTHON_VENV=1
export VENV_DIR="/tmp/ci_py_venv"

# CI自定义环境变量
# 数据库
export DB_NAME=$APP_ID
export DB_USER="root"
export DB_PASSWORD=
export DB_HOST="localhost"
export DB_PORT="3306"

# iam
export BK_IAM_SKIP=true