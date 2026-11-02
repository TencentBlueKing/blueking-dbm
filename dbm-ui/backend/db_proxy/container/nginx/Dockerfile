FROM mirrors.tencent.com/build/blueking/dbmedium:latest as medium

FROM debian:bookworm-slim

## 更新包列表并安装 gettext-base 等依赖
# 使用腾讯内网 Debian 源；bookworm 的源配置在 deb822 格式的 debian.sources 中，没有 sources.list
RUN sed -i 's|deb.debian.org|mirrors.tencent.com|g' /etc/apt/sources.list.d/debian.sources && \
    apt-get update && \
    apt-get install -y --no-install-recommends jq gettext-base curl wget ca-certificates && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /data/install

## 复制相关配置文件
COPY --from=medium /app/medium/cloud/cloud-kms-tool/*/*/bk-dbm-kms /data/install/
COPY ./start.bash ./nginx-tpl.conf ./dbm.html ./crond.bash /data/install/

## 获取nginx介质
ENV DOWNLOAD_URL=https://github.com/TencentBlueKing/blueking-dbm/releases/download
ENV VERSION=v1.0.0

RUN set -ex && \
    wget -qO nginx-portable.tgz ${DOWNLOAD_URL}/${VERSION}/nginx-portable-container.tgz --no-check-certificate && \
    chmod -R 755 /data/install/

## 启动nginx服务
ENTRYPOINT ["/bin/bash", "-c", "/data/install/start.bash"]
