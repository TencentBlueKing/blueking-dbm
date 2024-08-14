FROM mirrors.tencent.com/build/blueking/dbmedium:latest as medium

FROM debian:bookworm-slim

## 更新包列表并安装 cron 和 gettext-base
RUN apt-get update && \
    apt-get install -y cron gettext-base curl jq && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

## 获取nginx介质
COPY --from=medium /app/medium/cloud/cloud-nginx/*/nginx-portable.tgz /data/install/
COPY ./start.bash ./nginx-tpl.conf ./dbm.html ./crond.bash /data/install/

WORKDIR /data/install

RUN chmod -R 755 /data/install/

## 启动nginx服务
ENTRYPOINT ["/bin/bash", "-c", "service cron start && /data/install/start.bash"]
