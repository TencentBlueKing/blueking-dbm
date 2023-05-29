FROM mirrors.tencent.com/sccmsp/tmysqlparse:latest

ADD build/slow-query-parser-service /

WORKDIR /
ENTRYPOINT ["/slow-query-parser-service", "run", "--address=0.0.0.0:80", "--tmysqlparse-bin=/tmysqlparse"]
