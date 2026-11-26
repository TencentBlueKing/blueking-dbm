FROM golang:1.26

ADD build/db-event-consumer /
RUN mkdir /logs

WORKDIR /
# --enable-defaults 会在 config.yaml 同目录生成 data.defaults.yaml(每次启动覆盖重写)，
# 内置的默认入库项由此生效，个性化调整写在挂载进来的 data.sinkers.yaml 里
CMD /db-event-consumer -c config.yaml --enable-defaults
