FROM golang:1.23

ADD build/bkdata-kafka-consumer /
RUN mkdir /logs

WORKDIR /
CMD /bkdata-kafka-consumer -c config.yaml
