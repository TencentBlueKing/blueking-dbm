FROM mirrors.tencent.com/build/blueking/dbmedium:latest as medium

FROM debian:bookworm-slim

## 更新包列表并安装 cron 和 gettext-base
RUN apt-get update && \
    apt-get install -y curl jq && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

## 获取drs介质文件
COPY --from=medium /app/medium/cloud/cloud-drs/*/db-remote-service  /data/install/
COPY --from=medium /app/medium/cloud/cloud-drs-tmysqlparse/*/tmysqlparse /data/install/
COPY ./start.bash  /data/install/

WORKDIR /data/install

RUN chmod +x start.bash

## 启动drs服务
ENTRYPOINT ["/bin/bash", "-c", "/data/install/start.bash"]
