FROM mirrors.tencent.com/build/blueking/dbmedium-builder:1.0.0 as go-mod-builder

WORKDIR /blueking-dbm
ADD ./dbm-services ./dbm-services

## 初始化go依赖
RUN set -ex && \
    goimports -w . && find . -name go.mod -execdir go mod tidy \;


#FROM python:3.6.12-slim-buster AS base
FROM python:3.10.13-slim AS base

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
    rm /etc/apt/sources.list.d/debian.sources && \
    echo "deb https://mirrors.cloud.tencent.com/debian bookworm main contrib non-free" >> /etc/apt/sources.list && \
    echo "deb https://mirrors.cloud.tencent.com/debian bookworm-updates main contrib non-free" >> /etc/apt/sources.list && \
    echo "deb-src https://mirrors.cloud.tencent.com/debian bookworm main contrib non-free" >> /etc/apt/sources.list && \
    echo "deb-src https://mirrors.cloud.tencent.com/debian bookworm-updates main contrib non-free" >> /etc/apt/sources.list

RUN set -ex && mkdir ~/.pip && printf '[global]\nindex-url = https://mirrors.tencent.com/pypi/simple/' > ~/.pip/pip.conf

FROM base AS python-builder

WORKDIR /

# Install OS package dependencies.
# Do all of this in one RUN to limit final image size.
RUN set -ex &&  \
    apt-get update && \
    apt-get install -y --no-install-recommends \
     gcc gettext g++ pkg-config && \
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
COPY --from=python-builder /venv /venv

## 拷贝脚本文件
ADD ./dbm-ui/backend/dbm_init/medium/ ./

ENV DJANGO_SETTINGS_MODULE=settings
ENV MEDIUM_PATH=dbm-ui/backend/dbm_init/medium

ARG MEDIUM_BUILDER_BRANCH=master
ARG GITHUB_TOKEN=''
ARG GITHUB_USERNAME=''
ARG GITHUB_USER_EMAIL=''

## 更新并提交medicum.lock文件
RUN set -ex && \
    # 克隆线上的dbm仓库
    git config --global user.email ${GITHUB_USER_EMAIL} && \
    git config --global user.name ${GITHUB_USERNAME} && \
    git clone https://${GITHUB_TOKEN}@github.com/TencentBlueKing/blueking-dbm.git && \
    # 将clone的blueking-dbm转移到根目录操作
    mv blueking-dbm/ / && cd /blueking-dbm && git checkout -f ${MEDIUM_BUILDER_BRANCH} && \
    # 更新lock文件
    cd /app && python main.py --type update_lock && \
    # 将更新后的medium.lock文件放到clone的dbm仓库
    cp medium.lock /blueking-dbm/${MEDIUM_PATH} && \
    # 判断有diff才提pr，否则会非正常结束。注意这里也需要删除.git
    cd /blueking-dbm && git add ${MEDIUM_PATH}/medium.lock && \
    git diff-index --quiet HEAD && rm -rf /blueking-dbm || \
    ( \
     git commit -m "chore: [$(date +"%Y-%m-%d %H:%M:%S")]update medium.lock #1" && \
     git push --set-upstream --force origin ${MEDIUM_BUILDER_BRANCH}:medium_lock && \
     rm -rf /blueking-dbm \
    )


FROM go-mod-builder as medium-builder

WORKDIR /

## 保存jq的脚本用于下一阶段用
RUN set -ex && \
    echo 'yq e ".${1}[].${2} | .${3}" /medium.lock | grep -v null' >> lock.sh && \
    chmod 777 lock.sh

## 获取上一阶段的lock文件
COPY --from=base-app  /app/medium.lock /


FROM medium-builder as mysql-medium-builder

WORKDIR /
## 构建mysql介质
RUN set -ex && \
    cd /blueking-dbm/dbm-services/mysql/db-tools/dbactuator && \
    make VERSION=$(/lock.sh mysql actuator version) GITHASH=$(/lock.sh mysql actuator commitId) -j4 && \
    cd /blueking-dbm/dbm-services/mysql/db-tools/mysql-table-checksum && \
    make release-bin VERSION=$(/lock.sh mysql mysql-checksum version) GITHASH=$(/lock.sh mysql mysql-checksum commitId) GITDATE=$(/lock.sh mysql mysql-checksum commitDate) -j4 && \
    cd /blueking-dbm/dbm-services/mysql/db-tools/mysql-crond && \
    make release-bin VERSION=$(/lock.sh mysql mysql-crond version) GITHASH=$(/lock.sh mysql mysql-crond commitId) GITDATE=$(/lock.sh mysql mysql-crond commitDate) -j4 && \
    cd /blueking-dbm/dbm-services/mysql/db-tools/mysql-rotatebinlog && \
    make release-bin VERSION=$(/lock.sh mysql rotate-binlog version) GITHASH=$(/lock.sh mysql rotate-binlog commitId) GITDATE=$(/lock.sh mysql rotate-binlog commitDate) -j4 && \
    cd /blueking-dbm/dbm-services/mysql/db-tools/mysql-monitor && \
    make release-bin VERSION=$(/lock.sh mysql mysql-monitor version) GITHASH=$(/lock.sh mysql mysql-monitor commitId) GITDATE=$(/lock.sh mysql mysql-monitor commitDate) -j4

## 编译 dbbackup-go community，下载依赖
RUN set -ex && \
    cd /blueking-dbm/dbm-services/mysql/db-tools/mysql-dbbackup && \
    mv /toolkit/dbbackup-go-deps-community.tar.gz . && \
    make package VERSION=$(/lock.sh mysql dbbackup version) DIST=community GITHASH=$(/lock.sh mysql dbbackup commitId) -j4


