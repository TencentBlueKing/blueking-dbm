FROM mirrors.tencent.com/build/blueking/dbmedium:latest as medium

FROM debian:bookworm-slim

# 更新包列表并安装 cron 和 gettext-base
# 使用腾讯内网 Debian 源；bookworm 的源配置在 deb822 格式的 debian.sources 中，没有 sources.list
RUN sed -i 's|deb.debian.org|mirrors.tencent.com|g' /etc/apt/sources.list.d/debian.sources && \
    apt-get update && \
    apt-get install -y jq gettext-base curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

## 获取dns介质文件
COPY --from=medium /app/medium/cloud/cloud-dbha/*/*/dbha /data/install/
COPY --from=medium /app/medium/cloud/cloud-kms-tool/*/*/bk-dbm-kms /data/install/
COPY ./start.bash ./dbha-conf-tpl.yaml /data/install/

WORKDIR /data/install

RUN chmod +x start.bash bk-dbm-kms

## 启动dbha服务
ENTRYPOINT ["/bin/bash", "-c", "/data/install/start.bash"]
