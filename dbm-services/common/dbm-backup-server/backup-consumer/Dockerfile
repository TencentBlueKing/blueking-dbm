FROM golang:1.26

ADD build/backup-stm-kafka-consumer /
RUN mkdir /logs

WORKDIR /
CMD /backup-stm-kafka-consumer -c runtime_config.yaml
