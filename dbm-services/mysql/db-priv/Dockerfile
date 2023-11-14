FROM mirrors.tencent.com/sccmsp/golang:1.19-alpine3.17
MAINTAINER tencent
RUN ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime
RUN echo "Asia/Shanghai" > /etc/timezone

ADD privservice /
RUN mkdir /conf

WORKDIR /
CMD /privservice --migrate


