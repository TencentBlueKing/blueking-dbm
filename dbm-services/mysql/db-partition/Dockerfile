FROM mirrors.tencent.com/sccmsp/golang:1.16
MAINTAINER tencent
RUN ln -sf /usr/share/zoneinfo/Asia/Shanghai /etc/localtime
RUN echo "Asia/Shanghai" > /etc/timezone

ADD partition /

WORKDIR /
CMD /partition --migrate


