FROM golang:1.21 as go-builder

## 标准化时区
RUN ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime && \
    echo "Asia/Shanghai" > /etc/timezone

## 安装go import工具
RUN go install golang.org/x/tools/cmd/goimports@latest

FROM go-builder as go-mod-builder

WORKDIR /blueking-dbm
ADD ./dbm-services ./dbm-services

## 初始化go依赖
RUN set -ex && \
    goimports -w . && find . -name go.mod -execdir go mod tidy \;

FROM go-mod-builder as mysql-medium-builder

## 构建mysql介质
RUN set -ex && \
    cd /blueking-dbm/dbm-services/mysql/db-tools/dbactuator && make VERSION= -j4 && \
    cd /blueking-dbm/dbm-services/mysql/db-tools/mysql-dbbackup && sh build.sh -t txsql && \
    cd /blueking-dbm/dbm-services/mysql/db-tools/mysql-table-checksum && make release-bin VERSION= -j4 && \
    cd /blueking-dbm/dbm-services/mysql/db-tools/mysql-crond && make release-bin VERSION= -j4 && \
    cd /blueking-dbm/dbm-services/mysql/db-tools/mysql-rotatebinlog && make release VERSION= -j4 && \
    cd /blueking-dbm/dbm-services/mysql/db-tools/mysql-monitor && make release-bin VERSION= -j4


FROM go-mod-builder as redis-medium-builder

## 构建redis介质
RUN set -ex && \
    cd /blueking-dbm/dbm-services/redis/db-tools/dbactuator && make VERSION= -j4 && \
    cd /blueking-dbm/dbm-services/redis/db-tools/dbmon && bash package.sh


FROM go-mod-builder as bigdata-medium-builder

## 构建大数据介质
RUN set -ex && \
    cd /blueking-dbm/dbm-services/bigdata/db-tools/dbactuator && make VERSION= -j4


FROM go-builder as medium-builder

WORKDIR /blueking-dbm
COPY --from=mysql-medium-builder /blueking-dbm/dbm-services/mysql ./dbm-services/mysql
COPY --from=redis-medium-builder /blueking-dbm/dbm-services/redis ./dbm-services/redis
COPY --from=bigdata-medium-builder /blueking-dbm/dbm-services/bigdata ./dbm-services/bigdata


FROM python:3.6.12-slim-buster AS base

ENV LC_ALL=C.UTF-8 \
    LANG=C.UTF-8

## PYTHON
# Seems to speed things up
ENV PYTHONUNBUFFERED=1
# Turns off writing .pyc files. Superfluous on an ephemeral container.
ENV PYTHONDONTWRITEBYTECODE=1

# Ensures that the python and pip executables used
# in the image will be those from our virtualenv.
ENV PATH="/venv/bin:$PATH"

RUN set -ex && \
    chmod 1777 /tmp && \
    rm /etc/apt/sources.list && \
    echo "deb https://mirrors.cloud.tencent.com/debian buster main contrib non-free" >> /etc/apt/sources.list && \
    echo "deb https://mirrors.cloud.tencent.com/debian buster-updates main contrib non-free" >> /etc/apt/sources.list && \
    echo "deb-src https://mirrors.cloud.tencent.com/debian buster main contrib non-free" >> /etc/apt/sources.list && \
    echo "deb-src https://mirrors.cloud.tencent.com/debian buster-updates main contrib non-free" >> /etc/apt/sources.list

RUN set -ex && mkdir ~/.pip && printf '[global]\nindex-url = https://mirrors.tencent.com/pypi/simple/' > ~/.pip/pip.conf

FROM base AS builder

WORKDIR /

# Install OS package dependencies.
# Do all of this in one RUN to limit final image size.
RUN set -ex &&  \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        gcc gettext && \
    rm -rf /var/lib/apt/lists/*

RUN ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime

COPY ./dbm-ui/backend/dbm_init/medium/requirements.txt /

## 创建 Python 虚拟环境并安装依赖
RUN set -ex && python -m venv /venv && . /venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt

FROM base AS base-app

## 安装运行时依赖
RUN set -ex &&  \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        gettext curl vim wget git && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
USER root

## 拷贝虚拟环境
COPY --from=builder /venv /venv

## 拷贝第一阶段的文件，构建制品
COPY --from=medium-builder /blueking-dbm /blueking-dbm

## 拷贝脚本文件
ADD ./dbm-ui/backend/dbm_init/medium/ ./

ENV DJANGO_SETTINGS_MODULE=settings
ENV MEDIUM_PATH=dbm-ui/backend/dbm_init/medium

ARG MEDIUM_BUILDER_BRANCH=master
ARG GITHUB_TOKEN=''
ARG GITHUB_USERNAME=''
ARG GITHUB_USER_EMAIL=''

## 将相关制品移动到指定目录，提交medicum.lock文件
RUN set -ex && \
    # 克隆线上的dbm仓库
    git config --global user.email ${GITHUB_USER_EMAIL} && \
    git config --global user.name ${GITHUB_USERNAME} && \
    git clone https://${GITHUB_TOKEN}@github.com/TencentBlueKing/blueking-dbm.git && \
    # 注意：这里需要将.git文件复制给前面构建文件夹，用作判断commit是否需要更新
    cp -r blueking-dbm/.git /blueking-dbm && \
    python main.py --type build && \
    rm -rf /blueking-dbm && \
    # 将更新后的medium.lock文件放到clone的dbm仓库
    cd blueking-dbm/ && \
    git checkout -f ${MEDIUM_BUILDER_BRANCH} && \
    cp ../medium.lock ${MEDIUM_PATH} && \
    # 判断有diff才提pr，否则会非正常结束。注意这里也需要删除.git
    git add ${MEDIUM_PATH}/medium.lock && \
    git diff-index --quiet HEAD && rm -rf /app/blueking-dbm || \
    ( \
     git commit -m "minor: [$(date +"%Y-%m-%d %H:%M:%S")]update medium.lock" && \
     git push --set-upstream --force origin ${MEDIUM_BUILDER_BRANCH}:medicum_lock_${MEDIUM_BUILDER_BRANCH} && \
     rm -rf /app/blueking-dbm \
    )
