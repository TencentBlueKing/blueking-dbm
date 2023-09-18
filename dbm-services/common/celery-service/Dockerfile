FROM golang:1.19

ADD build/celery-service /
ADD build/external-tasks.yaml /
ADD build/collect /
WORKDIR /
ENTRYPOINT ["/celery-service", "run", "--log-console"]