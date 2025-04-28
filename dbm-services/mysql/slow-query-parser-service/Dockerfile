FROM mirrors.tencent.com/build/blueking/tmysqlparse:latest

RUN ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime
RUN echo "Asia/Shanghai" > /etc/timezone

ADD build/slow-query-parser-service /

WORKDIR /
ENTRYPOINT ["/slow-query-parser-service", "run", "--address=0.0.0.0:80", "--tmysqlparse-bin=/tmysqlparse"]
