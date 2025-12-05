FROM debian:bookworm-slim

## 更新包列表并安装 cron 和 gettext-base
RUN apt-get update && \
    apt-get install -y --no-install-recommends cron jq gettext-base curl wget ca-certificates && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /data/install

## 复制相关配置文件
COPY ./start.bash ./nginx-tpl.conf ./dbm.html ./crond.bash /data/install/

## 获取nginx介质
ENV DOWNLOAD_URL=https://github.com/TencentBlueKing/blueking-dbm/releases/download
ENV VERSION=v1.0.0

RUN set -ex && \
    wget -qO nginx-portable.tgz ${DOWNLOAD_URL}/${VERSION}/nginx-portable-container.tgz --no-check-certificate && \
    chmod -R 755 /data/install/

## 启动nginx服务
ENTRYPOINT ["/bin/bash", "-c", "service cron start && /data/install/start.bash"]
