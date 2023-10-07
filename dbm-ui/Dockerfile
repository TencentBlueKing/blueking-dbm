FROM node:16.20.1-slim AS static-builder

ENV NPM_VERSION 8.19.4
RUN npm config set registry https://mirrors.tencent.com/npm/

WORKDIR /frontend
COPY frontend ./
RUN yarn install
# fix heap out of memory
ENV NODE_OPTIONS="--max_old_space_size=8192"
RUN yarn build

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
        gcc gettext mariadb-client libmariadbclient-dev default-libmysqlclient-dev && \
    rm -rf /var/lib/apt/lists/*

RUN ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime

COPY ./pyproject.toml ./poetry.lock /

# 创建 Python 虚拟环境并安装依赖
RUN set -ex && python -m venv /venv && . /venv/bin/activate && pip install --upgrade pip && pip install poetry && poetry install

FROM base AS base-app

# 安装运行时依赖
RUN set -ex &&  \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        gettext curl vim default-libmysqlclient-dev && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app
USER root

ADD ./ ./

# 拷贝构件

COPY --from=builder /venv /venv
COPY --from=static-builder /frontend/dist /app/static/

ENV APP_ID=bk-dbm
ENV APP_TOKEN=xxxx

# 收集静态文件
RUN python manage.py collectstatic --settings=config.ci --noinput

ENTRYPOINT ["/app"]
