FROM mirrors.tencent.com/sccmsp/tmysqlparse:3.0.7

ADD build/slow-query-parser-service /

WORKDIR /
ENTRYPOINT ["/slow-query-parser-service", "run"]