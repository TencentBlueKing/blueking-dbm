FROM centos:7

RUN ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime
RUN echo "Asia/Shanghai" > /etc/timezone

WORKDIR /
COPY ./bk-dnsapi .

ENTRYPOINT ["/bk-dnsapi"]
