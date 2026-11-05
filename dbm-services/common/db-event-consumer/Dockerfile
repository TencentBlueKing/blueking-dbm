FROM golang:1.26

ADD build/db-event-consumer /
RUN mkdir /logs

WORKDIR /
CMD /db-event-consumer -c config.yaml
