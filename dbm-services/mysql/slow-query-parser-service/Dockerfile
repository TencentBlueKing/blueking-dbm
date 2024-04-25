FROM golang:1.21

ADD build/slow-query-parser-service /

WORKDIR /
ENTRYPOINT ["/slow-query-parser-service", "run", "--address=0.0.0.0:80"]
