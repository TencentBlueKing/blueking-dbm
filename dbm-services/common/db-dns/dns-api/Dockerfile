FROM centos:7
ARG SRV_NAME
MAINTAINER vincixu vincixu<vincixu@tencent.com>

RUN ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime
RUN echo "Asia/Shanghai" > /etc/timezone

WORKDIR /
COPY ./$SRV_NAME .
COPY ./conf ./conf

ENTRYPOINT ["/bk-dnsapi"]