FROM medium-builder as redis-medium-builder

## 构建redis介质
RUN set -ex && \
    cd /blueking-dbm/dbm-services/redis/db-tools/dbactuator && \
    make VERSION=$(/lock.sh redis actuator version) GITHASH=$(/lock.sh redis actuator commitId) -j4 && \
    cd /blueking-dbm/dbm-services/redis/db-tools/dbmon && \
    cat package.sh | tr -d '\r' > package.sh.tmp && mv package.sh.tmp package.sh && \
    bash package.sh --version=$(/lock.sh redis dbmon version) --git-hash=$(/lock.sh redis dbmon commitId) --git-date=$(/lock.sh redis dbmon commitDate)


FROM medium-builder as mongodb-medium-builder

## 构建mongodb介质
RUN set -ex && \
    cd /blueking-dbm/dbm-services/mongodb/db-tools/dbactuator && \
    make build VERSION=$(/lock.sh mongodb actuator version) GITHASH=$(/lock.sh mongodb actuator commitId) BUILDSTAMP=$(/lock.sh mongodb actuator commitDate) -j4 && \
    cd /blueking-dbm/dbm-services/mongodb/db-tools/dbmon && \
    cat package.sh | tr -d '\r' > package.sh.tmp && mv package.sh.tmp package.sh && \
    bash package.sh --version=$(/lock.sh mongodb dbmon version) --git-hash=$(/lock.sh mongodb dbmon commitId) --git-date=$(/lock.sh mongodb dbmon commitDate) && \
    cd /blueking-dbm/dbm-services/mongodb/db-tools/mongo-toolkit-go && \
    make build VERSION=$(/lock.sh mongodb mongo-toolkit version) GITHASH=$(/lock.sh mongodb mongo-toolkit commitId) BUILDSTAMP=$(/lock.sh mongodb mongo-toolkit commitDate) -j4


FROM medium-builder as bigdata-medium-builder

## 构建大数据介质
RUN set -ex && \
    ## 大数据的actuator都是一个，任意编译即可
    cd /blueking-dbm/dbm-services/bigdata/db-tools/dbactuator && \
    make VERSION=$(/lock.sh es actuator version) GITHASH=$(/lock.sh es actuator commitId) -j4 && \
    ## riak的介质需要单独编译
    cd /blueking-dbm/dbm-services/riak/db-tools/dbactuator && \
    make build VERSION=$(/lock.sh riak actuator version) GITHASH=$(/lock.sh riak actuator commitId) -j4 && \
    cd /blueking-dbm/dbm-services/riak/db-tools/riak-monitor && \
    make release-bin VERSION=$(/lock.sh riak riak-monitor version) GITHASH=$(/lock.sh riak riak-monitor commitId) -j4


FROM medium-builder as sqlserver-medium-builder

## 构建sqlserver介质
RUN set -ex && \
    cd /blueking-dbm/dbm-services/sqlserver/db-tools/dbactuator && \
    make build VERSION=$(/lock.sh sqlserver actuator version) GITHASH=$(/lock.sh sqlserver actuator commitId) -j4


FROM medium-builder as cloud-medium-builder

## 构建云区域组件介质
RUN set -ex && \
    cd /blueking-dbm/dbm-services/common/dbha/ha-module && \
    make build VERSION=$(/lock.sh cloud cloud-dbha version) GITHASH=$(/lock.sh cloud cloud-dbha commitId) -j4  && \
    cd /blueking-dbm/dbm-services/common/db-dns/dns-reload && \
    make build VER=$(/lock.sh cloud cloud-dns-pullcrond version) && \
    cd /blueking-dbm/dbm-services/mysql/db-remote-service && \
    make VERSION=$(/lock.sh cloud cloud-drs version) GITHASH=$(/lock.sh cloud cloud-drs commitId) -j4


FROM base-app as medium-app

WORKDIR /app

# 复制静态二进制文件
COPY --from=medium-builder /toolkit /toolkit
# 复制mysql的编译介质
COPY --from=mysql-medium-builder /blueking-dbm/dbm-services/mysql /blueking-dbm/dbm-services/mysql
# 复制redis的编译介质
COPY --from=redis-medium-builder /blueking-dbm/dbm-services/redis /blueking-dbm/dbm-services/redis
# 复制mongo的编译介质
COPY --from=mongodb-medium-builder /blueking-dbm/dbm-services/mongodb /blueking-dbm/dbm-services/mongodb
# 复制sqlserver的编译介质
COPY --from=sqlserver-medium-builder /blueking-dbm/dbm-services/sqlserver /blueking-dbm/dbm-services/sqlserver
# 复制大数据的编译介质
COPY --from=bigdata-medium-builder /blueking-dbm/dbm-services/bigdata /blueking-dbm/dbm-services/bigdata
COPY --from=bigdata-medium-builder /blueking-dbm/dbm-services/riak /blueking-dbm/dbm-services/riak
# 复制云区域组件的编译介质
COPY --from=cloud-medium-builder /blueking-dbm/dbm-services/common /blueking-dbm/dbm-services/common
COPY --from=cloud-medium-builder /blueking-dbm/dbm-services/mysql/db-remote-service /blueking-dbm/dbm-services/mysql/db-remote-service

RUN set -ex && \
    python main.py --type build && \
    rm -rf /blueking-dbm /toolkit
