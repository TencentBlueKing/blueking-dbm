FROM mirrors.tencent.com/build/blueking/tmysqlparse:3.0.8

RUN ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime
RUN echo "Asia/Shanghai" > /etc/timezone

ADD bksimulation /
#ADD tmysqlparse /
ADD rule.yaml /
ADD spider_rule.yaml /
WORKDIR /
ENTRYPOINT ["/bksimulation"]